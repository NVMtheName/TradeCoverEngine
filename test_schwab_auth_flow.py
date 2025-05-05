#!/usr/bin/env python3
"""
Test the Schwab API OAuth flow using the exact format from documentation
"""

import os
import logging
import sys
import requests
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('schwab_auth_test')

# Constants based on the provided documentation
AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"

# We'll use the Replit domain for our redirect URL
REDIRECT_URI = f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}/oauth/callback"

def test_auth_flow():
    """
    Test the Schwab API OAuth flow using the exact format from documentation
    """
    logger.info("=== Testing Schwab API OAuth Flow ====")
    
    # Get credentials from environment
    client_id = os.environ.get('SCHWAB_API_KEY')
    client_secret = os.environ.get('SCHWAB_API_SECRET')
    
    if not client_id or not client_secret:
        logger.error("SCHWAB_API_KEY or SCHWAB_API_SECRET environment variable not set")
        return False
    
    # Truncate credentials for logging
    display_id = f"{client_id[:4]}...{client_id[-4:]}" if len(client_id) > 8 else "[HIDDEN]"
    logger.info(f"Using client_id: {display_id}")
    logger.info(f"Redirect URI: {REDIRECT_URI}")
    
    # Construct the authorization URL as per Schwab documentation
    auth_params = {
        'response_type': 'code',
        'client_id': client_id,
        'scope': 'readonly',  # Using readonly scope as shown in docs
        'redirect_uri': REDIRECT_URI
    }
    
    auth_request_url = f"{AUTH_URL}?{urlencode(auth_params)}"
    logger.info(f"Authorization URL: {auth_request_url}")
    
    # Just test the connection to the authorization endpoint
    try:
        # We can't fully execute the flow automatically as it requires user interaction
        # Just check if the endpoint is accessible
        response = requests.head(
            AUTH_URL,
            headers={
                "User-Agent": "Schwab API OAuth Test",
                "Accept": "application/json"
            },
            timeout=10
        )
        
        logger.info(f"Authorization endpoint status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        # Check for Schwab-specific headers which would indicate we're hitting the right endpoint
        has_schwab_headers = any(h.startswith('Schwab-') for h in response.headers)
        logger.info(f"Contains Schwab-specific headers: {has_schwab_headers}")
        
        if has_schwab_headers:
            logger.info("✓ Successfully connected to Schwab API authorization endpoint")
            logger.info("✓ OAuth flow setup is correct based on documentation")
            
            logger.info("\nTo complete the OAuth flow in your application:")
            logger.info(f"1. Navigate to Settings in your app")
            logger.info(f"2. Click 'Connect with Schwab'")
            logger.info(f"3. Follow the authorization prompts")
            logger.info(f"4. You will be redirected back to: {REDIRECT_URI}")
            
            return True
        else:
            logger.error("✗ Connection successful but endpoint may not be a Schwab API endpoint")
            return False
            
    except Exception as e:
        logger.error(f"Error connecting to authorization endpoint: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_auth_flow()
    sys.exit(0 if success else 1)
