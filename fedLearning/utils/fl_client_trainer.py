#!/usr/bin/env python3
import logging
import os
import time
from pathlib import Path

from fedLearning.models import get_weights_size
from fedLearning.utils.fl_edc_utils import negotiate_model_receive_contract, receive_global_model_via_edc

logger = logging.getLogger(__name__)


class FLClientTrainer:

    def __init__(self, model, X_train, y_train, X_val, y_val, is_async, with_edc,
                 *, client_id, client_num, project_root, num_rounds,
                 get_model_from_server, save_trained_model_to_nextcloud,
                 train_round, submit_update, wait_for_round):
        self.model = model
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.is_async = is_async
        self.with_edc = with_edc
        self.client_id = client_id
        self.client_num = client_num
        self.project_root = project_root
        self.num_rounds = num_rounds
        self.model_agreement_id = None
        self.current_round = 0

        self._get_model_from_server = get_model_from_server
        self._save_trained_model_to_nextcloud = save_trained_model_to_nextcloud
        self._train_round = train_round
        self._submit_update = submit_update
        self._wait_for_round = wait_for_round

        from fedLearning.utils.config_utils import UnifiedConfig
        self.config = UnifiedConfig().raw

    #Get weights from server through EDC or direct HTTP
    def get_weights(self):
        if self.with_edc:
            return receive_global_model_via_edc(
                self.project_root, self.client_num, self.client_id, self.model_agreement_id)
        else:
            weights, _, model_dist_time = self._get_model_from_server()
            return weights

    #training for one round
    def train_iteration(self, weights, iteration_num):
        self.model.set_weights(weights)
        label = f"iter {iteration_num}" if self.is_async else f"round {iteration_num}"
        metrics = self._train_round(
            self.model, self.X_train, self.y_train, self.X_val, self.y_val, label)
        return metrics

    #submit weight updates to server through EDC or direct HTTP
    def submit_update(self, iteration_num, metrics):
        trained_weights = self.model.get_weights()

        upload_time = 0.0
        upload_bytes = 0
        upload_completion_timestamp = None
        if self.with_edc:
            t0 = time.time()
            self._save_trained_model_to_nextcloud(trained_weights)
            upload_time = time.time() - t0
            upload_completion_timestamp = time.time()
            upload_bytes = get_weights_size(trained_weights)

        return self._submit_update(iteration_num, trained_weights, len(self.X_train), metrics,
                                   upload_time=upload_time, upload_bytes=upload_bytes,
                                   upload_completion_timestamp=upload_completion_timestamp)

    def run(self):
        if self.with_edc:
            self.model_agreement_id = negotiate_model_receive_contract(
                self.project_root, self.client_num, self.client_id)

        iteration = 0
        while iteration < self.num_rounds:
            iteration += 1

            if not self.is_async:
                current = self._wait_for_round(iteration)
                if current is None:
                    break

            self.current_round = iteration
            weights = self.get_weights()
            metrics = self.train_iteration(weights, iteration)

            response = self.submit_update(iteration, metrics)

            if response.get('training_complete'):
                break

        mode = "ASYNC" if self.is_async else "SYNC"
        logger.info(f"{mode} training complete")
