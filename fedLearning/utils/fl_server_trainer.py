import logging
import os
import sys
import threading
import time
from pathlib import Path

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

from fedLearning.models import create_and_compile_model, serialize_weights, deserialize_weights
from fedLearning.utils.config_utils import UnifiedConfig
from fedLearning.utils.fl_aggregation import fedavg, fedavg_async
from fedLearning.utils.fl_server_utils import (
    save_initial_model, test_model, _get_num_samples, setup_without_edc
)
from fedLearning.utils.fl_edc_utils import (
    negotiate_with_clients, upload_model_to_rc_nextcloud,
    create_rc_model_edc_asset, fetch_trained_models_from_clients
)
from fedLearning.utils.metrics_collector import MetricsCollector, TimingContext
from dataspace.marketplace.marketplace_utils import discover_clients
from dataspace.nextcloud_utils import load_trained_weights_from_nextcloud
import ns3_coordinator


class FLTrainer:

    def __init__(self, config=None, project_root=None):
        self.project_root = project_root or Path(__file__).resolve().parent.parent.parent
        self.config = config or UnifiedConfig().raw
        self.logger = logging.getLogger("fl_server")
        sys._fedasync_logger = self.logger
        
        # Training configuration
        self.mode = self.config.get('mode', 'without-edc')
        self.num_clients = self.config['dataset_factors']['num_clients']
        self.num_rounds = self.config['federated']['rounds']
        self.local_epochs = self.config['federated']['local_epochs']
        self.batch_size = self.config['federated']['batch_size']
        self.learning_rate = self.config['federated']['learning_rate']
        self.server_port = self.config['federated'].get('server_port', 9091)
        self.fairness_ratios = self.config['dataset_factors'].get('fairness_ratios', [])
        self.total_training_samples = self.config['dataset_factors'].get('dataset_size', 60000)
        
        # Training mode
        self.aggregation = self.config['federated'].get('aggregation', 'fedavg')
        self.is_async = self.aggregation.lower() in ('fedasync', 'fedavg_async')
        self.with_edc = self.mode == 'with-edc'
        
        # NS3 network simulator
        self.ns3_host = self.config.get('network', {}).get('host', 'ns3-simulator')
        self.ns3_port = self.config.get('network', {}).get('ns3_port', 9099)
        
        # Runtime state
        self.run_id = os.environ.get('RUN_ID', 
                                     __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S'))
        self.metrics_dir = self.project_root / self.config['paths']['results_path'] / self.run_id
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        self.metrics = MetricsCollector(self.metrics_dir, setup_type="edc" if self.with_edc else "direct")
        self.global_model = None
        self.model_path_global = None
        
        # Sync training state
        self.current_round = 0
        self.training_complete = False
        self.model_ready = False
        self.lock = threading.Lock()
        self.round_done = threading.Event()
        self.client_updates = {}
        
        # Async training state
        self.global_version = 0
        self.client_versions = {}
        self.total_async_updates = 0
        self.client_async_iterations = {}
        
        # EDC state
        self.trained_model_agreements = []
        self.client_offers = []

    def setup(self):
        self.logger.info(
            f"FL Trainer | mode={self.mode} | strategy={'ASYNC' if self.is_async else 'SYNC'} | "
            f"rounds={self.num_rounds} | clients={self.num_clients} | "
            f"ns3={self.ns3_host}:{self.ns3_port}"
        )
        
        # Create and save initial model
        self.global_model = create_and_compile_model(
            input_shape=tuple(self.config['input_shape']), 
            learning_rate=self.learning_rate
        )
        self.model_path_global = save_initial_model(self.project_root, self.learning_rate)
        
        # Setup data exchange mode
        if self.with_edc:
            self._setup_edc()
        else:
            self._setup_direct()
        
        # Connect to network simulator
        self.logger.info(f"Connecting to NS3 at {self.ns3_host}:{self.ns3_port}...")
        ns3_coordinator.init(self.ns3_host, self.ns3_port, use_ns3=True)
        ns3_coordinator.connect()

    #Discover clients via marketplace, negotiate EDC contracts, create RC model asset
    def _setup_edc(self):
        self.logger.info("Setting up EDC contracts for model exchange...")
        self.client_offers[:] = discover_clients(self.num_clients, self.logger)
        data_neg = negotiate_with_clients(self.client_offers, self.project_root)
        self.trained_model_agreements[:] = data_neg['agreements']
        upload_model_to_rc_nextcloud(self.project_root, self.model_path_global)
        create_rc_model_edc_asset(self.project_root)
        self.logger.info(f"EDC setup complete: {len(self.trained_model_agreements)} agreements")

    #Setup direct HTTP mode - populate client list without EDC
    def _setup_direct(self):
        self.logger.info("Setting up direct HTTP communication mode...")
        setup_without_edc(self.client_offers, self.num_clients)

    #Synchronous training run
    def run_fedsync(self):
        self.logger.info("Starting SYNCHRONOUS Federated Learning Training...")
        
        for rnd in range(1, self.num_rounds + 1):
            self._sync_round(rnd)
        
        self.training_complete = True
        self.logger.info(f"Training complete ({self.num_rounds} rounds)")
        ns3_coordinator.send_exit()
        time.sleep(5)
        os._exit(0)

    # Sync One round: wait for all clients, fetch models, aggregate, evaluate, log
    def _sync_round(self, rnd):

        # PHASE 1: Initialize round and notify network simulator

        round_start = time.time()
        self.current_round = rnd

        with self.lock:
            self.client_updates = {}  
            self.round_done.clear()  
        
        ns3_coordinator.send_round_start(self.num_clients, self.num_clients, list(range(self.num_clients)))
        
        self.model_ready = True
        self.logger.info(f"[SYNC Round {rnd}/{self.num_rounds}] Waiting for {self.num_clients} clients...")
        

        # PHASE 2: Wait for clients and fetch models
        if not self.round_done.wait(timeout=1200):
            self.logger.warning(f"Round {rnd}: timeout — received {len(self.client_updates)}/{self.num_clients}")
            return
        self.model_ready = False
    
        if self.with_edc:
            # EDC MODE: Models were uploaded by clients to Nextcloud via EDC contracts
            self.logger.info(f"[SYNC Round {rnd}] Fetching trained models via EDC...")
            with TimingContext():
                fetch_trained_models_from_clients(
                    self.project_root, self.trained_model_agreements, self.client_offers)
            # Load weights from Nextcloud for each client and store in client_updates dict
            for cid in self.client_updates.keys():
                weights = load_trained_weights_from_nextcloud(cid)
                self.client_updates[cid]["weights"] = weights
        else:
            # DIRECT MODE: Weights already in client_updates dict (sent by client in HTTP request)
            pass
        
        # PHASE 4: Aggregated
        self.logger.info(f"[SYNC Round {rnd}] Aggregating {len(self.client_updates)} clients (FedAvg)...")
        with TimingContext():
            #fedavg calling
            agg_ok = fedavg(self.client_updates, self.global_model)
        
        if not agg_ok:
            self.logger.error(f"Round {rnd}: aggregation failed!")
            return
        accuracy, loss = test_model(self.project_root, self.global_model.get_weights(), self.config)
        round_time = time.time() - round_start
        self.logger.info(
            f"Round {rnd}/{self.num_rounds}: accuracy={accuracy:.4f}, loss={loss:.4f}, time={round_time:.1f}s"
        )

        ns3_coordinator.receive_round_stats(self.num_clients)  # Send round summary to NS3 simulator
        self.metrics.log_model_performance(rnd, loss, accuracy, round_time)  # Append to CSV
        self.model_path_global = save_initial_model(
            self.project_root, self.learning_rate, self.global_model.get_weights(), rnd
        )
        
        # Upload updated global model to research centre for next round
        if self.with_edc:
            upload_model_to_rc_nextcloud(self.project_root, self.model_path_global)


    def handle_sync_update(self, client_id, round_num, data):
        if round_num != self.current_round:
            return {"status": "ignored", "reason": "round mismatch"}, 409
        
        with self.lock:
            if client_id in self.client_updates:
                return {"status": "ignored", "reason": "duplicate"}, 400
            
            num_samples = int(data.get("num_samples", _get_num_samples(client_id, self)))
            
            if self.with_edc:
                self.client_updates[client_id] = {
                    "num_samples": num_samples,
                    "metrics": data.get("metrics", {}),
                    "staleness": 0,
                }
            else:
                self.client_updates[client_id] = {
                    "weights": deserialize_weights(data["model_weights"]),
                    "num_samples": num_samples,
                    "metrics": data.get("metrics", {}),
                    "staleness": 0,
                }
            
            if len(self.client_updates) >= self.num_clients:
                self.round_done.set()
        
        return {"status": "received"}, 200


    #async training
    def run_fedasync(self):
        self.logger.info("Starting ASYNCHRONOUS Federated Learning Training...")
        self.logger.info("Waiting for async client updates...")

    def handle_async_update(self, client_id, iteration, data):
        with self.lock:
            #Calculate stalness
            staleness = self.global_version - self.client_versions.get(client_id, 0)
            
            #Fetch model weights
            if self.with_edc:
                self.logger.info(f"[Async] Fetching trained model from {client_id} via EDC...")
                agreement = next((a for a in self.trained_model_agreements if a['client_id'] == client_id), None)
                offer = next((o for o in self.client_offers if o['client_id'] == client_id), None)
                with TimingContext():
                    fetch_trained_models_from_clients(
                        self.project_root, [agreement], [offer]
                    )
                    weights = load_trained_weights_from_nextcloud(client_id)

            else:
                weights = deserialize_weights(data["model_weights"])
            
            #aggregation
            num_samples = int(data.get("num_samples", _get_num_samples(client_id, self)))
            updates = {client_id: {
                "weights": weights,
                "num_samples": num_samples,
                "staleness": staleness, 
            }}

            with TimingContext():
                fedavg_async(updates, self.global_model,
                            alpha_init=0.6, staleness_fn='polynomial',
                            current_round=self.total_async_updates)
            
            self.global_version += 1
            self.client_versions[client_id] = self.global_version
            self.total_async_updates += 1
            self.client_async_iterations[client_id] = iteration
            
            #Test model
            accuracy, loss = test_model(self.project_root, self.global_model.get_weights(), self.config)
            self.logger.info(
                f"[Async {self.total_async_updates}] {client_id} (iter={iteration}, "
                f"staleness={staleness}): accuracy={accuracy:.4f}, loss={loss:.4f}"
            )
            self.metrics.log_model_performance(self.total_async_updates, loss, accuracy, 0)
            
            model_path = save_initial_model(self.project_root, self.learning_rate, 
                             self.global_model.get_weights(), self.total_async_updates)
            
            # Upload updated global model so next async client gets fresh version (only in EDC mode)
            if self.with_edc:
                upload_model_to_rc_nextcloud(self.project_root, model_path)
            
            #Check if training is complete
            if len(self.client_async_iterations) == self.num_clients:
                if all(it >= self.num_rounds for it in self.client_async_iterations.values()):
                    self.training_complete = True
                    self.global_model.save(str(self.metrics_dir / "final_model.keras"))
                    self.logger.info("Async training complete")
                    ns3_coordinator.send_exit()
                    threading.Timer(5.0, lambda: os._exit(0)).start()
            
            response = {
                "status": "aggregated",  # Successfully aggregated
                "version": self.global_version,  # New global version client should expect
                "training_complete": self.training_complete,  # Signal if training done
            }
            if not self.with_edc:
                response["model_weights"] = serialize_weights(self.global_model)
            
            return response, 200
