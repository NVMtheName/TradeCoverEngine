#!/usr/bin/env python3
"""
Comprehensive API endpoint testing script for Schwab API

This script attempts to connect to various possible Schwab API endpoints
using the provided API key and secret. It tries multiple patterns
and variations to determine which endpoints are working.
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

# Constants
USE_SANDBOX = input("Use sandbox environment? (y/n): ").lower() == 'y'

# Different URL patterns to try
AUTH_URLS = [
    # Standard OAuth2 patterns
    "https://developer.schwab.com/oauth/authorize",  # Direct developer portal
    "https://api.schwab.com/oauth/authorize",       # Root domain with OAuth prefix
    "https://broker-api.schwab.com/oauth/authorize", # Broker API subdomain
    "https://trader-api.schwab.com/oauth/authorize", # Trader API subdomain
    "https://auth.schwab.com/oauth/authorize",      # Authentication subdomain
    # Original patterns
    "https://api.schwabapi.com/oauth2/authorize",   # OAuth2 prefix
    "https://api.schwabapi.com/oauth/authorize",    # OAuth prefix
    "https://schwabapi.com/broker/rest/oauth/authorize",  # Legacy path
]

TOKEN_URLS = [
    # Standard OAuth2 patterns
    "https://developer.schwab.com/oauth/token",     # Direct developer portal
    "https://api.schwab.com/oauth/token",          # Root domain with OAuth prefix
    "https://broker-api.schwab.com/oauth/token",    # Broker API subdomain 
    "https://trader-api.schwab.com/oauth/token",    # Trader API subdomain
    "https://auth.schwab.com/oauth/token",          # Authentication subdomain
    # Original patterns
    "https://api.schwabapi.com/oauth2/token",      # OAuth2 prefix
    "https://api.schwabapi.com/oauth/token",       # OAuth prefix
    "https://schwabapi.com/broker/rest/oauth/token",  # Legacy path
]

API_URLS = [
    # Base API endpoints
    "https://api.schwab.com",                      # Root domain  
    "https://api.schwabapi.com",                   # API subdomain
    "https://broker-api.schwab.com",               # Broker API subdomain
    "https://trader-api.schwab.com",               # Trader API subdomain
    "https://schwabapi.com/broker/rest",           # Legacy path
]

CLIENT_INFO_PATHS = [
    "/v1/oauth/clientinfo",                        # OAuth2 client info
    "/oauth2/clientinfo",                          # Alternative path
    "/oauth/clientinfo",                           # Alternative path
]

ACCOUNT_PATHS = [
    "/v1/accounts",                               # Accounts endpoint
    "/v1/brokerage/accounts",                      # Brokerage accounts endpoint
    "/brokerage/accounts",                         # Alternative path
    "/accounts",                                   # Root path
]

def test_auth_endpoints():
    """Test authorization endpoints"""
    logger.info("\n===== Testing Authorization Endpoints =====")
    redirect_uri = "https://localhost/oauth/callback"  # Dummy for testing
    
    auth_params = {
        'client_id': API_KEY,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'trading'
    }
    
    for url in (SANDBOX_AUTH_URLS if USE_SANDBOX else AUTH_URLS):
        try:
            logger.info(f"Testing: {url}")
            full_url = f"{url}?{urlencode(auth_params)}"
            
            response = requests.head(
                url,
                headers={
                    "User-Agent": "Trading Bot API Test Script",
                    "Accept": "application/json"
                },
                timeout=10
            )
            
            logger.info(f"  Status: {response.status_code}")
            logger.info(f"  Headers: {dict(response.headers)}")
            
            # Log correlation ID if present
            if 'Schwab-Client-CorrelId' in response.headers:
                logger.info(f"  Correlation ID: {response.headers.get('Schwab-Client-CorrelId')}")
            
            # Special handling for common response codes
            if response.status_code == 404:
                logger.warning(f"  Endpoint not found")
            elif response.status_code == 403:
                logger.warning(f"  Forbidden access - may need API key approval")
            elif response.status_code == 401:
                logger.warning(f"  Unauthorized - check credentials")
            elif response.status_code >= 200 and response.status_code < 400:
                logger.info(f"  Successful connection")
            elif response.status_code == 500 and 'Schwab-Client-CorrelId' in response.headers:
                logger.info(f"  Received expected 500 with correlation ID - this is actually a valid response for Schwab OAuth")
                
        except Exception as e:
            logger.error(f"  Error: {str(e)}")
        
        print()  # Add space between tests
        time.sleep(1)  # Avoid rate limiting

def test_client_info_endpoints():
    """Test client information endpoints"""
    logger.info("\n===== Testing Client Info Endpoints =====")
    
    headers = {
        "User-Agent": "Trading Bot API Test Script",
        "Accept": "application/json",
        "clientid": API_KEY,  # Some endpoints may use this header
    }
    
    for base_url in (SANDBOX_API_URLS if USE_SANDBOX else API_URLS):
        for path in CLIENT_INFO_PATHS:
            try:
                url = f"{base_url}{path}"
                logger.info(f"Testing: {url}")
                
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=10
                )
                
                logger.info(f"  Status: {response.status_code}")
                logger.info(f"  Headers: {dict(response.headers)}")
                
                # Log successful response content
                if response.status_code >= 200 and response.status_code < 300:
                    try:
                        data = response.json()
                        logger.info(f"  Response: {json.dumps(data, indent=2)}")
                    except:
                        logger.info(f"  Response: {response.text[:100]}...")
                
            except Exception as e:
                logger.error(f"  Error: {str(e)}")
            
            print()  # Add space between tests
            time.sleep(1)  # Avoid rate limiting

def test_account_endpoints():
    """Test account information endpoints"""
    logger.info("\n===== Testing Account Endpoints =====")
    
    # For demo only - we need OAuth tokens for most account endpoints
    # This is just to check if the endpoint exists
    
    headers = {
        "User-Agent": "Trading Bot API Test Script",
        "Accept": "application/json",
        "clientid": API_KEY,  # Some endpoints may use this header
    }
    
    for base_url in (SANDBOX_API_URLS if USE_SANDBOX else API_URLS):
        for path in ACCOUNT_PATHS:
            try:
                url = f"{base_url}{path}"
                logger.info(f"Testing: {url}")
                
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=10
                )
                
                logger.info(f"  Status: {response.status_code}")
                logger.info(f"  Headers: {dict(response.headers)}")
                
                # Analysis of response codes
                if response.status_code == 401:
                    logger.info("  Got 401 Unauthorized - Expected since we don't have auth tokens")
                    logger.info("  This indicates the endpoint exists but requires authentication")
                    # If we got 401 rather than 404, the endpoint might exist
                
            except Exception as e:
                logger.error(f"  Error: {str(e)}")
            
            print()  # Add space between tests
            time.sleep(1)  # Avoid rate limiting

def test_all_endpoints():
    """Run all endpoint tests"""
    # Define sandbox URLs if using sandbox
    global SANDBOX_AUTH_URLS, SANDBOX_TOKEN_URLS, SANDBOX_API_URLS
    
    if USE_SANDBOX:
        # Replace domain names with sandbox versions
        SANDBOX_AUTH_URLS = [
            url.replace('schwab.com', 'schwab-sandbox.com')
               .replace('schwabapi.com', 'sandbox.schwabapi.com') 
            for url in AUTH_URLS
        ]
        SANDBOX_TOKEN_URLS = [
            url.replace('schwab.com', 'schwab-sandbox.com')
               .replace('schwabapi.com', 'sandbox.schwabapi.com')
            for url in TOKEN_URLS
        ]
        SANDBOX_API_URLS = [
            url.replace('schwab.com', 'schwab-sandbox.com')
               .replace('schwabapi.com', 'sandbox.schwabapi.com')
            for url in API_URLS
        ]
        
        logger.info("Using sandbox environment")
        logger.info(f"Sandbox Auth URLs: {SANDBOX_AUTH_URLS}")
    else:
        logger.info("Using production environment")
    
    logger.info(f"API Key: {API_KEY[:4]}...{API_KEY[-4:]}")
    
    # Run tests
    test_auth_endpoints()
    test_client_info_endpoints()
    test_account_endpoints()
    
    logger.info("\n===== Testing Complete =====")

if __name__ == "__main__":
    try:
        test_all_endpoints()
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"\nTest failed with error: {str(e)}")
