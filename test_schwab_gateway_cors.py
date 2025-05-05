#!/usr/bin/env python3

"""
Test CORS configuration for Schwab Gateway

This script tests CORS headers on the Schwab Gateway domain
to determine if CORS is causing connection issues.
"""

import os
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gateway_cors():
    """Test CORS configuration on the Schwab Gateway domain"""
    base_url = "https://sws-gateway.schwab.com"
    
    # List of paths to test for CORS
    paths = [
        "/v1/oauth/authorize",
        "/v1/oauth/token",
        "/oauth/authorize",
        "/oauth/token"
    ]
    
    # Test each path with preflight OPTIONS request
    for path in paths:
        url = f"{base_url}{path}"
        
        try:
            try:
                # Set Origin header to simulate cross-origin request
                headers = {
                    "Origin": "https://7352034c-d741-4cbf-9bc5-d05d9b93e49d-00-z4porq8bem36.picard.replit.dev",
                    "Access-Control-Request-Method": "GET",
                    "User-Agent": "TradingBot-Test/1.0"
                }
                
                logger.info(f"Testing CORS OPTIONS request for {url}")
                options_response = requests.options(url, headers=headers, timeout=5)
                
                # Check for CORS headers
                logger.info(f"OPTIONS response status: {options_response.status_code}")
                
                cors_headers = {
                    "Access-Control-Allow-Origin": options_response.headers.get("Access-Control-Allow-Origin"),
                    "Access-Control-Allow-Methods": options_response.headers.get("Access-Control-Allow-Methods"),
                    "Access-Control-Allow-Headers": options_response.headers.get("Access-Control-Allow-Headers")
                }
                
                logger.info(f"CORS headers: {cors_headers}")
            except requests.RequestException as e:
                logger.error(f"Error during OPTIONS request for {url}: {str(e)}")
            
            try:
                # Now try a GET request with Origin header
                logger.info(f"Testing CORS GET request for {url}")
                get_headers = {"Origin": "https://7352034c-d741-4cbf-9bc5-d05d9b93e49d-00-z4porq8bem36.picard.replit.dev"}
                get_response = requests.get(url, headers=get_headers, timeout=5)
                
                logger.info(f"GET response status: {get_response.status_code}")
                logger.info(f"Access-Control-Allow-Origin: {get_response.headers.get('Access-Control-Allow-Origin')}")
            except requests.RequestException as e:
                logger.error(f"Error during GET request for {url}: {str(e)}")
            
        except requests.RequestException as e:
            logger.error(f"Error testing CORS for {url}: {str(e)}")

def main():
    """Run the CORS tests"""
    logger.info("Testing Schwab Gateway CORS configuration...")
    test_gateway_cors()
    logger.info("CORS testing complete.")

if __name__ == "__main__":
    main()
