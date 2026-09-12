#!/usr/bin/env python3
import os
from datetime import datetime


def setup_ns3_env_vars(config, exp_name=None):
    # Setup NS3 simulator environment variables from config
    os.environ['NUM_CLIENTS'] = str(config['dataset_factors']['num_clients'])
    
    network_config = config.get('network', {})
    os.environ['NS3_NETWORK_TYPE'] = network_config.get('type', 'ethernet')
    os.environ['NS3_NETWORK_MODE'] = network_config.get('mode', 'sync')
    os.environ['NS3_PACKET_SIZE'] = str(network_config.get('max_packet_size', 1024))
    os.environ['NS3_MODEL_SIZE'] = str(network_config.get('model_size_kb', 9500))
    os.environ['NS3_CLIENT_DATA_RATE'] = f"{network_config.get('client_data_rate_kbps', 2048)}kbps"
    os.environ['NS3_SERVER_DATA_RATE'] = f"{network_config.get('server_data_rate_kbps', 10000)}kbps"
    os.environ['NS3_PORT'] = str(network_config.get('ns3_port', 9099))
    
    paths_config = config.get('paths')
    results_path = paths_config['results_path']
    logs_path = paths_config['logs_path']
    
    os.environ['RESULTS_PATH'] = results_path
    os.environ['LOGS_PATH'] = logs_path
    
    os.environ['NS3_HOST_RESULTS_PATH'] = results_path
    os.environ['NS3_HOST_LOGS_PATH'] = logs_path
    
    os.environ['NS3_RESULTS_PATH'] = results_path
    os.environ['NS3_LOGS_PATH'] = logs_path
    
    if exp_name:
        run_id = exp_name
    else:
        run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    os.environ['RUN_ID'] = run_id
    
    print(f"NS3 Config: {os.environ['NUM_CLIENTS']} clients, "
          f"type={os.environ['NS3_NETWORK_TYPE']}, "
          f"mode={os.environ['NS3_NETWORK_MODE']}")
    
    return run_id
