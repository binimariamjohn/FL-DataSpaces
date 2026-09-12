#!/usr/bin/env python3
"""
Dataspace Web App - Federated Catalogue Registry
Minimal Flask service for offer registration and discovery (in-memory storage).
"""
from flask import Flask, request, render_template_string, Response
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

offers = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Data Space Marketplace</title>
    <style>
        body { font-family: Arial; margin: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #4CAF50; color: white; }
        tr:hover { background: #f5f5f5; }
        .price-high { color: #4CAF50; font-weight: bold; }
        .price-low { color: #999; }
    </style>
</head>
<body>
    <h1>Data Space Marketplace - Federated Catalogue</h1>
    <p><strong>Total Offers:</strong> {{ total_offers }} | <strong>Last Updated:</strong> {{ last_updated }}</p>
    <table>
        <thead>
            <tr><th>Client</th><th>Dataset</th><th>Price</th><th>Training</th><th>Asset ID</th><th>Provider URL</th></tr>
        </thead>
        <tbody>
            {% if offers %}
                {% for offer in offers %}
                <tr>
                    <td>{{ offer.client_id }}</td>
                    <td>{{ offer.dataset_id }}</td>
                    <td class="{% if offer.price_info|int > 10000 %}price-high{% else %}price-low{% endif %}">${{ "{:,}".format(offer.price_info|int) }}</td>
                    <td>{{ offer.training_allowed }}</td>
                    <td>{{ offer.asset_id }}</td>
                    <td>{{ offer.provider_connector_protocol_url }}</td>
                </tr>
                {% endfor %}
            {% else %}
                <tr><td colspan="6" style="text-align:center;color:#999;">No offers yet</td></tr>
            {% endif %}
        </tbody>
    </table>
</body>
</html>
"""

@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

@app.route('/')
def index():
    return render_template_string(
        HTML_TEMPLATE,
        offers=offers,
        total_offers=len(offers),
        last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

@app.route('/offers', methods=['GET'])
def get_offers():
    dataset_group = request.args.get('dataset_group')
    training_allowed = request.args.get('training_allowed')
    min_price = request.args.get('min_price', type=int)
    
    filtered_offers = offers
    if dataset_group:
        filtered_offers = [o for o in filtered_offers if o['dataset_group'] == dataset_group]
    if training_allowed:
        filtered_offers = [o for o in filtered_offers if o['training_allowed'] == training_allowed]
    if min_price is not None:
        filtered_offers = [o for o in filtered_offers if int(o['price_info']) > min_price]
    
    root = ET.Element('offers')
    root.set('count', str(len(filtered_offers)))
    
    for offer in filtered_offers:
        offer_elem = ET.SubElement(root, 'offer')
        for key, value in offer.items():
            child = ET.SubElement(offer_elem, key)
            child.text = str(value)
    
    xml_str = ET.tostring(root, encoding='utf-8', method='xml')
    return Response(xml_str, mimetype='application/xml')

@app.route('/offers', methods=['POST'])
def register_offer():
    try:
        xml_data = request.data
        root = ET.fromstring(xml_data)
        
        offer = {}
        for child in root:
            offer[child.tag] = child.text
        
        offer['registered_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check for duplicates
        existing = next((o for o in offers if o['client_id'] == offer['client_id'] 
                        and o['asset_id'] == offer['asset_id']), None)
        if existing:
            offers.remove(existing)
        
        offers.append(offer)
        logger.info(f"Registered offer from {offer['client_id']}: {offer['dataset_id']} (${offer['price_info']})")
        
        return {'status': 'success', 'message': 'Offer registered'}, 201
    except Exception as e:
        logger.error(f"Error registering offer: {e}")
        return {'error': str(e)}, 500

if __name__ == '__main__':
    logger.info("Starting Dataspace Web App on http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=False)


def start_web_app():
    def run_flask():
        app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
    
    thread = threading.Thread(target=run_flask, daemon=True)
    thread.start()
    
    time.sleep(2)
    try:
        import requests
        requests.get('http://localhost:5001/', timeout=5)
        logger.info("Web app started on http://localhost:5001")
        return True
    except Exception as e:
        logger.error(f"Failed to start web app: {e}")
        return False


def retrieve_catalogue_from_web_app():
    try:
        import requests
        resp = requests.get('http://localhost:5001/offers', timeout=10)
        resp.raise_for_status()
        
        root = ET.fromstring(resp.content)
        offers = []
        
        for offer_elem in root.findall('offer'):
            offer = {child.tag: child.text for child in offer_elem}
            offers.append(offer)
        
        return offers
    except Exception as e:
        logger.error(f"Failed to retrieve catalogue: {e}")
        return []
