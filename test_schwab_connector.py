#!/usr/bin/env python3

"""
Test the new specialized Schwab connector with improved reliability.

This script tests the connection and functionality of the specialized 
Schwab connector built to handle Schwab's API robustly.
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our connector
from trading_bot.schwab_connector import SchwabConnector

def test_connector():
    """Test the Schwab connector with production environment"""
    # Load credentials from environment (if available)
    client_id = os.environ.get("SCHWAB_API_KEY")
    client_secret = os.environ.get("SCHWAB_API_SECRET")
    
    if not client_id or not client_secret:
        logger.warning("Missing Schwab API credentials. Please set SCHWAB_API_KEY and SCHWAB_API_SECRET.")
        logger.info("Continuing with placeholder credentials for testing purposes only.")
        client_id = "placeholder_id"
        client_secret = "placeholder_secret"
    
    # Create connector for the production environment
    logger.info("Creating Schwab connector for production environment")
    connector = SchwabConnector(
        client_id=client_id,
        client_secret=client_secret,
        is_sandbox=False,  # Use production environment
    )
    
    # Display connection info
    logger.info(f"Schwab connector initialized with environment: {connector.is_sandbox}")
    logger.info(f"API base URL: {connector.api_base_url}")
    
    # Get diagnostic info
    diagnostics = connector.get_diagnostic_info()
    logger.info("Connection Diagnostics:")
    for key, value in diagnostics.items():
        logger.info(f"  {key}: {value}")
    
    # Test connection - this will also try to use any tokens if available
    logger.info("Testing connection to Schwab API...")
    is_connected = connector.is_connected()
    logger.info(f"Connection test result: {'SUCCESS' if is_connected else 'FAILED'}")
    
    # Get updated diagnostics
    diagnostics = connector.get_diagnostic_info()
    logger.info("Updated connection status: " + diagnostics['connection_status'])
    
    if not is_connected:
        logger.warning("Connection test failed. This is expected without valid OAuth tokens.")
        logger.info("To complete OAuth authentication, use the web application's OAuth flow.")
    
    return is_connected

def test_sandbox_connector():
    """Test the Schwab connector with sandbox environment"""
    # Load credentials from environment (if available)
    client_id = os.environ.get("SCHWAB_API_KEY")
    client_secret = os.environ.get("SCHWAB_API_SECRET")
    
    if not client_id or not client_secret:
        logger.warning("Missing Schwab API credentials. Please set SCHWAB_API_KEY and SCHWAB_API_SECRET.")
        logger.info("Continuing with placeholder credentials for testing purposes only.")
        client_id = "placeholder_id"
        client_secret = "placeholder_secret"
    
    # Create connector for the sandbox environment
    logger.info("Creating Schwab connector for sandbox environment")
    connector = SchwabConnector(
        client_id=client_id,
        client_secret=client_secret,
        is_sandbox=True,  # Use sandbox environment
    )
    
    # Display connection info
    logger.info(f"Schwab connector initialized with environment: {'sandbox' if connector.is_sandbox else 'production'}")
    logger.info(f"API base URL: {connector.api_base_url}")
    
    # Get diagnostic info
    diagnostics = connector.get_diagnostic_info()
    logger.info("Connection Diagnostics:")
    for key, value in diagnostics.items():
        logger.info(f"  {key}: {value}")
    
    # Test connection - this will also try to use any tokens if available
    logger.info("Testing connection to Schwab API (sandbox)...")
    is_connected = connector.is_connected()
    logger.info(f"Connection test result: {'SUCCESS' if is_connected else 'FAILED'}")
    
    # Get updated diagnostics
    diagnostics = connector.get_diagnostic_info()
    logger.info("Updated connection status: " + diagnostics['connection_status'])
    
    if not is_connected:
        logger.warning("Connection test failed. This is expected without valid OAuth tokens.")
        logger.info("To complete OAuth authentication, use the web application's OAuth flow.")
    
    return is_connected

def main():
    """Run the test cases for Schwab connector"""
    logger.info("===== TESTING SCHWAB CONNECTOR =====")
    logger.info("Testing production environment first:")
    production_result = test_connector()
    
    logger.info("\n===== TESTING SANDBOX ENVIRONMENT =====")
    sandbox_result = test_sandbox_connector()
    
    # Summary
    logger.info("\n===== TEST SUMMARY =====")
    logger.info(f"Production environment test: {'PASSED' if production_result else 'FAILED (Expected without tokens)'}")
    logger.info(f"Sandbox environment test: {'PASSED' if sandbox_result else 'FAILED (Expected without tokens)'}")
    logger.info("\nNote: Full connection tests will pass only after completing OAuth authentication")
    logger.info("through the web application's OAuth flow.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())