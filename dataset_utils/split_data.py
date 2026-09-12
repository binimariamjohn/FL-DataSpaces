# Split dataset for clients
import json
import numpy as np
from pathlib import Path


def save_bundle(path, images, labels):
    path.mkdir(parents=True, exist_ok=True)
    np.savez(path / "images.npz", images=images)
    np.savez(path / "labels.npz", labels=labels)


def load_local_dataset(train_base_dir):
    images_file = train_base_dir / "images.npz"
    labels_file = train_base_dir / "labels.npz"

    if images_file.exists() and labels_file.exists():
        images = np.load(images_file)["images"]
        labels = np.load(labels_file)["labels"]
        return images, labels

    raise FileNotFoundError(f"Dataset not found in {train_base_dir}")


def split_and_save_datasets(config, project_root):
    base_path = (project_root / config["paths"]["dataset_path"]).resolve()
    split_cfg = config["dataset_details"]["dataset_split"]
    factors = config["dataset_factors"]

    dataset_folder = config["dataset_details"]["dataset_name"]

    train_base_dir = base_path / dataset_folder / split_cfg["training_dataset_dir"]

    num_clients = factors["num_clients"]
    partition_size = factors.get("partition_size", 0)
    fairness_ratios = factors.get("fairness_ratios", [1] * num_clients)

    all_images, all_labels = load_local_dataset(train_base_dir)

    # If partition_size is not specified or is 0, use the full training dataset
    if not partition_size or partition_size <= 0:
        total_used = len(all_images)
    else:
        total_used = partition_size * num_clients
    
    rng = np.random.default_rng(config.get("random_seed", 42))
    indices = rng.permutation(len(all_images))[:total_used]

    fairness_ratios = np.array(fairness_ratios, dtype=float)
    client_sizes = (fairness_ratios / fairness_ratios.sum() * total_used).astype(int)

    while client_sizes.sum() < total_used:
        client_sizes[np.argmin(client_sizes)] += 1

    start = 0
    for i in range(num_clients):
        end = start + client_sizes[i]
        idx = indices[start:end]

        client_dir = train_base_dir / f"client_{i + 1}"
        save_bundle(client_dir, all_images[idx], all_labels[idx])
        unique, counts = np.unique(all_labels[idx], return_counts=True)
        start = end


def main():
    root = Path(__file__).resolve().parents[1]
    config_path = root / "configs" / "datasetFactors.json"

    with open(config_path, "r") as f:
        config = json.load(f)

    split_and_save_datasets(config, root)
    print("Dataset split complete")


if __name__ == "__main__":
    main()