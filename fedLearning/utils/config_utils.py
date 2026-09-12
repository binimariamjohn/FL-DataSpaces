import json
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class UnifiedConfig:
    
    def __init__(self, config_dir: Optional[str] = None):
        self.path = Path(config_dir) if config_dir else PROJECT_ROOT / "configs"
        self.raw = self._load_all()
    
    # Load and merge all config files
    def _load_all(self) -> dict:        
        d = self._load("datasetFactors.json")
        n = self._load("networkingFactors.json")
        f = self._load("flFactors.json")
        e = self._load("dataSpaceFactors.json")
        
        return {
            'mode': f.get('mode', 'without-edc'),
            'paths': d.get('paths', {}),
            'dataset_details': d.get('dataset_details', {}),
            'dataset_factors': d.get('dataset_factors', [{}])[0],
            'network': n,
            'federated': f.get('federated', {}),
            'edc': e.get('edc', {}),
            'dataspace': e,
            'input_shape': d.get('input_shape', [28])
        }

    def _load(self, name: str) -> dict:
        p = self.path / name
        return json.loads(p.read_text()) if p.exists() else {}
    

