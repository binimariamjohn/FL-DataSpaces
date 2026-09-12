#!/usr/bin/env python3
"""Marketplace utilities."""
import logging
import time
import xml.etree.ElementTree as ET
from pathlib import Path
import requests
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

logger = logging.getLogger(__name__)


def publish_client_offer(client_id, project_root):
    from dataspace.connector_config import ConnectorConfig
    from dataspace.edc_utils import load_template, _create_edc_objects
    from fedLearning.utils.config_utils import UnifiedConfig

    conn_cfg = ConnectorConfig(project_root / "configs")
    h_cfg = conn_cfg.get_client_config(client_id)
    providers = UnifiedConfig().raw.get('edc', {}).get('providers_connectors', [])
    provider_entry = next(
        (p for p in providers if f"client-{client_id}" in p.get('name', '')),
        {}
    )

    mgmt_host = f"http://localhost:{h_cfg['mgmt_port']}/management/v3"
    mgmt_catalogue = h_cfg['mgmt_url']
    dsp = h_cfg['protocol_url']
    provider_id = h_cfg['participant_id']
    asset_id = f"{provider_id}-mnist"
    price = provider_entry.get('price_info', '12000')
    training_allowed = provider_entry.get('training_allowed', 'true')

    asset = load_template(
        str(project_root / "configs/edc/asset.json"),
        ASSET_ID=asset_id, PROVIDER_NC=f"{provider_id}-nextcloud", PROVIDER_ID=provider_id,
        remote_base_path="trained_models",
        filename=f"{provider_id}_weights.pkl",
        DATASET_ID=f"MNIST-{client_id}", CLIENT_ID=provider_id,
        PRICE_INFO=price, TRAINING_ALLOWED=training_allowed
    )
    policy = load_template(str(project_root / "configs/edc/policy.json"),
                           POLICY_ID=f"{provider_id}-policy")
    contract = load_template(
        str(project_root / "configs/edc/contract.json"),
        CONTRACT_ID=f"{provider_id}-contract",
        POLICY_ID=f"{provider_id}-policy",
        CONTRACT_POLICY_ID=f"{provider_id}-policy",
        ASSET_ID=asset_id
    )

    _create_edc_objects(mgmt_host, asset, policy, contract, h_cfg['api_key'])

    offer = ET.Element('offer')
    for k, v in {
        'client_id': provider_id,
        'dataset_id': f'MNIST-{client_id}', 'price_info': price,
        'training_allowed': training_allowed, 'provider_connector_protocol_url': dsp,
        'provider_connector_management_url': mgmt_catalogue, 'asset_id': asset_id,
        'policy_id': f'{provider_id}-policy',
        'contract_definition_id': f'{provider_id}-contract'
    }.items():
        ET.SubElement(offer, k).text = str(v)

    import os
    host = "marketplace-webapp" if os.path.exists("/.dockerenv") else "localhost"
    webapp_url = f"http://{host}:5001/offers"
    for attempt in range(30):
        try:
            resp = requests.post(
                webapp_url,
                data=ET.tostring(offer, encoding='utf-8', method='xml'),
                headers={'Content-Type': 'application/xml'},
                timeout=5
            )
            resp.raise_for_status()
            logger.info(f"Client {client_id} offer published")
            return
        except Exception as e:
            if attempt < 29:
                time.sleep(3)
            else:
                raise RuntimeError(f"Marketplace not reachable at {webapp_url} after 30 attempts: {e}")


def get_client_offers_from_webapp():
    import os
    host = "marketplace-webapp" if os.path.exists("/.dockerenv") else "localhost"
    resp = requests.get(f'http://{host}:5001/offers', timeout=10)
    resp.raise_for_status()
    return [{child.tag: child.text for child in offer}
            for offer in ET.fromstring(resp.content).findall('offer')]


def select_clients_by_criteria(offers, min_price=10000, require_training=True):
    selected = []
    for offer in offers:
        training_ok = offer.get('training_allowed', '').lower() == 'true'
        price = int(offer.get('price_info', '0')) if offer.get('price_info', '0').isdigit() else 0
        if training_ok == require_training and price > min_price:
            selected.append(offer)
    return selected


def discover_clients(num_clients, logger_obj, max_wait=180):
    selected = []
    logger_obj.info(f"Waiting for marketplace webapp and {num_clients} client offers...")
    for attempt in range(max_wait):
        try:
            r = requests.get("http://marketplace-webapp:5001/offers", timeout=5)
            if r.status_code == 200:
                catalogue = get_client_offers_from_webapp()
                selected = select_clients_by_criteria(catalogue, min_price=10000, require_training=True)
                if len(selected) >= num_clients:
                    logger_obj.info(f"Found {len(selected)} clients (after {attempt+1}s)")
                    return selected
                if selected and attempt % 10 == 0:
                    logger_obj.info(f"Found {len(selected)}/{num_clients} clients so far "
                                    f"(attempt {attempt+1}/{max_wait})... waiting for all")
                elif attempt % 10 == 0:
                    logger_obj.info(f"Marketplace up but 0 offers yet (attempt {attempt+1}/{max_wait})...")
        except Exception:
            if attempt % 10 == 0:
                logger_obj.info(f"Marketplace not reachable yet (attempt {attempt+1}/{max_wait})...")
        time.sleep(1)

    raise RuntimeError(f"Expected {num_clients} clients but only found "
                       f"{len(selected)} after {max_wait}s")
