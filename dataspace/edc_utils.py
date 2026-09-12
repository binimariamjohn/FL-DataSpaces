#!/usr/bin/env python3
"""EDC utilities."""
import json
import logging
import time
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


def _make_edc_request(method, url, api_key, json_data=None, timeout=10):
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    try:
        resp = requests.request(method, url, json=json_data, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {method} {url} - {e}")
        raise


class EDCConfig:
    def __init__(self, config_dir="configs"):
        self.base_dir = Path(config_dir)
        with open(self.base_dir / "dataSpaceFactors.json") as f:
            self.edc_data = json.load(f)
    
    def load_connector(self, connector_id):
        providers = self.edc_data.get("edc", {}).get("providers_connectors", [])
        consumers = self.edc_data.get("edc", {}).get("consumer_connectors", [])
        
        for item in providers + consumers:
            if item["name"] == connector_id or item["name"].startswith(connector_id):
                return self._load_props(item["config_path"])
        raise ValueError(f"Connector {connector_id} not found")
    
    def _load_props(self, path):
        props = {}
        with open(self.base_dir / path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    props[k.strip()] = v.strip()
        return props
    
    def get_api_key(self):
        return self.edc_data.get("edc", {}).get("api_key", "password")


def load_template(file_path, **params):
    with open(file_path) as f:
        content = f.read()
    
    for k, v in params.items():
        placeholder = f"{{{{{k}}}}}"
        if isinstance(v, (dict, list)):
            content = content.replace(placeholder, f"__OBJ_{k}__")
        else:
            content = content.replace(placeholder, str(v))
    
    data = json.loads(content)
    
    def replace_obj(obj):
        if isinstance(obj, dict):
            return {k: replace_obj(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_obj(i) for i in obj]
        elif isinstance(obj, str):
            for k, v in params.items():
                if isinstance(v, (dict, list)) and obj == f"__OBJ_{k}__":
                    return v
            return obj
        return obj
    
    return replace_obj(data)


def check_edc_health(connector_name, config: EDCConfig) -> bool:
    try:
        props = config.load_connector(connector_name)
        participant_id = props.get('edc.participant.id', '')
        host = f"{participant_id}-connector" if participant_id else "localhost"
        url = f"http://{host}:{props['web.http.management.port']}/management/v3/assets/request"
        query = {"@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"}, "filterExpression": []}
        resp = requests.post(url, json=query, 
                            headers={"X-API-Key": "password", "Content-Type": "application/json"},
                            timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def create_asset(mgmt_url, asset_data, api_key="password"):
    asset_id = asset_data['@id']
    resp = _make_edc_request("POST", f"{mgmt_url}/assets", api_key, asset_data)
    if resp.status_code not in [200, 204, 409]:
        raise RuntimeError(f"Asset creation failed: {resp.status_code}")
    logger.info(f"Asset created: {asset_id}")


def create_policy(mgmt_url, policy_data, api_key="password"):
    policy_id = policy_data['@id']
    resp = _make_edc_request("POST", f"{mgmt_url}/policydefinitions", api_key, policy_data)
    if resp.status_code not in [200, 204, 409]:
        raise RuntimeError(f"Policy creation failed: {resp.status_code}")
    logger.info(f"Policy created: {policy_id}")


def create_contract_definition(mgmt_url, contract_data, api_key="password"):
    contract_id = contract_data['@id']
    resp = _make_edc_request("POST", f"{mgmt_url}/contractdefinitions", api_key, contract_data)
    if resp.status_code not in [200, 204, 409]:
        raise RuntimeError(f"Contract creation failed: {resp.status_code}")
    logger.info(f"Contract created: {contract_id}")


def fetch_catalogue(mgmt_url, provider_dsp_url, api_key="password", config_path=None, retries=5, delay=10):
    catalog_request = load_template(f"{config_path}/edc/catalog-request.json", PROVIDER_DSP=provider_dsp_url)
    req_body_size = len(json.dumps(catalog_request).encode())

    for attempt in range(retries):
        try:
            t0 = time.time()
            resp = _make_edc_request("POST", f"{mgmt_url}/catalog/request", api_key, catalog_request, timeout=30)
            catalog_json = resp.json()
            return {
                'catalog': catalog_json,
                'catalog_time': time.time() - t0,
                'bytes_sent': req_body_size,
                'bytes_received': len(resp.content) if resp.content else 0,
                'num_messages': attempt + 1,
            }
        except Exception as e:
            if attempt < retries - 1:
                logger.warning(f"Catalog attempt {attempt + 1}/{retries} failed, retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"Catalog fetch failed after {retries} attempts")
                raise


def negotiate_contract(mgmt_url, provider_dsp_url, contract_offer, asset_id, api_key="password", config_path=None):
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    t0 = time.time()
    total_bytes_sent = 0
    total_bytes_received = 0
    num_messages = 0
    
    policy = dict(contract_offer)
    if "odrl:target" not in policy:
        policy["odrl:target"] = {"@id": asset_id}
    if "odrl:assigner" not in policy:
        provider_id = provider_dsp_url.split("://")[1].split("-connector")[0]
        policy["odrl:assigner"] = {"@id": provider_id}
    
    negotiation_request = load_template(f"{config_path}/edc/negotiation-request.json", PROVIDER_DSP=provider_dsp_url, OFFER_POLICY=policy)
    total_bytes_sent += len(json.dumps(negotiation_request).encode())

    num_messages += 1
    resp = requests.post(f"{mgmt_url}/contractnegotiations", json=negotiation_request, headers=headers, timeout=30)
    total_bytes_received += len(resp.content) if resp.content else 0

    if resp.status_code != 200:
        logger.error(f"Negotiation failed: {resp.status_code}")
        return {'agreement_id': None, 'negotiation_time': time.time() - t0, 'bytes_sent': total_bytes_sent, 'bytes_received': total_bytes_received, 'num_messages': num_messages}
    
    negotiation_id = resp.json().get("@id")

    for poll_attempt in range(60):
        time.sleep(2)
        num_messages += 1
        poll_resp = requests.get(f"{mgmt_url}/contractnegotiations/{negotiation_id}", headers=headers, timeout=10)
        total_bytes_received += len(poll_resp.content) if poll_resp.content else 0
        state = poll_resp.json().get("edc:state") or poll_resp.json().get("state")

        if state in ["FINALIZED", "CONFIRMED"]:
            agreement_id = poll_resp.json().get("edc:contractAgreementId") or poll_resp.json().get("contractAgreementId")
            logger.info(f"Contract negotiated: {agreement_id}")
            return {'agreement_id': agreement_id, 'negotiation_time': time.time() - t0, 'bytes_sent': total_bytes_sent, 'bytes_received': total_bytes_received, 'num_messages': num_messages}
        
        if state in ["TERMINATED", "ERROR", "FAILED"]:
            logger.error(f"Negotiation failed: {state}")
            return {'agreement_id': None, 'negotiation_time': time.time() - t0, 'bytes_sent': total_bytes_sent, 'bytes_received': total_bytes_received, 'num_messages': num_messages}
    
    logger.error("Negotiation timeout")
    return {'agreement_id': None, 'negotiation_time': time.time() - t0, 'bytes_sent': total_bytes_sent, 'bytes_received': total_bytes_received, 'num_messages': num_messages}


def initiate_transfer(mgmt_url, provider_dsp_url, agreement_id, asset_id, destination_config, api_key="password", config_path=None):
    transfer_request = load_template(
        f"{config_path}/edc/transfer-request.json",
        PROVIDER_DSP=provider_dsp_url,
        AGREEMENT_ID=agreement_id,
        ASSET_ID=asset_id,
        CONSUMER_NC=destination_config.get("baseUrl", "").replace("http://", "").replace(":80", ""),
        TARGET_PATH=destination_config.get("filePath", ""),
        CONSUMER_ID=destination_config.get("keyName", "").replace("-key", ""),
        CONSUMER_CONNECTOR=destination_config.get("receiverHttpEndpoint", "").split("://")[1].split(":")[0],
        CONSUMER_MANAGEMENT_PORT=destination_config.get("receiverHttpEndpoint", "").split(":")[-1].replace("/management", "")
    )

    req_size = len(json.dumps(transfer_request).encode())
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    resp = requests.post(f"{mgmt_url}/transferprocesses", json=transfer_request, headers=headers, timeout=30)
    resp_size = len(resp.content) if resp.content else 0

    if resp.status_code == 200:
        transfer_id = resp.json().get("@id")
        logger.debug(f"Transfer initiated: {transfer_id}")
        return {'transfer_id': transfer_id, 'bytes_sent': req_size, 'bytes_received': resp_size, 'num_messages': 1}
    else:
        logger.error(f"Transfer failed: {resp.status_code}")
        return {'transfer_id': None, 'bytes_sent': req_size, 'bytes_received': resp_size, 'num_messages': 1}


def poll_transfer_status(mgmt_url, transfer_id, api_key="password", max_attempts=60):
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    t0 = time.time()
    total_bytes = 0

    for i in range(max_attempts):
        time.sleep(2)
        raw = requests.get(f"{mgmt_url}/transferprocesses/{transfer_id}", headers=headers, timeout=10)
        total_bytes += len(raw.content) if raw.content else 0
        resp = raw.json()
        
        if isinstance(resp, list):
            logger.error(f"Transfer error: {resp}")
            return {'success': False, 'transfer_time': time.time() - t0, 'bytes_sent': 0, 'bytes_received': total_bytes, 'num_messages': i + 1}
        
        state = resp.get("edc:state") or resp.get("state")

        if state == "COMPLETED":
            return {'success': True, 'transfer_time': time.time() - t0, 'bytes_sent': 0, 'bytes_received': total_bytes, 'num_messages': i + 1}
        elif state in ["TERMINATED", "ERROR", "FAILED"]:
            logger.error(f"Transfer failed: {state}")
            return {'success': False, 'transfer_time': time.time() - t0, 'bytes_sent': 0, 'bytes_received': total_bytes, 'num_messages': i + 1}
    
    logger.error("Transfer timeout")
    return {'success': False, 'transfer_time': time.time() - t0, 'bytes_sent': 0, 'bytes_received': total_bytes, 'num_messages': max_attempts}


def _create_edc_objects(mgmt_url, asset, policy, contract, api_key):
    create_asset(mgmt_url, asset, api_key)
    create_policy(mgmt_url, policy, api_key)
    create_contract_definition(mgmt_url, contract, api_key)


def check_all_edc_connectors(project_root):
    from fedLearning.utils.config_utils import UnifiedConfig
    num_clients = UnifiedConfig().raw['dataset_factors']['num_clients']
    config = EDCConfig(str(project_root / "configs"))
    connectors = [(f"client-{i}-provider", f"Client {i}") for i in range(1, num_clients + 1)]
    connectors.append(("research-centre-consumer", "Research Centre"))
    for name, label in connectors:
        if not check_edc_health(name, config):
            raise RuntimeError(f"{label} connector not healthy")
        logger.info(f"{label} OK")


def wait_for_edc_connectors(project_root):
    logger.info("Checking EDC connectors...")
    check_all_edc_connectors(project_root)


