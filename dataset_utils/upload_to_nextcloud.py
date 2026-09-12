#!/usr/bin/env python3
import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from dataspace.edc_utils import load_template
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_path):
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    return json.loads(config_path.read_text())

def upload_to_nextcloud_container(container_name, user, local_path, remote_base_path, create_archive=False):
    if not local_path.exists():
        logger.warning(f"Local path {local_path} does not exist. Skipping.")
        return

    nc_user_files_root = f"/var/www/html/data/{user}/files"
    dest_path = f"{nc_user_files_root}/{remote_base_path}"

    logger.info(f"Uploading to {container_name}: {local_path} -> {remote_base_path}")

    subprocess.run(f"docker exec {container_name} mkdir -p {dest_path}", shell=True, check=True)
    
    files_to_copy = [f for f in local_path.iterdir() if f.is_file()]
    if not files_to_copy:
        logger.warning(f"No files found in {local_path}")
        return

    for item in files_to_copy:
        subprocess.run(f"docker cp {item} {container_name}:{dest_path}/{item.name}", shell=True, check=True)

    subprocess.run(f"docker exec {container_name} chown -R www-data:www-data {dest_path}", shell=True, check=True)

    if create_archive:
        subprocess.run(f"docker exec {container_name} tar -cf {nc_user_files_root}/client_data.tar -C {nc_user_files_root} client_data", 
                       shell=True, check=True)
        subprocess.run(f"docker exec {container_name} mv {nc_user_files_root}/client_data.tar {dest_path}/client_data.tar", 
                       shell=True, check=True)
        subprocess.run(f"docker exec {container_name} chown www-data:www-data {dest_path}/client_data.tar", 
                       shell=True, check=True)

    logger.info(f"Upload complete for {container_name}")

def setup_edc_assets(provider_name, remote_base_path, api_key="password"):
    logger.info(f"Setting up EDC for {provider_name}")
    
    project_root = Path(__file__).resolve().parent.parent
    from dataspace.edc_utils import EDCConfig
    
    config = EDCConfig(str(project_root / "configs"))
    p_props = config.load_connector(provider_name)
    provider_mgmt = f"http://localhost:{p_props['web.http.management.port']}/management/v3"
    provider_id = provider_name.split('-')[0]
    
    asset = load_template(str(project_root / "configs/edc/asset.json"), ASSET_ID="asset_id", PROVIDER_NC=f"{provider_id}-nextcloud", PROVIDER_ID=provider_id, remote_base_path=remote_base_path, filename="client_data.tar")
    policy = load_template(str(project_root / "configs/edc/policy.json"), POLICY_ID="policy_id")
    contract = load_template(str(project_root / "configs/edc/contract.json"), CONTRACT_ID="contract_id", POLICY_ID="policy_id", CONTRACT_POLICY_ID="policy_id", ASSET_ID="asset_id")
    
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    
    requests.post(f"{provider_mgmt}/assets", json=asset, headers=headers)
    requests.post(f"{provider_mgmt}/policydefinitions", json=policy, headers=headers)
    requests.post(f"{provider_mgmt}/contractdefinitions", json=contract, headers=headers)
    
    logger.info(f"EDC setup complete for {provider_name}")

def upload_to_nextcloud(mode):
    project_root = Path(__file__).resolve().parent.parent
    config_dir = project_root / "configs"
    
    edc_cfg = load_config(config_dir / "dataSpaceFactors.json")
    dataset_cfg = load_config(config_dir / "datasetFactors.json")

    dataset_path_str = dataset_cfg.get("paths", {}).get("dataset_path")
    train_dir_name = dataset_cfg.get("dataset_details", {}).get("dataset_split", {}).get("training_dataset_dir")
    train_path = (project_root / dataset_path_str / train_dir_name).resolve()

    if not train_path.exists():
        logger.error(f"Training data directory not found: {train_path}")
        return

    logger.info(f"Starting upload in '{mode}' mode")

    if mode == "with-edc":
        providers = edc_cfg.get("edc", {}).get("providers_connectors", [])
        for i, provider in enumerate(providers):
            client_folder = train_path / f"client_{i + 1}"
            if not client_folder.exists():
                continue
            
            upload_to_nextcloud_container(
                container_name=provider.get("nextcloud_container"),
                user="padmin",
                local_path=client_folder,
                remote_base_path="client_data",
                create_archive=True
            )
            setup_edc_assets(provider_name=provider.get("name"), remote_base_path="client_data")

    elif mode == "without-edc":
        for client_folder in sorted(train_path.glob("client_*")):
            try:
                client_id = int(client_folder.name.split('_')[1])
                upload_to_nextcloud_container(
                    container_name=f"rc{client_id}-nextcloud",
                    user="cadmin",
                    local_path=client_folder,
                    remote_base_path="client_data",
                    create_archive=False
                )
            except (IndexError, ValueError, subprocess.CalledProcessError) as e:
                logger.error(f"Failed to upload {client_folder.name}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload data to Nextcloud containers.")
    parser.add_argument("--mode", choices=["with-edc", "without-edc"], required=True, help="Upload mode")
    args = parser.parse_args()
    
    upload_to_nextcloud(args.mode)
