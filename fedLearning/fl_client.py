#!/usr/bin/env python3
import json
import logging
import os
import sys
import time
import numpy as np
from pathlib import Path

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests

from fedLearning.utils.config_utils import UnifiedConfig
from fedLearning.models import create_and_compile_model, serialize_weights, deserialize_weights
from dataspace.nextcloud_utils import get_client_nextcloud
from fedLearning.utils.fl_client_trainer import FLClientTrainer

# Load config once
config = UnifiedConfig().raw
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_NUM = CLIENT_ID.replace("client-", "").replace("client", "")

IS_ASYNC = config.get('federated', {}).get('aggregation', 'fedavg').lower() in ('fedasync', 'fedavg_async') or \
           config.get('network', {}).get('mode', 'sync') == 'async'
WITH_EDC = config['mode'] == 'with-edc'
SERVER_URL = f"http://{config['federated']['server_host']}:{config['federated']['server_port']}"

logging.basicConfig(level=logging.INFO, format=f"%(asctime)s | {CLIENT_ID} | %(message)s")
logger = logging.getLogger(f"fl_client_{CLIENT_ID}")
session = requests.Session()

def load_client_data():
    # Load local client training/validation data from dataset split
    dataset_config = config['dataset_details']
    paths_config = config['paths']
    
    dataset_folder = dataset_config['dataset_name']
    dataset_base = paths_config['dataset_path']
    if not dataset_base.startswith('/'):
        dataset_base = f"/data/{dataset_folder}"
    else:
        dataset_base = f"{dataset_base}/{dataset_folder}"
    
    train_dir = dataset_config['dataset_split']['training_dataset_dir']
    data_path = Path(f"{dataset_base}/{train_dir}/client_{CLIENT_NUM}")
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data not found: {data_path}")

    images = np.load(data_path / "images.npz")["images"]
    labels = np.load(data_path / "labels.npz")["labels"]

    n_train = int(0.8 * len(images))
    X_train, y_train = images[:n_train], labels[:n_train]
    X_val, y_val = images[n_train:], labels[n_train:]

    logger.info(f"Loaded {len(images)} samples → train={len(X_train)}, val={len(X_val)}")
    return X_train, y_train, X_val, y_val

def get_model_from_server():
    # Fetch current global model weights from server
    t0 = time.time()
    r = session.get(f"{SERVER_URL}/get_model", timeout=30)
    r.raise_for_status()
    data = r.json()
    return deserialize_weights(data["model_weights"]), data.get("round", 0), time.time() - t0

def save_trained_model_to_nextcloud(weights):
    # Upload trained model weights to client Nextcloud storage
    nc = get_client_nextcloud(int(CLIENT_NUM))
    nc.upload_pickle(weights, f"trained_models/{CLIENT_ID}_weights.pkl")


def wait_for_server():
    # Poll server health endpoint until ready
    for _ in range(260):
        try:
            r = session.get(f"{SERVER_URL}/health", timeout=5)
            if r.status_code == 200:
                logger.info(f"Server ready (mode={r.json().get('mode')})")
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def wait_for_round(expected_round):
    # Poll server until current round is ready
    while True:
        try:
            r = session.get(f"{SERVER_URL}/round_status", timeout=30)
            if r.status_code == 200:
                st = r.json()
                if st.get("training_complete"):
                    return None
                if st.get("current_round", 0) >= expected_round and st.get("model_ready"):
                    return st["current_round"]
        except Exception:
            pass
        time.sleep(1)

def submit_update(round_or_iter, trained_weights, num_samples, train_metrics, upload_time=0.0, upload_bytes=0, upload_completion_timestamp=None):
    # Send trained model update and metrics to server
    payload = {
        "client_id": CLIENT_ID,
        "round": round_or_iter,
        "iteration": round_or_iter,
        "num_samples": num_samples,
        "metrics": train_metrics,
        "upload_time": upload_time,
        "upload_bytes": upload_bytes,
        "upload_completion_timestamp": upload_completion_timestamp,
    }
    if not WITH_EDC:
        payload["model_weights"] = serialize_weights(trained_weights)

    r = session.post(f"{SERVER_URL}/submit_update", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()

def train_round(model, X_train, y_train, X_val, y_val, round_label):
    # Train model for one round/iteration and return metrics
    logger.info(f"Training {round_label}")
    train_start_time = time.time()
    hist = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=config['federated']['local_epochs'],
        batch_size=config['federated']['batch_size'],
        verbose=0,
    )
    train_duration = time.time() - train_start_time
    
    return {
        "loss": float(hist.history["loss"][-1]),
        "accuracy": float(hist.history["accuracy"][-1]),
        "val_loss": float(hist.history["val_loss"][-1]),
        "val_accuracy": float(hist.history["val_accuracy"][-1]),
        "local_training_duration": train_duration,
        "local_training_start_time": train_start_time,
        "local_training_end_time": train_start_time + train_duration,
    }


def main():
    # Initialize client, load data, and run federated training
    if not wait_for_server():
        logger.error("Server unavailable")
        sys.exit(1)

    X_train, y_train, X_val, y_val = load_client_data()
    model = create_and_compile_model(
        input_shape=tuple(config['input_shape']),
        learning_rate=config['federated']['learning_rate']
    )
    
    logger.info(f"Starting {'ASYNC' if IS_ASYNC else 'SYNC'} training")

    trainer = FLClientTrainer(
        model, X_train, y_train, X_val, y_val, IS_ASYNC, WITH_EDC,
        client_id=CLIENT_ID, client_num=CLIENT_NUM, project_root=PROJECT_ROOT,
        num_rounds=config['federated']['rounds'],
        get_model_from_server=get_model_from_server,
        save_trained_model_to_nextcloud=save_trained_model_to_nextcloud,
        train_round=train_round,
        submit_update=submit_update,
        wait_for_round=wait_for_round,
    )
    trainer.run()
    logger.info("Training complete")


if __name__ == "__main__":
    main()
