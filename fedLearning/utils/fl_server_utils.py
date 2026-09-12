import logging
import numpy as np
from pathlib import Path

from fedLearning.models import create_and_compile_model

logger = logging.getLogger(__name__)


def save_initial_model(project_root, learning_rate=0.01, weights=None, round_num=0):
    model = create_and_compile_model(learning_rate=learning_rate)
    if weights is not None:
        model.set_weights(weights)
    public_models_dir = project_root / "public" / "models"
    public_models_dir.mkdir(parents=True, exist_ok=True)
    model_path = public_models_dir / (f"global_model_round{round_num}.h5" if round_num else "global_model.h5")
    model.save(model_path)
    return model_path


def test_model(project_root, weights, config):
    dataset_folder = config['dataset_details']['dataset_name']
    dataset_base = config['paths']['dataset_path']
    if not dataset_base.startswith('/'):
        dataset_base = f"/data/{dataset_folder}"
    else:
        dataset_base = f"{dataset_base}/{dataset_folder}"
    
    test_dir = config['dataset_details']['dataset_split']['global_test_dir']
    test_data_path = Path(dataset_base) / test_dir
    
    images = np.load(test_data_path / "images.npz")["images"]
    labels = np.load(test_data_path / "labels.npz")["labels"]
    
    model = create_and_compile_model()
    model.set_weights(weights)
    loss, accuracy = model.evaluate(images, labels, verbose=0)
    return accuracy, loss


def _get_num_samples(client_id, trainer):
    idx = next(
        (i for i, o in enumerate(trainer.client_offers) if o.get('client_id') == client_id),
        None
    )
    if idx is not None and idx < len(trainer.fairness_ratios):
        return int(int(trainer.total_training_samples * trainer.fairness_ratios[idx]) * 0.8)
    return trainer.total_training_samples // trainer.num_clients

def setup_without_edc(client_offers, num_clients):
    client_offers[:] = [
        {'client_id': f'client-{i}'} for i in range(1, num_clients + 1)
    ]
    logger.info(f"Without-EDC mode: {num_clients} clients registered")
