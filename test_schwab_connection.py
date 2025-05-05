#!/usr/bin/env python3
"""
Test the connection to Schwab API with the updated v2 endpoints
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API credentials
API_KEY = os.environ.get("SCHWAB_API_KEY") or input("Enter your Schwab API Key: ")
API_SECRET = os.environ.get("SCHWAB_API_SECRET") or input("Enter your Schwab API Secret: ")

def test_connection(use_sandbox=True):
    """Test connection to Schwab API authorization endpoint"""
    # Based on the successful domains from our DNS tests
    domains = [
        "developer.schwab.com",
        "api.schwab.com",
        "api.schwabapi.com",
        "sandbox.schwabapi.com", # Only for sandbox
    ]
    
    paths = [
        "/oauth/authorize",
        "/oauth2/authorize",
        "/v1/oauth/authorize",
        "/products/trader-api--individual/oauth/authorize",
    ]
    
    # For sandbox, transform domains
    if use_sandbox:
        sandbox_domains = []
        for domain in domains:
            if domain == "sandbox.schwabapi.com":
                sandbox_domains.append(domain) # Already sandbox
            elif "schwab.com" in domain:
                sandbox_domains.append(domain.replace("schwab.com", "schwab-sandbox.com"))
            elif "schwabapi.com" in domain:
                sandbox_domains.append(domain.replace("schwabapi.com", "sandbox.schwabapi.com"))
        domains = sandbox_domains
    
    logger.info(f"Testing connection to Schwab API ({', '.join(domains)})")
    logger.info(f"Environment: {'Sandbox' if use_sandbox else 'Production'}")
    
    # Dummy redirect URI for testing only
    redirect_uri = "https://localhost/oauth/callback"
    
    # Authorization parameters
    auth_params = {
        'client_id': API_KEY,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'trading'
    }
    
    # Try each combination of domain and path
    working_endpoints = []
    for domain in domains:
        for path in paths:
            auth_url = f"https://{domain}{path}"
            logger.info(f"\nTesting endpoint: {auth_url}")
            
            try:
                # Make a HEAD request to check endpoint existence
                # Note: For Schwab API, a 500 error with correlation ID is a normal response
                response = requests.head(
                    auth_url,
                    headers={"User-Agent": "Trading Bot Connection Test"},
                    timeout=10
                )
                
                status = response.status_code
                logger.info(f"Status code: {status}")
                logger.info(f"Headers: {dict(response.headers)}")
                
                if 'Schwab-Client-CorrelId' in response.headers:
                    correl_id = response.headers.get('Schwab-Client-CorrelId')
                    logger.info(f"Correlation ID: {correl_id}")
                    logger.info("✓ This is a valid Schwab API endpoint! (Correlation ID present)")
                    working_endpoints.append(auth_url)
                    
                elif status >= 200 and status < 400:
                    logger.info("✓ Endpoint responded with successful status")
                    working_endpoints.append(auth_url)
                    
                elif status == 404:
                    logger.warning("✗ Endpoint not found")
                    
                else:
                    logger.warning(f"? Endpoint returned status {status} - may require API key approval")
            except Exception as e:
                logger.error(f"✗ Error connecting to endpoint: {str(e)}")
    
    # Summary
    if working_endpoints:
        logger.info(f"\n✓ Found {len(working_endpoints)} working Schwab API endpoints:")
        for endpoint in working_endpoints:
            logger.info(f"  - {endpoint}")
    else:
        logger.error("\n✗ No working Schwab API endpoints found")
    
    return working_endpoints

def main():
    # Default to sandbox for testing
    use_sandbox = True
    
    # Test both environments
    print("====== Testing Sandbox Environment ======")
    sandbox_endpoints = test_connection(use_sandbox=True)
    
    print("\n\n====== Testing Production Environment ======")
    production_endpoints = test_connection(use_sandbox=False)
    
    # Summary
    print("\n\n====== Summary ======")
    print(f"Sandbox working endpoints: {len(sandbox_endpoints)}")
    print(f"Production working endpoints: {len(production_endpoints)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"\nTest failed with error: {str(e)}")
