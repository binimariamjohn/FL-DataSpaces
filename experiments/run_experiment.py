#!/usr/bin/env python3
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIGS_DIR = PROJECT_ROOT / "configs"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


# Factors live next to this script
factors = load_json(SCRIPT_DIR / "experimentFactors.json")

# Base configs live under configs/ (some may not exist, that's fine)
base_configs = {}
for name in ("networkingFactors", "flFactors", "datasetFactors", "dataSpaceFactors"):
    cfg_path = CONFIGS_DIR / f"{name}.json"
    if cfg_path.exists():
        base_configs[name] = load_json(cfg_path)

# Builds a temp config folder for one run, calls start_fl.py, and cleans up.
def merge_and_run(mode: str, scenario_name: str, num_clients: int, scenario: dict) -> bool:

    exp_name = f"{mode}_{num_clients}c_{scenario_name}"
    temp_dir = PROJECT_ROOT / f".exp_{exp_name}"
    temp_dir.mkdir(exist_ok=True)

    try:
        # --- networkingFactors.json ---
        net_cfg = deepcopy(base_configs.get("networkingFactors", {}))
        net_cfg.update(scenario["network"])
        net_cfg["mode"] = scenario["algorithm"]["mode"]
        write_json(temp_dir / "networkingFactors.json", net_cfg)

        # --- flFactors.json ---
        fl_cfg = deepcopy(base_configs.get("flFactors", {}))
        fl_cfg["mode"] = mode
        if "federated" in fl_cfg:
            fl_cfg["federated"]["aggregation"] = scenario["algorithm"]["aggregation"]
        write_json(temp_dir / "flFactors.json", fl_cfg)

        # --- datasetFactors.json ---
        ds_cfg = deepcopy(base_configs.get("datasetFactors", {}))
        if ds_cfg.get("dataset_factors"):
            ds_cfg["dataset_factors"][0]["num_clients"] = num_clients
            ds_cfg["dataset_factors"][0]["fairness_ratios"] = scenario["fairness_ratios"]
            ds_cfg["dataset_factors"][0]["distribution"] = scenario["distribution"]
        write_json(temp_dir / "datasetFactors.json", ds_cfg)

        # --- dataSpaceFactors.json (kept as-is) ---
        ds_space_cfg = deepcopy(base_configs.get("dataSpaceFactors", {}))
        write_json(temp_dir / "dataSpaceFactors.json", ds_space_cfg)

        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "start_fl.py"),
                "--config-dir",
                str(temp_dir),
                "--exp-name",
                exp_name,
            ],
            cwd=str(PROJECT_ROOT),
        )
        return result.returncode == 0

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def main() -> None:
    factor_defs = factors["factor_definitions"]
    experiments = factors["experiments"]  # e.g. ["with-edc", "without-edc"]
    num_clients_list = factors["datasetFactors"]["num_clients"]
    scenarios = factors["scenarios"]

    total = len(experiments) * len(num_clients_list) * len(scenarios)
    count = 0

    for nc in num_clients_list:
        for scenario_combo in scenarios:
            net_key, algo_key, rate_key, fair_key = scenario_combo
            scenario_name = f"{net_key}_{algo_key}_{rate_key}_{fair_key}"

            net_cfg = factor_defs["network"][net_key].copy()
            net_cfg.update(factor_defs["data_rate"][rate_key])
            fairness_ratios = factor_defs["fairness"][fair_key][str(nc)]

            scenario = {
                "network": net_cfg,
                "algorithm": factor_defs["algorithm"][algo_key].copy(),
                "fairness_ratios": fairness_ratios,
                "distribution": fair_key,
            }

            for mode in experiments:
                count += 1
                print(f"Experiment {count}/{total}: {nc}c | {scenario_name} | {mode}")

                success = merge_and_run(mode, scenario_name, nc, scenario)
if __name__ == "__main__":
    main()