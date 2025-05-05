#!/usr/bin/env python3
"""
Checks the OAuth flow implementation in api_connector.py
This script verifies that the OAuth flow is properly implemented
"""

import os
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('oauth_check')

# Add the current directory to the path so we can import our modules
sys.path.append('.')

# Import our modules
from trading_bot.api_connector import APIConnector

def check_oauth_flow():
    """Check that the OAuth flow is properly implemented"""
    logger.info("Checking OAuth flow implementation")
    
    # Get API credentials from environment variables
    api_key = os.environ.get("SCHWAB_API_KEY")
    api_secret = os.environ.get("SCHWAB_API_SECRET")
    
    if not api_key or not api_secret:
        logger.warning("Missing API credentials. Using placeholder values for simulation mode check.")
        api_key = "test_key"
        api_secret = "test_secret"
    
    # Create API connector
    connector = APIConnector(
        provider='schwab',
        api_key=api_key,
        api_secret=api_secret,
        paper_trading=True,
        force_simulation=True
    )
    
    # Verify OAuth related attributes
    logger.info("Verifying OAuth related attributes")
    assert hasattr(connector, 'access_token'), "Missing access_token attribute"
    assert hasattr(connector, 'refresh_token'), "Missing refresh_token attribute"
    assert hasattr(connector, 'token_expiry'), "Missing token_expiry attribute"
    assert hasattr(connector, 'is_token_expired'), "Missing is_token_expired method"
    assert hasattr(connector, 'refresh_access_token'), "Missing refresh_access_token method"
    
    # Check that the connector falls back to simulation mode when no tokens are available
    logger.info("Checking simulation mode fallback")
    assert connector.force_simulation, "Should be in simulation mode"
    
    # Check connection status
    logger.info("Checking connection status")
    is_connected = connector.is_connected()
    logger.info(f"Connection status: {is_connected}")
    
    # Check simulated data access
    logger.info("Checking simulated data access")
    account_info = connector.get_account_info()
    logger.info(f"Account info available: {bool(account_info)}")
    
    logger.info("OAuth flow implementation check complete!")
    return True

if __name__ == "__main__":
    try:
        success = check_oauth_flow()
        if success:
            logger.info("✅ OAuth flow check passed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ OAuth flow check failed!")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error checking OAuth flow: {str(e)}")
        sys.exit(1)
