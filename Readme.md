# Federated Learning with Data Spaces and NS-3 Network Simulation

This project implements a Federated Learning (FL) pipeline in which model weights are exchanged between clients and a research-centre server through a **Data Space layer** rather than direct network transfer. EDC (Eclipse Dataspace Connector) is used as the Data Space implementation, Nextcloud as an EDC extension for file storage/transfer, and NS-3 to simulate network conditions between participants.

> Note: This README documents the current technical implementation. The specific research question/thesis topic this codebase is being used for is being finalized separately and will be added here once confirmed.

# Key Features
  - Data Space Layer: EDC connectors and Nextcloud for sovereign, contract-governed model exchange.
  - Federated Learning implementation with model exchange through EDC or direct HTTP (configurable).
  - Synchronous (FedAvg) and asynchronous (FedAsync) aggregation strategies.
  - CNN model for image classification on MNIST/Fashion-MNIST dataset (used as a stand-in for real multi-partner data).
  - NS-3 integration to simulate network conditions (e.g., WiFi/Ethernet) between clients and server.

<img src="./resources/system_architecture.png" alt="System Architecture" width="800">
  
## Repository Structure

```
├── configs/
│   ├── flFactors.json
│   ├── datasetFactors.json
│   ├── networkingFactors.json
│   ├── dataSpaceFactors.json
│   └── edc/
│   └── resources/
├── dataset_utils/
│   ├── prepare_dataset.py
│   ├── split_data.py
│   └── upload_to_nextcloud.py
├── dataspace/
│   ├── connector_config.py
│   ├── edc-ionos-nextcloud-extension
│   ├── edc_negotiation.py
│   ├── edc_utils.py
│   ├── marketplace/
│   ├── nextcloud_utils.py
├── fedLearning/
│   ├── fl_server.py
│   ├── fl_client.py
│   ├── models.py
│   └── utils/
│       ├── fl_aggregation.py
│       ├── fl_server_utils.py
│       ├── fl_edc_utils.py
│       ├── fl_server_trainer.py
│       ├── fl_client_trainer.py
│       ├── fl_utils.py
│       ├── config_utils.py
│       └── metrics_collector.py
├── ns3-fl-network/
├── docker-compose.yml
├── start_fl.py
└── requirements.txt
```

## Setup

### 1. Python Environment
```bash
pip install -r requirements.txt
```
Recommended: Python 3.11 (pinned dependency versions may fail to build on newer versions on some platforms).

### 2. Build Docker Images
```bash
# EDC connector image
cd dataspace
chmod +x ./gradlew
./gradlew clean build
docker build -t edc-ionos-nextcloud:1.0 .
cd ..

# FL + NS3 images
# NOTE: `docker-compose build` with no arguments builds ALL client trainers
# (client-1 .. client-10), which is slow and produces many large (~20GB) images.
# Only build the services you actually need for your experiment, e.g.:
docker compose build ns3-simulator rc-fl-server client-1-trainer marketplace-webapp
```

### 3. Prepare Dataset
Downloads dataset into `data/` (path configured via `configs/datasetFactors.json`).
```bash
py dataset_utils/prepare_dataset.py
```

## Verified Smoke Test

A minimal one-client end-to-end run has been verified to work with the `with-edc` / `fedasync` pipeline (Marketplace → EDC contract negotiation → Nextcloud model transfer → local training → EDC-mediated upload → server-side FedAsync aggregation).

Smoke-test configuration used (`configs/flFactors.json` / `configs/datasetFactors.json`):
```json
"federated": {
  "rounds": 1,
  "local_epochs": 1,
  "batch_size": 64,
  "aggregation": "fedasync"
}
```
```json
"dataset_factors": [
  { "num_clients": 1, "partition_size": 10000, "distribution": "iid", "fairness_ratios": [1] }
]
```

Run it with:
```bash
docker compose down -v --remove-orphans
python start_fl.py --exp-name smoke-test
```

Expected result: both `rc-fl-server` and `client-1-trainer` containers exit with code `0`, and a log/metrics file is written to `results/<exp-name>/`.

### Notes from getting this to run reliably

- **Docker volume paths must be repo-relative bind mounts**, e.g. `./data:/data`. A source path like `data/` (no `./` or `/` prefix) is interpreted by Docker Compose as a *named volume reference*, not a bind mount, and will fail with `refers to undefined volume` if that name isn't declared under top-level `volumes:`. This affects `configs/datasetFactors.json`'s `results_path`/`logs_path` values as well as the Compose file's `volumes:` entries.
- **`start_fl.py` must be run from the host**, not inside a container — it invokes `docker-compose`/`docker compose` itself.
- **NS-3 compiles ~1,750 tasks in C++** and can exhaust Docker Desktop's memory limit if built with default parallelism. `docker-images/Dockerfile.ns3` builds with `python3 ./waf build -j1` to avoid this (slower, but memory-safe).
- **Full-scale training (60k samples, multiple rounds/epochs) can OOM-kill the trainer container** (exit code 137) depending on available Docker Desktop memory. The reduced smoke-test config above (10k samples, 1 round, 1 epoch) is a safe way to validate the pipeline before scaling up for real experiments.
- **`docker compose build` with no service names builds all 10 client trainer images** (`client-1-trainer` … `client-10-trainer`), each several GB, even if only one client is used. Always pass explicit service names when building.

## Running an Experiment

`start_fl.py` is the single entry point. It:
1. Splits the dataset for the configured number of clients
2. Sets NS-3 environment variables
4. Starts only the Docker services needed (scales with `num_clients`)
5. In `with-edc` mode: waits for the marketplace web app and publishes client offers
6. Starts the training in FL loop with transfer through EDC depending on the mode in config file.

```bash
python3 start_fl.py
```

## How it works

### With-EDC mode

Here we introduce the **Data Space layer using EDC + Nextcloud**.

- Each client has its **own EDC connector and its own Nextcloud storage**.
- The Research Centre (RC) also has its **own EDC connector and Nextcloud**.

Model exchange now happens through **EDC-managed transfers**:

- **RC → Client (global model)**  
  The client acts as the **EDC consumer**.  
  Its connector initiates a `Nextcloud-PUSH` transfer.  
  This triggers the RC connector to **push `global_weights.pkl` as a filetransfer into the client’s Nextcloud**.

- **Client → RC (trained model)**  
  The RC acts as the **EDC consumer**.  
  Its connector initiates a `Nextcloud-PUSH` transfer.  
  This triggers the client connector to **push `{client_id}_weights.pkl` as a filetransfer into the RC’s Nextcloud**.

### Without-EDC mode

In this mode the model weights are exchanged directly between clients and the server via GET/POST requests:

- Clients train locally and send their model weights directly in the HTTP `submit_update` request.
- The server aggregates and sends back the updated global model in the `get_model` response.

### Aggregation Strategies

| Strategy | Config value | Behaviour |
|---|---|---|
| FedAvg (sync) | `"aggregation": "fedavg"` + `"mode": "sync"` | Wait for all clients each round, then aggregate |
| FedAsync | `"aggregation": "fedasync"` or `"mode": "async"` | Aggregate immediately on each client update |

## References :

- EDC-Nextcloud extension: https://github.com/Digital-Ecosystems/edc-ionos-nextcloud
- NS3-FL : https://github.com/eekaireb/ns3-fl