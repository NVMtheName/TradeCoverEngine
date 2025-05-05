#!/usr/bin/env python3
"""
Test the Schwab API OAuth2 flow using the updated endpoints
"""

import os
import logging
import sys
import requests
import time
import random
import string
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('schwab_oauth2_test')

# Constants - using multiple possible paths for Schwab OAuth2 endpoints
# https://developer.schwab.com/products/trader-api--individual/details/specifications/Retail%20Trader%20API%20Production
# Try multiple patterns to find the right one
SANDBOX_AUTH_URLS = [
    "https://api-sandbox.schwabapi.com/oauth2/authorize",
    "https://api-sandbox.schwabapi.com/v1/oauth2/authorize",
    "https://api-sandbox.schwabapi.com/broker/rest/v1/oauth2/authorize",
    "https://api-sandbox.schwabapi.com/oauth/authorize",  # Original v1 endpoint without version
    "https://sandbox.schwabapi.com/broker/rest/oauth/authorize",  # From docs example
    "https://sandbox.schwabapi.com/broker/rest/v1/oauth/authorize"  # From docs example with version
]
SANDBOX_TOKEN_URLS = [
    "https://api-sandbox.schwabapi.com/oauth2/token",
    "https://api-sandbox.schwabapi.com/v1/oauth2/token",
    "https://api-sandbox.schwabapi.com/broker/rest/v1/oauth2/token",
    "https://api-sandbox.schwabapi.com/oauth/token",  # Original v1 endpoint without version
    "https://sandbox.schwabapi.com/broker/rest/oauth/token",  # From docs example
    "https://sandbox.schwabapi.com/broker/rest/v1/oauth/token"  # From docs example with version
]
PRODUCTION_AUTH_URLS = [
    "https://api.schwabapi.com/oauth2/authorize",
    "https://api.schwabapi.com/v1/oauth2/authorize",
    "https://api.schwabapi.com/broker/rest/v1/oauth2/authorize",
    "https://api.schwabapi.com/oauth/authorize",  # Original v1 endpoint without version
    "https://schwabapi.com/broker/rest/oauth/authorize",  # From docs example
    "https://schwabapi.com/broker/rest/v1/oauth/authorize",  # From docs example with version
    "https://www.schwabapi.com/oauth/authorize",  # With www
    "https://www.schwabapi.com/broker/rest/oauth/authorize"  # With www + path
]
PRODUCTION_TOKEN_URLS = [
    "https://api.schwabapi.com/oauth2/token",
    "https://api.schwabapi.com/v1/oauth2/token",
    "https://api.schwabapi.com/broker/rest/v1/oauth2/token",
    "https://api.schwabapi.com/oauth/token",  # Original v1 endpoint without version
    "https://schwabapi.com/broker/rest/oauth/token",  # From docs example
    "https://schwabapi.com/broker/rest/v1/oauth/token",  # From docs example with version
    "https://www.schwabapi.com/oauth/token",  # With www
    "https://www.schwabapi.com/broker/rest/oauth/token"  # With www + path
]

