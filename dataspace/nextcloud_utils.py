#!/usr/bin/env python3
"""Nextcloud WebDAV client."""
import pickle
import logging
from pathlib import Path
from typing import Union, Optional
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class NextcloudClient:
    
    def __init__(self, host: str, username: str, password: str, port: int = 80):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.auth = HTTPBasicAuth(username, password)
        self.base_url = f"http://{host}:{port}/remote.php/dav/files/{username}"
        self.session = requests.Session()
    
    def ensure_directory(self, path: str, timeout: int = 30) -> bool:
        url = f"{self.base_url}/{path}"
        try:
            resp = self.session.request("MKCOL", url, auth=self.auth, timeout=timeout)
            if resp.status_code in [201, 405]:  # 201=Created, 405=Already exists
                return True
            logger.warning(f"MKCOL returned {resp.status_code} for {path}")
            return False
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False
    
    def upload_file(self, local_path: Union[str, Path], remote_path: str, 
                   ensure_dir: bool = True, timeout: int = 120) -> bool:
        if ensure_dir:
            parent_dir = str(Path(remote_path).parent)
            if parent_dir != ".":
                self.ensure_directory(parent_dir, timeout=30)
        
        url = f"{self.base_url}/{remote_path}"
        try:
            with open(local_path, 'rb') as f:
                data = f.read()
            resp = self.session.put(url, data=data, auth=self.auth, timeout=timeout,
                                   headers={"Content-Type": "application/octet-stream"})
            if resp.status_code in [200, 201, 204]:
                logger.info(f"Uploaded {local_path} → {remote_path} ({len(data)/1024:.1f} KB)")
                return True
            logger.error(f"Upload failed: {resp.status_code}")
            return False
        except Exception as e:
            logger.error(f"Failed to upload {local_path}: {e}")
            return False
    
    def upload_bytes(self, data: bytes, remote_path: str, 
                    ensure_dir: bool = True, timeout: int = 120) -> bool:
        if ensure_dir:
            parent_dir = str(Path(remote_path).parent)
            if parent_dir != ".":
                self.ensure_directory(parent_dir, timeout=30)
        
        url = f"{self.base_url}/{remote_path}"
        try:
            resp = self.session.put(url, data=data, auth=self.auth, timeout=timeout,
                                   headers={"Content-Type": "application/octet-stream"})
            if resp.status_code in [200, 201, 204]:
                logger.info(f"Uploaded {len(data)/1024:.1f} KB → {remote_path}")
                return True
            logger.error(f"Upload failed: {resp.status_code}")
            return False
        except Exception as e:
            logger.error(f"Failed to upload bytes: {e}")
            return False
    
    def upload_pickle(self, obj, remote_path: str, ensure_dir: bool = True, timeout: int = 120) -> bool:
        data = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
        return self.upload_bytes(data, remote_path, ensure_dir, timeout)
    
    def file_exists(self, remote_path: str, timeout: int = 10) -> bool:
        url = f"{self.base_url}/{remote_path}"
        try:
            resp = self.session.head(url, auth=self.auth, timeout=timeout)
            return resp.status_code == 200
        except Exception:
            return False


def get_client_nextcloud(client_num: int) -> NextcloudClient:
    return NextcloudClient(
        host=f"client-{client_num}-nextcloud",
        username="padmin",
        password="p123"
    )


def get_research_centre_nextcloud() -> NextcloudClient:
    return NextcloudClient(
        host="research-centre-nextcloud",
        username="cadmin",
        password="c123"
    )


def load_trained_weights_from_nextcloud(client_id: str):
    from fedLearning.models import load_weights_from_file
    weights_path = Path(f"/nextcloud-data/data/cadmin/files/received_trained_models/{client_id}_weights.pkl")
    if not weights_path.exists():
        raise FileNotFoundError(f"Weights not found: {weights_path}")
    return load_weights_from_file(str(weights_path))

