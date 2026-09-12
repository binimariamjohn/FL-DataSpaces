import logging
import tensorflow as tf
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dataspace.connector_config import ConnectorConfig
from dataspace.edc_utils import (
    load_template, initiate_transfer, poll_transfer_status, _create_edc_objects,
    fetch_catalogue, negotiate_contract
)
from dataspace.nextcloud_utils import get_client_nextcloud, get_research_centre_nextcloud
from dataspace.edc_negotiation import (
    negotiate_edc_contracts, select_offered_asset, build_simple_agreement
)
from fedLearning.models import load_weights_from_file

logger = logging.getLogger(__name__)

#EDC: Negotiate contract to receive global model from research centre.
def negotiate_model_receive_contract(project_root, client_num, client_id):
    conn_cfg = ConnectorConfig(project_root / "configs")
    h_cfg = conn_cfg.get_client_config(int(client_num))
    rc_cfg = conn_cfg.get_research_centre_config()

    cat_result = fetch_catalogue(
        h_cfg['mgmt_url'], rc_cfg['protocol_url'], h_cfg['api_key'], str(project_root / "configs"))
    catalog = cat_result['catalog']
    datasets = catalog.get("dcat:dataset", [])
    if isinstance(datasets, dict):
        datasets = [datasets]
    ds = next((d for d in datasets if d.get("@id") == "rc-model-v0"), None)
    if not ds:
        raise RuntimeError("rc-model-v0 not found in RC catalog")
    policies = ds.get("odrl:hasPolicy", [])
    if isinstance(policies, dict):
        policies = [policies]

    neg_result = negotiate_contract(
        h_cfg['mgmt_url'], rc_cfg['protocol_url'], policies[0], "rc-model-v0",
        h_cfg['api_key'], str(project_root / "configs")
    )
    agreement_id = neg_result['agreement_id']
    logger.info(f"{client_id}: model receive contract negotiated")
    return agreement_id


#EDC: Receive global model weights from research centre.
def receive_global_model_via_edc(project_root, client_num, client_id, agreement_id):
    conn_cfg = ConnectorConfig(project_root / "configs")
    h_cfg = conn_cfg.get_client_config(int(client_num))
    rc_cfg = conn_cfg.get_research_centre_config()

    h_nc = f"{h_cfg['participant_id']}-nextcloud"
    target_path = "received_models"
    nc = get_client_nextcloud(int(client_num))
    nc.ensure_directory(target_path)

    dest_config = {
        "type": "Nextcloud",
        "baseUrl": f"http://{h_nc}:80",
        "filePath": target_path,
        "keyName": f"{h_cfg['participant_id']}-key",
        "receiverHttpEndpoint": f"http://{h_cfg['connector_hostname']}:{h_cfg['mgmt_port']}/management"
    }

    init_result = initiate_transfer(
        h_cfg['mgmt_url'], rc_cfg['protocol_url'],
        agreement_id, "rc-model-v0",
        dest_config, h_cfg['api_key'], str(project_root / "configs")
    )
    transfer_id = init_result['transfer_id']
    logger.info(f"{client_id}: global model transfer initiated")

    poll_result = poll_transfer_status(h_cfg['mgmt_url'], transfer_id, h_cfg['api_key'])
    if not poll_result['success']:
        raise RuntimeError(f"{client_id}: global model transfer failed")

    return load_weights_from_file("/nextcloud-data/data/padmin/files/received_models/global_weights.pkl")


#Negotiate with clients for model weights
def negotiate_with_clients(offers, project_root):
    """EDC: Negotiate FL participation contracts with all clients."""
    conn_cfg = ConnectorConfig(project_root / "configs")
    rc_cfg = conn_cfg.get_research_centre_config()
    result = negotiate_edc_contracts(
        partners=offers,
        consumer_mgmt_url=rc_cfg['mgmt_url'],
        consumer_api_key=rc_cfg['api_key'],
        config_path=str(project_root / "configs"),
        asset_selector=select_offered_asset,
        agreement_builder=build_simple_agreement,
        operation_name="FL participation contract"
    )
    return {'agreements': result['agreements'], 'stats': result['stats']}

