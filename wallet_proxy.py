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
import time

app = Flask(__name__, static_folder='.', static_url_path='')
# Enable CORS for all origins (needed for frontend)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Add CORS headers manually to all responses (CRITICAL for Render)
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize cloudscraper with more aggressive settings
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False,
        'desktop': True
    },
    delay=10,  # Add delay between requests
    debug=False
)

WALLET_ADDRESS = os.getenv('WALLET_ADDRESS', '95L9VfK5Dsshpeiaicsrz9E4D2iTtp9iapBUAtmihmcw')

@app.route('/api/wallet-activity', methods=['GET'])
def get_wallet_activity():
    """Proxy endpoint for wallet activity"""
    try:
        wallet = request.args.get('wallet', WALLET_ADDRESS)
        limit = request.args.get('limit', '50')
        cost = request.args.get('cost', '10')
        
        # Log the wallet being requested for debugging
        logger.info(f"Requested wallet: {wallet}")
        
        url = f"https://gmgn.ai/vas/api/v1/wallet_activity/sol?type=buy&type=sell&device_id=5f314746-4f28-407f-bb42-6fa36b4c12e5&fp_did=34d0f8ae922f6b5c5397b8cf5cde1117&client_id=gmgn_web_20260105-9509-b9c2d27&from_app=gmgn&app_ver=20260105-9509-b9c2d27&tz_name=Europe%2FWarsaw&tz_offset=3600&app_lang=en-US&os=web&worker=0&wallet={wallet}&limit={limit}&cost={cost}"
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://gmgn.ai/',
            'Origin': 'https://gmgn.ai',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        logger.info(f"Fetching wallet activity for {wallet}")
        logger.info(f"Request URL: {url}")
        
        # Retry logic for Cloudflare challenges with longer waits
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Add delay before request to avoid rate limiting
                if attempt > 0:
                    wait_time = min(attempt * 3, 15)  # Max 15 seconds
                    logger.info(f"Waiting {wait_time}s before retry attempt {attempt + 1}...")
                    time.sleep(wait_time)
                
                # Create a fresh scraper instance for each retry
                if attempt > 0:
                    scraper = cloudscraper.create_scraper(
                        browser={
                            'browser': 'chrome',
                            'platform': 'windows',
                            'mobile': False,
                            'desktop': True
                        },
                        delay=10
                    )
                
                response = scraper.get(url, headers=headers, timeout=45)
                logger.info(f"Response status: {response.status_code} (attempt {attempt + 1})")
                
                # Check if we got HTML (Cloudflare challenge page)
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type and attempt < max_retries - 1:
                    logger.warning(f"Got HTML response (Cloudflare challenge), retrying...")
                    continue
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    if isinstance(data, dict) and 'data' in data and 'activities' in data.get('data', {}):
                        logger.info(f"Found {len(data['data']['activities'])} activities")
                    return jsonify(data)
                elif response.status_code == 403 and attempt < max_retries - 1:
                    # Cloudflare challenge - wait longer and retry
                    logger.warning(f"Got 403, will retry...")
                    continue
                else:
                    logger.error(f"API returned status {response.status_code}")
                    logger.error(f"Response text: {response.text[:500]}")
                    if attempt == max_retries - 1:
                        return jsonify({'error': f'API returned status {response.status_code} after {max_retries} attempts'}), response.status_code
                    continue
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Request failed, will retry... Error: {str(e)}")
                    continue
                else:
                    logger.error(f"Final attempt failed: {str(e)}")
                    raise
            
    except Exception as e:
        logger.error(f"Error fetching wallet activity: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/profit-stats', methods=['GET'])
def get_profit_stats():
    """Proxy endpoint for GMGN profit stats API"""
    try:
        wallet = request.args.get('wallet', WALLET_ADDRESS)
        period = request.args.get('period', '7d')
        
        url = f"https://gmgn.ai/pf/api/v1/wallet/sol/{wallet}/profit_stat/{period}?device_id=5f314746-4f28-407f-bb42-6fa36b4c12e5&fp_did=34d0f8ae922f6b5c5397b8cf5cde1117&client_id=gmgn_web_20260105-9509-b9c2d27&from_app=gmgn&app_ver=20260105-9509-b9c2d27&tz_name=Europe%2FWarsaw&tz_offset=3600&app_lang=en-US&os=web&worker=0"
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://gmgn.ai/',
            'Origin': 'https://gmgn.ai',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        logger.info(f"Requested wallet for profit stats: {wallet}")
        logger.info(f"Fetching profit stats for {wallet}")
        
        # Retry logic for Cloudflare challenges with longer waits
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Add delay before request to avoid rate limiting
                if attempt > 0:
                    wait_time = min(attempt * 3, 15)  # Max 15 seconds
                    logger.info(f"Waiting {wait_time}s before retry attempt {attempt + 1}...")
                    time.sleep(wait_time)
                
                # Create a fresh scraper instance for each retry
                if attempt > 0:
                    scraper = cloudscraper.create_scraper(
                        browser={
                            'browser': 'chrome',
                            'platform': 'windows',
                            'mobile': False,
                            'desktop': True
                        },
                        delay=10
                    )
                
                response = scraper.get(url, headers=headers, timeout=45)
                logger.info(f"Profit stats response status: {response.status_code} (attempt {attempt + 1})")
                
                # Check if we got HTML (Cloudflare challenge page)
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type and attempt < max_retries - 1:
                    logger.warning(f"Got HTML response (Cloudflare challenge), retrying...")
                    continue
                
                if response.status_code == 200:
                    data = response.json()
                    return jsonify(data)
                elif response.status_code == 403 and attempt < max_retries - 1:
                    # Cloudflare challenge - wait longer and retry
                    logger.warning(f"Got 403, will retry...")
                    continue
                else:
                    logger.error(f"GMGN API returned status {response.status_code}")
                    if attempt == max_retries - 1:
                        return jsonify({'error': f'API returned status {response.status_code} after {max_retries} attempts'}), response.status_code
                    continue
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Request failed, will retry... Error: {str(e)}")
                    continue
                else:
                    logger.error(f"Final attempt failed: {str(e)}")
                    raise
            
    except Exception as e:
        logger.error(f"Error fetching profit stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

@app.route('/')
def index():
    """Serve the main HTML file (optional - not needed for API-only service)"""
    return jsonify({'message': 'Klaude Proxy API', 'endpoints': ['/api/wallet-activity', '/api/profit-stats', '/health']})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting wallet proxy server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

