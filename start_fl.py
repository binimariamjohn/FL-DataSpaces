#!/usr/bin/env python3
"""FL startup script."""
import argparse
import subprocess
import sys
import time
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from fedLearning.utils.config_utils import UnifiedConfig
from fedLearning.utils.ns3_utils import setup_ns3_env_vars
from fedLearning.utils.metrics_collector import save_run_config
from dataset_utils.split_data import split_and_save_datasets
from dataspace.marketplace.marketplace_utils import publish_client_offer

parser = argparse.ArgumentParser(description="FL startup script")
parser.add_argument("--config-dir", type=str,
                    help="Path to custom config directory (overrides configs/)")
parser.add_argument("--exp-name", type=str,
                    help="Experiment name (for logging)")
CLI_ARGS, _ = parser.parse_known_args()

CONFIG_DIR = CLI_ARGS.config_dir
if CONFIG_DIR:
    import shutil
    src = Path(CONFIG_DIR)
    dst = PROJECT_ROOT / "configs"
    for cfg_file in ["datasetFactors.json", "networkingFactors.json",
                     "flFactors.json", "dataSpaceFactors.json"]:
        if (src / cfg_file).exists():
            shutil.copy2(src / cfg_file, dst / cfg_file)

def run_command(cmd):
    subprocess.run(cmd, shell=True)


def split_dataset():
    """Split and prepare dataset for clients"""
    config = UnifiedConfig().raw
    split_config = {
        "paths": config["paths"],
        "dataset_details": config["dataset_details"],
        "dataset_factors": config["dataset_factors"]
    }
    print("Splitting dataset...")
    split_and_save_datasets(split_config, PROJECT_ROOT)
    num_clients = config['dataset_factors']['num_clients']
    print(f"Dataset split for {num_clients} clients")

def setup_client_offers():
    """Publish training data offers from clients to marketplace"""
    import requests as _req
    print("\nWaiting for marketplace web app to be ready...")
    for attempt in range(60):
        try:
            r = _req.get("http://localhost:5001/offers", timeout=3)
            if r.status_code == 200:
                print("Marketplace ready.")
                break
        except Exception:
            pass
        time.sleep(3)
    else:
        raise RuntimeError("Marketplace webapp not reachable on localhost:5001 after 3 minutes")

    print("Publishing client offers...")
    config = UnifiedConfig().raw
    num_clients = config['dataset_factors']['num_clients']
    for client_id in range(1, num_clients + 1):
        publish_client_offer(client_id, PROJECT_ROOT)

    print(f"Published {num_clients} client offers")


def collect_all_container_logs(run_id, config):
    """Collect logs from all running containers into single file"""
    results_dir = PROJECT_ROOT / config['paths']['results_path'] / run_id
    results_dir.mkdir(parents=True, exist_ok=True)
    log_file = results_dir / "all_containers.log"

    print(f"\nCollecting logs from all containers → {log_file}")
    with open(log_file, "w") as f:
        result = subprocess.run(
            ["docker-compose", "logs", "--no-color"],
            capture_output=True, text=True, timeout=60,
            cwd=str(PROJECT_ROOT),
        )
        output = result.stdout + result.stderr
        f.write(output if output.strip() else "(no output)\n")

    print(f"Logs saved to {log_file}")

def get_services_for_num_clients(num_clients, with_edc=True):
    """Build list of docker-compose services needed for given number of clients"""
    services = []
    for i in range(1, num_clients + 1):
        services.extend([f"client-{i}-trainer"])
        if with_edc:
            services.extend([
                f"client-{i}-cloud-db",
                f"client-{i}-nextcloud",
                f"client-{i}-connector",
            ])
    # Shared services
    shared = ["rc-fl-server", "ns3-simulator"]
    if with_edc:
        shared = [
            "research-centre-cloud-db",
            "research-centre-nextcloud",
            "research-centre-connector",
            "marketplace-webapp",
        ] + shared
    services.extend(shared)
    return services


def main():
    # Load config upfront
    config = UnifiedConfig().raw
    
    if CLI_ARGS.exp_name:
        print(f"\nExperiment: {CLI_ARGS.exp_name}")

    # Prepare data first
    print("Splitting dataset before starting containers...")
    split_dataset()

    # Setup network environment
    print("\nSetting up NS3 environment variables...")
    run_id = setup_ns3_env_vars(config, CLI_ARGS.exp_name)

    # Record what we're running
    results_path = config['paths']['results_path']
    save_run_config(config, run_id, PROJECT_ROOT / results_path)

    # Figure out which services we need to start
    num_clients = config['dataset_factors']['num_clients']
    with_edc = config.get('mode', 'without-edc') == 'with-edc'
    services = get_services_for_num_clients(num_clients, with_edc=with_edc)
    services_str = " ".join(services)
    mode = 'with-edc' if with_edc else 'without-edc'
    print(f"\nStarting {num_clients} clients ({mode})")

    # Start containers
    print("\nCleaning up volumes...")
    run_command("docker-compose down -v")

    run_command(f"docker-compose up -d {services_str}")

    if with_edc:
        print("\nWaiting for containers to initialize...")
        time.sleep(60)
        setup_client_offers()
        print("Marketplace setup done.")
    else:
        print("\nWithout-EDC mode: FL server starting immediately.")
    
    # Watch training progress
    trainer_services = " ".join(f"client-{i}-trainer" for i in range(1, num_clients + 1))
    run_command(f"docker-compose logs -f rc-fl-server {trainer_services}")

    # Save everything once training is done
    collect_all_container_logs(run_id, config)

if __name__ == "__main__":
    main()
