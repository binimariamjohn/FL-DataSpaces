import csv
import json
import time
from pathlib import Path
from datetime import datetime


class MetricsCollector:

    def __init__(self, output_dir, setup_type="direct"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.setup_type = setup_type  # "edc" or "direct"

        self.model_perf_file = self.output_dir / "model_performance.csv"

    def log_model_performance(self, round_num, test_loss, test_accuracy, round_time=0.0):
        with open(self.model_perf_file, 'a', newline='') as f:
            csv.writer(f).writerow([
                round_num,
                f"{test_loss:.6f}",
                f"{test_accuracy:.6f}",
                f"{round_time:.2f}",
                datetime.now().isoformat(),
            ])


class TimingContext:

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time


def save_run_config(config, run_id, output_dir):
    # Dump final run configuration to JSON file
    fed = config['federated']
    net = config.get('network', {})
    ds_factors = config['dataset_factors']
    ds_details = config['dataset_details']

    run_config = {
        "with_edc": config['mode'] == 'with-edc',
        "algo": fed['aggregation'],
        "mode": net['mode'],
        "clients": ds_factors['num_clients'],
        "rounds": fed['rounds'],
        "local_epochs": fed['local_epochs'],
        "batch_size": fed['batch_size'],
        "learning_rate": fed['learning_rate'],
        "fairness_ratio": ds_factors['fairness_ratios'],
        "distribution": ds_factors['distribution'],
        "network": net['type'],
        "datarate": f"{net['client_data_rate_kbps']}kbps",
        "dataset": ds_details['dataset_name'],
        "run_id": run_id,
    }

    results_dir = Path(output_dir) / run_id
    results_dir.mkdir(parents=True, exist_ok=True)
    config_path = results_dir / "run_config.json"

    with open(config_path, "w") as f:
        json.dump(run_config, f, indent=2)

    print(f"Run config saved to {config_path}")
