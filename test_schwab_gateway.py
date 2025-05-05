#!/usr/bin/env python3

"""
Test connectivity to the Schwab Gateway

This script tests various paths on the sws-gateway.schwab.com domain
to identify which ones might be used in the OAuth flow.
"""

import os
import logging
import requests
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gateway_paths():
    """Test common paths on the Schwab Gateway domain"""
    base_url = "https://sws-gateway.schwab.com"
    
    # Paths to test
    paths = [
        "/",  # Root path
        "/api",  # Common API base path
        "/v1",  # Version path
        "/oauth",  # OAuth base path
        "/oauth/authorize",  # OAuth authorization endpoint
        "/v1/oauth/authorize",  # Versioned OAuth authorization endpoint
        "/oauth/token",  # OAuth token endpoint
        "/v1/oauth/token",  # Versioned OAuth token endpoint
        "/broker",  # Broker API path
        "/broker/rest",  # Broker REST API path
        "/broker/rest/oauth/authorize",  # Full broker OAuth path
        "/broker/rest/oauth/token",  # Full broker OAuth token path
        "/identity",  # Identity services
        "/auth",  # Auth services
    ]
    
    results = {}
    headers = {"User-Agent": "TradingBot-Test/1.0"}
    
    for path in paths:
        url = urljoin(base_url, path)
        try:
            logger.info(f"Testing URL: {url}")
            response = requests.head(url, headers=headers, timeout=10)
            status = response.status_code
            response_headers = dict(response.headers)
            correlation_id = response_headers.get('Schwab-Client-CorrelId', 'None')
            
            results[url] = {
                "status": status,
                "correlation_id": correlation_id,
                "headers": response_headers
            }
            
            logger.info(f"Response status: {status}")
            if correlation_id != 'None':
                logger.info(f"Correlation ID: {correlation_id}")
            if 'server' in response_headers:
                logger.info(f"Server: {response_headers['server']}")
                
        except requests.RequestException as e:
            logger.error(f"Error testing {url}: {str(e)}")
            results[url] = {"error": str(e)}
    
    # Print summary of results
    logger.info("\nSummary of test results:")
    logger.info("-" * 80)
    for url, result in results.items():
        if "error" in result:
            logger.info(f"{url}: ERROR - {result['error']}")
        else:
            logger.info(f"{url}: Status {result['status']}")
            if result['correlation_id'] != 'None':
                logger.info(f"  - Found correlation ID: {result['correlation_id']}")
    
    # Identify potentially working endpoints (non-404, 403 with correlation ID, etc.)
    logger.info("\nPotentially working endpoints:")
    logger.info("-" * 80)
    for url, result in results.items():
        if "error" not in result:
            status = result["status"]
            has_correlation = result["correlation_id"] != 'None'
            
            # Consider endpoints that don't return 404 as potentially working
            if status != 404:
                if status == 200:
                    logger.info(f"{url}: SUCCESS (200 OK)")
                elif status == 401 or status == 403:
                    if has_correlation:
                        logger.info(f"{url}: LIKELY VALID (Returned {status} with correlation ID)")
                    else:
                        logger.info(f"{url}: POSSIBLY VALID (Returned {status} but no correlation ID)")
                elif status == 500 and has_correlation:
                    # Schwab's API often returns 500 with correlation ID for OAuth endpoints
                    logger.info(f"{url}: LIKELY VALID (Returned 500 with correlation ID)")
                elif status >= 500:
                    logger.info(f"{url}: POSSIBLY VALID (Server error {status})")
                else:
                    logger.info(f"{url}: POSSIBLY VALID (Status {status})")

def main():
    """Run all tests"""
    logger.info("Testing Schwab Gateway connectivity...")
    test_gateway_paths()
    logger.info("Testing complete.")

if __name__ == "__main__":
    main()
