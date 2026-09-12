#!/usr/bin/env python3
"""EDC contract negotiation utility."""
import logging
from typing import List, Dict, Callable, Optional
from pathlib import Path

from dataspace.edc_utils import fetch_catalogue, negotiate_contract

logger = logging.getLogger(__name__)


def negotiate_edc_contracts(
    partners: List[Dict],
    consumer_mgmt_url: str,
    consumer_api_key: str,
    config_path: str,
    asset_selector: Callable[[Dict, Dict], Optional[str]],
    agreement_builder: Optional[Callable[[Dict, Dict], Dict]] = None,
    operation_name: str = "Contract negotiation"
) -> Dict:
    stats = {
        'catalog_time': 0,
        'negotiation_time': 0,
        'bytes_sent': 0,
        'bytes_received': 0,
        'num_contracts': 0,
        'num_messages': 0
    }
    agreements = []
    
    for partner in partners:
        partner_id = partner.get('client_id', partner.get('partner_id', 'unknown'))
        provider_dsp = partner.get('provider_connector_protocol_url', partner.get('provider_dsp'))
        
        partner_consumer_mgmt = partner.get('consumer_mgmt_url', consumer_mgmt_url)

        cat_result = fetch_catalogue(partner_consumer_mgmt, provider_dsp, consumer_api_key, config_path)
        catalog = cat_result['catalog']
        stats['catalog_time'] += cat_result['catalog_time']
        stats['bytes_sent'] += cat_result['bytes_sent']
        stats['bytes_received'] += cat_result['bytes_received']
        stats['num_messages'] += cat_result.get('num_messages', 0)
        
        asset_id = asset_selector(partner, catalog)
        if not asset_id:
            logger.error(f"Asset not found in catalog for {partner_id}")
            continue
        
        datasets = catalog.get("dcat:dataset", [])
        if isinstance(datasets, dict):
            datasets = [datasets]
        
        dataset = next((d for d in datasets if d.get("@id") == asset_id), None)
        if not dataset:
            raise RuntimeError(f"Dataset {asset_id} not found in catalog for {partner_id}")
        
        policies = dataset.get("odrl:hasPolicy", [])
        if isinstance(policies, dict):
            policies = [policies]
        policy = policies[0]
        
        neg_result = negotiate_contract(
            partner_consumer_mgmt, provider_dsp, policy, asset_id,
            consumer_api_key, config_path
        )
        stats['negotiation_time'] += neg_result['negotiation_time']
        stats['bytes_sent'] += neg_result['bytes_sent']
        stats['bytes_received'] += neg_result['bytes_received']
        stats['num_contracts'] += 1
        stats['num_messages'] += neg_result.get('num_messages', 0)
        
        agreement_id = neg_result['agreement_id']
        if not agreement_id:
            logger.error(f"Contract negotiation failed for {partner_id}")
            continue
        
        if agreement_builder:
            agreement = agreement_builder(partner, neg_result)
        else:
            agreement = {'partner_id': partner_id, 'agreement_id': agreement_id}
        
        agreements.append(agreement)
        logger.info(f"{operation_name}: {partner_id} → {agreement_id}")
    
    return {'agreements': agreements, 'stats': stats}


def select_offered_asset(offer: Dict, catalog: Dict) -> Optional[str]:
    return offer.get('asset_id')


def select_asset_by_id(target_asset_id: str):
    def selector(offer: Dict, catalog: Dict) -> Optional[str]:
        datasets = catalog.get("dcat:dataset", [])
        if isinstance(datasets, dict):
            datasets = [datasets]
        ds = next((d for d in datasets if d.get("@id") == target_asset_id), None)
        return ds.get("@id") if ds else None
    return selector


def build_simple_agreement(offer: Dict, neg_result: Dict) -> Dict:
    return {
        'client_id': offer['client_id'],
        'agreement_id': neg_result['agreement_id'],
        'asset_id': offer.get('asset_id', '')
    }


def build_model_transfer_agreement(offer: Dict, neg_result: Dict) -> Dict:
    client_id = offer['client_id']
    return {
        'client_id': client_id,
        'client_num': int(''.join(filter(str.isdigit, client_id))),
        'agreement_id': neg_result['agreement_id'],
        'mgmt_url': offer['provider_connector_management_url']
    }