def test_oauth_flow(use_sandbox=False):
    """Test the Schwab API OAuth2 flow"""
    logger.info(f"Testing Schwab API OAuth2 flow in {('sandbox' if use_sandbox else 'production')} environment")
    
    # Get credentials from environment
    client_id = os.environ.get('SCHWAB_API_KEY')
    client_secret = os.environ.get('SCHWAB_API_SECRET')
    
    if not client_id or not client_secret:
        logger.error("SCHWAB_API_KEY or SCHWAB_API_SECRET environment variables not set")
        return False
    
    # Truncate for logging
    display_id = f"{client_id[:4]}...{client_id[-4:]}" if len(client_id) > 8 else "[HIDDEN]"
    logger.info(f"Using client ID: {display_id}")
    
    # Select URL arrays based on environment
    auth_urls = SANDBOX_AUTH_URLS if use_sandbox else PRODUCTION_AUTH_URLS
    token_urls = SANDBOX_TOKEN_URLS if use_sandbox else PRODUCTION_TOKEN_URLS
    
    # Track results
    auth_test_passed = False
    token_test_passed = False
    
    # 1. Test each authorization endpoint
    # Generate a random state value
    state = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    # Define redirect URI for the OAuth flow
    # For testing, we use a non-existent callback that we don't expect to be called
    redirect_uri = "https://example.com/callback"
    
    # Define authorization parameters
    auth_params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'trading',
        'state': state
    }
    
    for auth_url in auth_urls:
        logger.info(f"Testing authorization endpoint: {auth_url}")
        
        # Build the authorization URL
        full_auth_url = f"{auth_url}?{urlencode(auth_params)}"
        
        try:
            # Test with a GET request (we don't expect this to succeed, just checking endpoint)
            logger.info(f"Sending request to {auth_url}...")
            response = requests.get(
                auth_url,
                params=auth_params,
                headers={"User-Agent": "Schwab OAuth2 Flow Test"},
                timeout=10,
                allow_redirects=False  # We don't want to follow redirects
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Headers: {dict(response.headers)}")
            
            # Check if we got a redirect or another valid response
            # 302 is expected for successful auth request (redirect to login)
            # 400 might indicate invalid parameters but endpoint exists
            # 401/403 might indicate authentication required
            if response.status_code in (302, 303, 307, 400, 401, 403):
                logger.info(f"✓ Authorization endpoint {auth_url} is working!")
                auth_test_passed = True
                break  # No need to try other URLs
            elif response.status_code == 404:
                logger.warning(f"✗ Endpoint not found (404): {auth_url}")
                # Continue to next URL
            elif response.status_code >= 500:
                logger.warning(f"✗ Server error ({response.status_code}): {auth_url}")
                # Continue to next URL
            else:
                logger.info(f"? Unexpected status {response.status_code}: {auth_url}")
                auth_test_passed = True  # Assume it works for now
                break
            
        except requests.RequestException as e:
            logger.error(f"✗ Connection error for {auth_url}: {str(e)}")
            # Continue to next URL
            
    if not auth_test_passed:
        logger.error("✗ All authorization endpoints failed!")
    else:
        logger.info("✓ Found working authorization endpoint!")

    
    # 2. Test token endpoints with a simulated token request
    # This is just a test, so we use a fake authorization code
    fake_code = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
    
    # Prepare token request payload
    token_payload = {
        'grant_type': 'authorization_code',
        'code': fake_code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'trading'
    }
    
    for token_url in token_urls:
        logger.info(f"Testing token endpoint: {token_url}")
        
        try:
            # Send the token request
            logger.info(f"Sending request to {token_url}...")
            token_response = requests.post(
                token_url,
                data=token_payload,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json',
                    'User-Agent': 'Schwab OAuth2 Flow Test'
                },
                timeout=15
            )
            
            logger.info(f"Response status: {token_response.status_code}")
            logger.info(f"Headers: {dict(token_response.headers)}")
            
            # We expect this to fail with a 400 since we're using a fake code
            # But a 400 error means the endpoint exists and is processing requests
            if token_response.status_code == 400:
                logger.info(f"\u2713 Token endpoint {token_url} returned 400 Bad Request - this is expected with a fake code")
                token_test_passed = True
                break  # Found working endpoint
            elif token_response.status_code == 401:
                logger.info(f"\u2713 Token endpoint {token_url} returned 401 Unauthorized - this is acceptable")
                token_test_passed = True
                break  # Found working endpoint
            elif token_response.status_code == 404:
                logger.warning(f"\u2717 Endpoint not found (404): {token_url}")
                # Continue to next URL
            elif token_response.status_code >= 500:
                logger.warning(f"\u2717 Server error ({token_response.status_code}): {token_url}")
                # Continue to next URL
            else:
                logger.info(f"? Unexpected status {token_response.status_code}: {token_url}")
                token_test_passed = True  # Assume it works
                break
            
            # Try to parse the response as JSON
            try:
                if token_response.status_code != 404 and 'application/json' in token_response.headers.get('content-type', ''):
                    response_data = token_response.json()
                    logger.info(f"Response content: {response_data}")
                    
                    # Check for specific OAuth error codes that indicate the endpoint is working
                    if response_data.get('error') in ('invalid_grant', 'invalid_client', 'invalid_request'):
                        logger.info(f"\u2713 Received valid OAuth error: {response_data.get('error')}")
                        token_test_passed = True
                        break  # Found working endpoint
            except ValueError:
                logger.warning("Could not parse token response as JSON")
            
        except requests.RequestException as e:
            logger.error(f"\u2717 Connection error for {token_url}: {str(e)}")
            # Continue to next URL
    
    if not token_test_passed:
        logger.error("\u2717 All token endpoints failed!")
    else:
        logger.info("\u2713 Found working token endpoint!")
    
    # Return overall test result
    return auth_test_passed and token_test_passed

def main():
    # Test both sandbox and production
    logger.info("====== Testing Schwab API OAuth2 Flow ======")
    
    # Start with production
    production_result = test_oauth_flow(use_sandbox=False)
    time.sleep(1)  # Small delay between tests
    sandbox_result = test_oauth_flow(use_sandbox=True)
    
    # Display recommendation
    if sandbox_result and not production_result:
        logger.info("✓ RECOMMENDATION: Use sandbox environment for OAuth2 authentication")
    elif production_result and not sandbox_result:
        logger.info("✓ RECOMMENDATION: Use production environment for OAuth2 authentication")
    elif sandbox_result and production_result:
        logger.info("✓ RECOMMENDATION: Both environments are accessible for OAuth2 - use sandbox for testing")
    else:
        logger.error("✗ RECOMMENDATION: OAuth2 flow not accessible in either environment - check your credentials and endpoints")
    
    logger.info("====== Schwab API OAuth2 Flow Test Complete ======")
    return production_result or sandbox_result

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
