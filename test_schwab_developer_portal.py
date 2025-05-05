#!/usr/bin/env python3
"""
Test connectivity to the Schwab Developer Portal

This script tests connections to the Schwab Developer Portal
to check DNS resolution and connectivity issues.
"""

import os
import sys
import socket
import requests
from urllib.parse import urlparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# List of domains to test
DOMAINS = [
    "developer.schwab.com",
    "api.schwab.com",
    "broker-api.schwab.com",
    "trader-api.schwab.com",
    "auth.schwab.com",
    "schwabapi.com",
    "api.schwabapi.com",
    "sandbox.schwabapi.com",
    "api-sandbox.schwabapi.com",
    "auth.schwab-sandbox.com",
]

def test_dns_resolution(domain):
    """Test DNS resolution for a domain"""
    try:
        logger.info(f"DNS lookup for {domain}...")
        ip_address = socket.gethostbyname(domain)
        logger.info(f"✓ Success: {domain} resolves to {ip_address}")
        return True
    except socket.gaierror as e:
        logger.error(f"✗ Failed: {domain} - {str(e)}")
        return False

def test_http_connection(domain):
    """Test HTTP connection to domain"""
    for protocol in ["https"]:
        url = f"{protocol}://{domain}"
        try:
            logger.info(f"Testing connection to {url}...")
            response = requests.head(
                url, 
                headers={"User-Agent": "Schwab API Test Script"}, 
                timeout=10
            )
            status = response.status_code
            logger.info(f"✓ Response: {status} - {url}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Connection failed: {url} - {str(e)}")
            return False

def main():
    """Run all tests"""
    logger.info("============================================")
    logger.info("Schwab Developer Portal Connectivity Tests")
    logger.info("============================================")
    
    dns_results = {}
    http_results = {}
    
    # Test DNS resolution
    logger.info("\nTesting DNS Resolution...")
    for domain in DOMAINS:
        dns_results[domain] = test_dns_resolution(domain)
    
    # Test HTTP connectivity
    logger.info("\nTesting HTTP Connectivity...")
    for domain in DOMAINS:
        if dns_results[domain]:
            http_results[domain] = test_http_connection(domain)
        else:
            http_results[domain] = False
    
    # Summary
    logger.info("\n============================================")
    logger.info("Summary Report")
    logger.info("============================================")
    
    working_domains = []
    dns_issues = []
    connection_issues = []
    
    for domain in DOMAINS:
        if dns_results[domain] and http_results[domain]:
            working_domains.append(domain)
            logger.info(f"✓ {domain}: Fully operational")
        elif not dns_results[domain]:
            dns_issues.append(domain)
            logger.info(f"✗ {domain}: DNS resolution failed")
        else:
            connection_issues.append(domain)
            logger.info(f"✗ {domain}: HTTP connection failed")
    
    logger.info("\nRecommendations:")
    if dns_issues:
        logger.info(f"- The following domains have DNS issues: {', '.join(dns_issues)}")
        logger.info("  This suggests these domains might not exist or there are DNS configuration issues")
    
    if connection_issues:
        logger.info(f"- The following domains resolve but have connection issues: {', '.join(connection_issues)}")
        logger.info("  This could indicate firewalls, proxies, or server-side issues")
    
    if working_domains:
        logger.info(f"- Use the following working domains for your API URLs: {', '.join(working_domains)}")
    else:
        logger.info("- No working domains found. Check your internet connection or contact Schwab support")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"\nTest failed with error: {str(e)}")
