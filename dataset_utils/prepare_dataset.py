#Download dataset

import json
import numpy as np
from pathlib import Path
from torchvision import datasets

#Save images for normalisation
def save_bundle(path, images, labels, mean, std):
    path.mkdir(parents=True, exist_ok=True)

    images = images.astype(np.float32) / 255.0
    images = (images - mean) / std
    images = np.expand_dims(images, -1) 

    np.savez(path / "images.npz", images=images)
    np.savez(path / "labels.npz", labels=labels)

#Download dataset and save to local folder
def prepare_dataset(dataset_class, dataset_name, base_path, train_dir_name, test_dir_name, mean, std):
    raw_download_path = base_path / "_raw_downloads"
    train_set = dataset_class(raw_download_path, train=True, download=True)
    test_set = dataset_class(raw_download_path, train=False, download=True)

    dataset_dir = base_path / dataset_name
    train_dir = dataset_dir / train_dir_name
    test_dir = dataset_dir / test_dir_name

    save_bundle(train_dir, train_set.data.numpy(), train_set.targets.numpy(), mean, std,)
    save_bundle(test_dir,test_set.data.numpy(), test_set.targets.numpy(), mean,std,)


def main():
    root = Path(__file__).resolve().parents[1]
    config_path = root / "configs" / "datasetFactors.json"

    with open(config_path, "r") as f:
        config = json.load(f)

    dataset_base_path = (root / config["paths"]["dataset_path"]).resolve()

    split_cfg = config.get("dataset_details", {}).get("dataset_split", {})
    train_dir_name = split_cfg.get("training_dataset_dir", "train")
    test_dir_name = split_cfg.get("global_test_dir", "test")

    # MNIST normalization values
    mnist_mean = 0.1307
    mnist_std = 0.3081

    # Fashion-MNIST normalization values
    fashion_mnist_mean = 0.2860
    fashion_mnist_std = 0.3530

    prepare_dataset(datasets.MNIST, "MNIST", dataset_base_path, train_dir_name, test_dir_name, mnist_mean, mnist_std,)

    prepare_dataset(datasets.FashionMNIST,"FASHION-MNIST",dataset_base_path,train_dir_name, test_dir_name,fashion_mnist_mean,fashion_mnist_std,)

    print(f"Datasets downloaded")


if __name__ == "__main__":
    main()