#create asset on global model
def create_rc_model_edc_asset(project_root):
    """EDC: Create asset registration for global model in RC connector."""
    conn_cfg = ConnectorConfig(project_root / "configs")
    rc_cfg = conn_cfg.get_research_centre_config()
    rc_mgmt = rc_cfg['mgmt_url']
    rc_id = rc_cfg['participant_id']
    asset = load_template(
        str(project_root / "configs/edc/asset.json"),
        ASSET_ID="rc-model-v0",
        DATASET_ID="global-model-v0", CLIENT_ID=rc_id,
        PRICE_INFO="0", TRAINING_ALLOWED="false", PROVIDER_NC=f"{rc_id}-nextcloud",
        remote_base_path="models", filename="global_weights.pkl", PROVIDER_ID=rc_id
    )
    policy = load_template(str(project_root / "configs/edc/policy.json"),
                           POLICY_ID="rc-model-policy-v0")
    contract = load_template(
        str(project_root / "configs/edc/contract.json"),
        CONTRACT_ID="rc-model-contract-v0", POLICY_ID="rc-model-policy-v0",
        CONTRACT_POLICY_ID="rc-model-policy-v0", ASSET_ID="rc-model-v0"
    )
    _create_edc_objects(rc_mgmt, asset, policy, contract, rc_cfg['api_key'])
    logger.info("RC model weights asset created")


#Receive trained model from client for async one by one
def _fetch_model_from_one_client(agreement, rc_mgmt, rc_nc, target_path, rc_cfg, client_dsp, api_key, project_root):
    client_id = agreement.get('client_id', 'unknown')
    asset_id = agreement['asset_id']
    agreement_id = agreement['agreement_id']
    filename = f"{client_id}_weights.pkl"
    dest_config = {
        "type": "Nextcloud",
        "baseUrl": f"http://{rc_nc}:80",
        "filePath": target_path,
        "keyName": "research-centre-key",
        "receiverHttpEndpoint": f"http://{rc_cfg['connector_hostname']}:{rc_cfg['mgmt_port']}/management"
    }
    
    init_start = time.time()
    init_result = initiate_transfer(
        rc_mgmt, client_dsp, agreement_id, asset_id,
        dest_config, api_key, str(project_root / "configs")
    )
    negotiation_time = time.time() - init_start
    
    transfer_id = init_result['transfer_id']
    logger.info(
        f"Fetching trained model from {client_id} | "
        f"asset: {asset_id} | file: {filename} | "
        f"agreement: {agreement_id} (transfer: {transfer_id})"
    )
    
    poll_start = time.time()
    poll_result = poll_transfer_status(rc_mgmt, transfer_id, api_key)
    total_transfer_time = time.time() - poll_start
    
    if poll_result['success']:
        logger.info(f"Trained model from {client_id} received")
        return {
            'success': True,
            'negotiation_time': negotiation_time,
            'transfer_time': total_transfer_time,
            'polling_time': poll_result['transfer_time'],
            'total_transfer_time': negotiation_time + total_transfer_time,
            'bytes_sent': init_result['bytes_sent'] + poll_result['bytes_sent'],
            'bytes_received': init_result['bytes_received'] + poll_result['bytes_received'],
            'num_messages': init_result['num_messages'] + poll_result['num_messages'] + 5,
        }
    else:
        raise RuntimeError(f"Failed to fetch trained model from {client_id}")

#Receive trained model from clienys together for sync
def fetch_trained_models_from_clients(project_root, trained_model_agreements, client_offers):
    if not trained_model_agreements:
        logger.warning("No trained model agreements")
        return {}
    conn_cfg = ConnectorConfig(project_root / "configs")
    rc_cfg = conn_cfg.get_research_centre_config()
    rc_mgmt = rc_cfg['mgmt_url']
    api_key = rc_cfg['api_key']
    rc_nc = f"{rc_cfg['participant_id']}-nextcloud"
    target_path = "received_trained_models"
    offer_map = {offer['client_id']: offer for offer in client_offers}
    nc = get_research_centre_nextcloud()
    nc.ensure_directory(target_path)
    stats = {}
    with ThreadPoolExecutor(max_workers=len(trained_model_agreements)) as executor:
        futures = {executor.submit(
            _fetch_model_from_one_client, agreement, rc_mgmt, rc_nc,
            target_path, rc_cfg,
            offer_map[agreement['client_id']]['provider_connector_protocol_url'],
            api_key, project_root): agreement
            for agreement in trained_model_agreements}
        for future in as_completed(futures):
            agreement = futures[future]
            stats[agreement['client_id']] = future.result()
    return stats

# Upload aggregated global model weights to research centre Nextcloud
def upload_model_to_rc_nextcloud(project_root, model_path):
    model = tf.keras.models.load_model(str(model_path))
    nc = get_research_centre_nextcloud()
    nc.upload_pickle(model.get_weights(), "models/global_weights.pkl")
