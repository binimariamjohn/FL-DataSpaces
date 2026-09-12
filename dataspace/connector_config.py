#!/usr/bin/env python3
"""Connector configuration loader."""
import json
from pathlib import Path
from typing import Dict


class ConnectorConfig:
    
    def __init__(self, config_root: Path):
        self.config_root = Path(config_root)
        config_path = self.config_root / "dataSpaceFactors.json"
        if not config_path.exists():
            raise FileNotFoundError(f"dataSpaceFactors.json not found at {config_path}")
        with open(config_path) as f:
            self.data_space_config = json.load(f)
    
    def get_client_config(self, client_num: int) -> Dict[str, str]:
        providers = self.data_space_config.get("edc", {}).get("providers_connectors", [])
        provider_name = f"client-{client_num}-provider"
        provider = next((p for p in providers if p["name"] == provider_name), None)
        if not provider:
            raise ValueError(f"Provider {provider_name} not found")
        
        props = self._load_properties(self.config_root / provider["config_path"])
        participant_id = props.get("edc.participant.id")
        connector_hostname = f"{participant_id}-connector"
        mgmt_port = props.get("web.http.management.port")
        protocol_port = props.get("web.http.protocol.port")
        
        return {
            "participant_id": participant_id,
            "connector_hostname": connector_hostname,
            "mgmt_port": mgmt_port,
            "protocol_port": protocol_port,
            "mgmt_url": f"http://{connector_hostname}:{mgmt_port}/management/v3",
            "protocol_url": f"http://{connector_hostname}:{protocol_port}/protocol",
            "api_key": props.get("edc.api.auth.key", "password"),
            "nextcloud_container": provider.get("nextcloud_container", ""),
            "provider_name": provider_name
        }
    
    def get_research_centre_config(self, rc_num: int = 1) -> Dict[str, str]:
        consumers = self.data_space_config.get("edc", {}).get("consumer_connectors", [])
        consumer_name = f"research-centre-consumer" if rc_num == 1 else f"research-centre-{rc_num}-consumer"
        consumer = next((c for c in consumers if c["name"] == consumer_name), None)
        if not consumer:
            raise ValueError(f"Consumer {consumer_name} not found")
        
        props = self._load_properties(self.config_root / consumer["config_path"])
        participant_id = props.get("edc.participant.id")
        connector_hostname = f"{participant_id}-connector"
        mgmt_port = props.get("web.http.management.port")
        protocol_port = props.get("web.http.protocol.port")
        
        return {
            "participant_id": participant_id,
            "connector_hostname": connector_hostname,
            "mgmt_port": mgmt_port,
            "protocol_port": protocol_port,
            "mgmt_url": f"http://{connector_hostname}:{mgmt_port}/management/v3",
            "protocol_url": f"http://{connector_hostname}:{protocol_port}/protocol",
            "api_key": props.get("edc.api.auth.key", "password"),
            "consumer_name": consumer_name
        }
    
    @staticmethod
    def _load_properties(filepath: Path) -> Dict[str, str]:
        props = {}
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        props[key.strip()] = value.strip()
        return props
