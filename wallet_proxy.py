#!/usr/bin/env python3
"""
Wallet Activity Proxy Server
Fetches wallet data from GMGN API using cloudscraper to bypass Cloudflare
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import cloudscraper
import logging
import os

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # Enable CORS for frontend

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize cloudscraper
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False,
        'desktop': True
    }
)

WALLET_ADDRESS = os.getenv('WALLET_ADDRESS', '95L9VfK5Dsshpeiaicsrz9E4D2iTtp9iapBUAtmihmcw')

@app.route('/api/wallet-activity', methods=['GET'])
def get_wallet_activity():
    """Proxy endpoint for wallet activity"""
    try:
        limit = request.args.get('limit', '50')
        cost = request.args.get('cost', '10')
        
        url = f"https://gmgn.ai/vas/api/v1/wallet_activity/sol?type=buy&type=sell&device_id=5f314746-4f28-407f-bb42-6fa36b4c12e5&fp_did=34d0f8ae922f6b5c5397b8cf5cde1117&client_id=gmgn_web_20260105-9509-b9c2d27&from_app=gmgn&app_ver=20260105-9509-b9c2d27&tz_name=Europe%2FWarsaw&tz_offset=3600&app_lang=en-US&os=web&worker=0&wallet={WALLET_ADDRESS}&limit={limit}&cost={cost}"
        
        headers = {
            'Accept': 'application/json',
            'Referer': 'https://gmgn.ai/',
            'Origin': 'https://gmgn.ai',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        logger.info(f"Fetching wallet activity for {WALLET_ADDRESS}")
        logger.info(f"Request URL: {url}")
        response = scraper.get(url, headers=headers, timeout=30)
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            if isinstance(data, dict) and 'data' in data and 'activities' in data.get('data', {}):
                logger.info(f"Found {len(data['data']['activities'])} activities")
            return jsonify(data)
        else:
            logger.error(f"API returned status {response.status_code}")
            logger.error(f"Response text: {response.text[:500]}")
            return jsonify({'error': f'API returned status {response.status_code}'}), response.status_code
            
    except Exception as e:
        logger.error(f"Error fetching wallet activity: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory('.', 'index.html')

@app.route('/api/profit-stats', methods=['GET'])
def get_profit_stats():
    """Proxy endpoint for GMGN profit stats API"""
    try:
        wallet = request.args.get('wallet', WALLET_ADDRESS)
        period = request.args.get('period', '7d')
        
        url = f"https://gmgn.ai/pf/api/v1/wallet/sol/{wallet}/profit_stat/{period}?device_id=5f314746-4f28-407f-bb42-6fa36b4c12e5&fp_did=34d0f8ae922f6b5c5397b8cf5cde1117&client_id=gmgn_web_20260105-9509-b9c2d27&from_app=gmgn&app_ver=20260105-9509-b9c2d27&tz_name=Europe%2FWarsaw&tz_offset=3600&app_lang=en-US&os=web&worker=0"
        
        headers = {
            'Accept': 'application/json',
            'Referer': 'https://gmgn.ai/',
            'Origin': 'https://gmgn.ai',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        logger.info(f"Fetching profit stats for {wallet}")
        response = scraper.get(url, headers=headers, timeout=30)
        
        logger.info(f"Profit stats response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        else:
            logger.error(f"GMGN API returned status {response.status_code}")
            return jsonify({'error': f'API returned status {response.status_code}'}), response.status_code
            
    except Exception as e:
        logger.error(f"Error fetching profit stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting wallet proxy server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

