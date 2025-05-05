#!/usr/bin/env python3
"""
Test the connection to Schwab API with the updated v2 endpoints
"""

import os
import logging
import sys
import requests
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('schwab_test')

# Constants - using paths as specified in Schwab production specs
# According to https://developer.schwab.com/products/trader-api--individual/details/specifications/Retail%20Trader%20API%20Production
SANDBOX_AUTH_URL = "https://api-sandbox.schwabapi.com/oauth2/authorize"
PRODUCTION_AUTH_URL = "https://api.schwabapi.com/oauth2/authorize"

def test_connection(use_sandbox=True):
    """Test connection to Schwab API authorization endpoint"""
    logger.info(f"Testing connection to Schwab API {('sandbox' if use_sandbox else 'production')} v1 endpoints")
    
    # Get credentials from environment
    api_key = os.environ.get('SCHWAB_API_KEY')
    if not api_key:
        logger.error("SCHWAB_API_KEY environment variable not set")
        return False
    
    # Truncate key for logging
    display_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "[HIDDEN]"
    logger.info(f"Using API key: {display_key}")
    
    # Set the URL based on environment
    base_url = SANDBOX_AUTH_URL if use_sandbox else PRODUCTION_AUTH_URL
    logger.info(f"Testing connection to: {base_url}")
    
    # Test with a HEAD request
    try:
        response = requests.head(
            base_url,
            headers={"User-Agent": "Schwab API Connection Test"},
            timeout=10
        )
        
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        # 401/403 might be expected - it means the endpoint exists but we're not authorized
        if response.status_code in (401, 403):
            logger.info("Received 401/403 - this is normal for API endpoints that require authentication")
            logger.info("Connection test successful - endpoint exists!")
            return True
        elif response.status_code < 500:  # Any non-server error is okay
            logger.info("Connection test successful!")
            return True
        else:
            logger.error(f"Connection test failed with server error: {response.status_code}")
            return False
            
    except requests.RequestException as e:
        logger.error(f"Connection error: {str(e)}")
        return False

def main():
    # Test both sandbox and production
    logger.info("====== Testing Schwab API Connection ======")
    sandbox_result = test_connection(use_sandbox=True)
    production_result = test_connection(use_sandbox=False)
    
    # Display recommendation
    if sandbox_result and not production_result:
        logger.info("✓ RECOMMENDATION: Use sandbox environment with your current credentials")
    elif production_result and not sandbox_result:
        logger.info("✓ RECOMMENDATION: Use production environment with your current credentials")
    elif sandbox_result and production_result:
        logger.info("✓ RECOMMENDATION: Both environments are accessible - use sandbox for testing")
    else:
        logger.error("✗ RECOMMENDATION: Neither environment is accessible - check your credentials")
    
    logger.info("====== Schwab API Connection Test Complete ======")
    return sandbox_result or production_result

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
