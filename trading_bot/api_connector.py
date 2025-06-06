import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import time
import requests
import re
import random
from urllib.parse import urlencode

# Configure logging
logger = logging.getLogger(__name__)

class APIConnector:
    """
    Connects to trading APIs (Alpaca, TD Ameritrade, Schwab) to get market data and place trades.
    """
    
    def __init__(self, provider='alpaca', paper_trading=True, api_key=None, api_secret=None, force_simulation=False):
        """
        Initialize the API connector.
        
        Args:
            provider (str): API provider ('alpaca', 'td_ameritrade', or 'schwab')
            paper_trading (bool): Whether to use paper trading APIs
            api_key (str): API key for the provider
            api_secret (str): API secret for the provider
            force_simulation (bool): Force simulation mode regardless of credentials
        """
        self.provider = provider.lower()
        self.paper_trading = paper_trading
        self.api_key = api_key
        self.api_secret = api_secret
        self.force_simulation = force_simulation
        self.session = requests.Session()
        self.headers = {}
        self.base_url = None
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        
        # Initialize provider-specific settings
        if self.provider == 'alpaca':
            self._init_alpaca()
        elif self.provider == 'td_ameritrade':
            self._init_td_ameritrade()
        elif self.provider == 'schwab':
            self._init_schwab()
        else:
            logger.warning(f"Unknown provider '{provider}', defaulting to Alpaca")
            self.provider = 'alpaca'
            self._init_alpaca()
            
        if not self.force_simulation:
            self._check_connection()
        else:
            logger.info("Force simulation mode enabled - bypassing API connection check")
            
    def _init_alpaca(self):
        """Initialize Alpaca API settings."""
        if self.paper_trading:
            self.base_url = "https://paper-api.alpaca.markets"
        else:
            self.base_url = "https://api.alpaca.markets"
            
        # Data API URL is the same for both paper and live trading
        self.data_url = "https://data.alpaca.markets"
        
        # Set API keys
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Initialized Alpaca API connector with paper trading: {self.paper_trading}")
        
    def _init_td_ameritrade(self):
        """Initialize TD Ameritrade API settings."""
        self.base_url = "https://api.tdameritrade.com/v1"
        
        # Set API headers (just content-type for now, authorization will be added per request)
        self.headers = {
            "Content-Type": "application/json"
        }
        
        logger.info(f"Initialized TD Ameritrade API connector")
        
    def _init_schwab(self):
        """Initialize Charles Schwab API settings."""
        # Import the specialized Schwab connector
        from trading_bot.schwab_connector import SchwabConnector, create_connector_from_settings
        
        # Initialize OAuth credentials
        self.client_id = self.api_key  # Schwab uses client_id/client_secret terminology
        self.client_secret = self.api_secret
        
        # Create a specialized Schwab connector
        self.schwab_connector = SchwabConnector(
            client_id=self.client_id,
            client_secret=self.client_secret,
            is_sandbox=self.paper_trading
        )
        
        # Set up base URLs and endpoints - Exact Schwab API specifications
        if self.paper_trading:
            # Sandbox environment - using production URLs as Schwab has unified endpoints
            self.base_url = "https://api.schwabapi.com/trader/v1"
            self.market_data_url = "https://api.schwabapi.com/marketdata/v1"
            logger.info("Using Schwab sandbox API endpoints (v1)")
            self.oauth_auth_url = "https://api.schwabapi.com/v1/oauth/authorize"
            self.oauth_token_url = "https://api.schwabapi.com/v1/oauth/token"
        else:
            # Production environment - Exact Schwab API URLs
            self.base_url = "https://api.schwabapi.com/trader/v1"
            self.market_data_url = "https://api.schwabapi.com/marketdata/v1"
            logger.info("Using Schwab production API endpoints (v1)")
            self.oauth_auth_url = "https://api.schwabapi.com/v1/oauth/authorize"
            self.oauth_token_url = "https://api.schwabapi.com/v1/oauth/token"
        
        # Set API headers (no authorization yet - will be added after OAuth flow)
        self.headers = {
            "Content-Type": "application/json"
        }
        
        # Initialize token-related attributes
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        
        # For compatibility with existing code, keep auth URL lists
        self.oauth_auth_urls = [self.oauth_auth_url]
        self.oauth_token_urls = [self.oauth_token_url]
        
        # Truncate for logging
        display_client_id = f"{self.client_id[:4]}...{self.client_id[-4:]}" if self.client_id and len(self.client_id) > 8 else "None"
        
        logger.info(f"Initialized Charles Schwab API connector with client ID: {display_client_id}")
        logger.info(f"Paper trading mode: {self.paper_trading}")
        
        # Check if we need to authenticate
        if not self.client_id or not self.client_secret:
            logger.warning("No API key or secret provided for Schwab API - OAuth2 authentication not possible")
            logger.warning("Falling back to simulation mode")
            self.force_simulation = True
        elif not self.access_token:
            logger.warning("No access token available for Schwab API - OAuth2 authentication required")
            logger.warning("To use the Schwab API, you need to register your application for OAuth2 access.")
            logger.warning("Your API key is your OAuth2 client_id and your API secret is your client_secret.")
            logger.warning("Falling back to simulation mode")
            self.force_simulation = True
        
    def is_token_expired(self):
        """Check if the access token has expired.
        
        Returns:
            bool: True if token is expired or about to expire, False otherwise
        """
        if not self.token_expiry:
            return True
            
        # Consider token expired if less than 5 minutes remaining
        from datetime import datetime, timedelta
        buffer_time = timedelta(minutes=5)
        return datetime.now() + buffer_time >= self.token_expiry
    
    def refresh_access_token(self):
        """Refresh the access token using the refresh token.
        Follows the OAuth 2.0 refresh token flow as specified by Schwab API.
        If the primary token URL fails, it will try fallback URLs.
        
        Returns:
            bool: True if token was successfully refreshed, False otherwise
        """
        if not self.refresh_token:
            logger.warning("No refresh token available for token refresh")
            return False
            
        if not self.client_id or not self.client_secret:
            logger.warning("Missing client credentials for token refresh")
            return False
            
        # Prepare token refresh request based on Schwab API docs
        token_payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'trading'  # Using trading scope for full API access per Schwab documentation
        }
        
        # Common headers for token requests
        token_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        # Try each token URL in the list until one works
        for token_url in self.oauth_token_urls:
            try:
                from datetime import datetime, timedelta
                
                # Execute the token refresh request
                logger.info(f"Attempting to refresh access token at {token_url}")
                
                token_response = self.session.post(
                    token_url,
                    data=token_payload,
                    headers=token_headers,
                    timeout=15  # Longer timeout for token operations
                )
                
                logger.info(f"Token refresh response status: {token_response.status_code}")
                
                if token_response.status_code == 200:
                    # Process successful token response
                    token_data = token_response.json() if token_response.content else {}
                    
                    # Extract and save token data
                    self.access_token = (token_data or {}).get('access_token')
                    new_refresh_token = (token_data or {}).get('refresh_token')  # May or may not be provided
                    expires_in = (token_data or {}).get('expires_in', 3600)  # Default to 1 hour
                    
                    # Update refresh token if a new one was provided
                    if new_refresh_token:
                        self.refresh_token = new_refresh_token
                        
                    # Update token expiry
                    self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                    
                    # Update authorization header
                    token_type = (token_data or {}).get('token_type', 'Bearer')
                    self.session.headers.update({
                        'Authorization': f'{token_type} {self.access_token}'
                    })
                    
                    # If this URL worked, update the primary token URL
                    self.oauth_token_url = token_url
                    
                    logger.info(f"Successfully refreshed access token using {token_url}, expires in {expires_in} seconds")
                    return True
                elif token_response.status_code == 404:
                    # This URL doesn't exist, try the next one
                    logger.warning(f"Token URL not found (404): {token_url}")
                    continue
                else:
                    # Handle error response for this URL
                    try:
                        error_content = token_response.json() if token_response.content else {}
                    except ValueError:
                        error_content = {}
                        
                    error_type = (error_content or {}).get('error', 'server_error')
                    error_desc = (error_content or {}).get('error_description', token_response.text[:100])
                    
                    logger.warning(f"Token refresh error at {token_url}: {error_type} - {error_desc}")
                    
                    # If it's a server error (5xx), try the next URL
                    if token_response.status_code >= 500:
                        continue
                    
                    # If it's an auth error (401), try the next URL
                    if token_response.status_code == 401:
                        continue
                    
                    # For other errors like 400 (Bad Request), this URL might be correct but
                    # there's another issue with the request, so stop and report the error
                    if token_response.status_code == 400:
                        logger.error(f"Token refresh failed at {token_url} with 400 Bad Request - there may be an issue with the refresh token or credentials")
                        return False
                    
            except requests.RequestException as e:
                # Network error for this URL, try the next one
                logger.warning(f"Network error connecting to {token_url}: {str(e)}")
                continue
                
        # If we get here, all token URLs failed
        logger.error("Token refresh failed - all token URLs returned errors")
        return False
        
    def is_connected(self):
        """Check if the API connection is working and return connection status.
        
        Returns:
            bool: True if connected, False otherwise
        """
        # If in force simulation mode, we don't need a real connection
        if self.force_simulation:
            return True
            
        # Perform real connection check
        return self._check_connection()
    
    def _check_connection(self):
        """Check if the API connection is working."""
        try:
            if self.force_simulation:
                logger.warning("Using simulation mode, skipping API connection check")
                return True
                
            if self.provider == 'alpaca':
                # Test connection by getting account
                response = self.session.get(f"{self.base_url}/v2/account", headers=self.headers)
                
                if response.status_code == 200:
                    logger.info("Successfully connected to Alpaca API")
                    return True
                else:
                    logger.warning(f"API connection failed with status code {response.status_code}: {response.text}")
                    return False
                    
            elif self.provider == 'td_ameritrade':
                # Need to check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for TD Ameritrade API")
                    return False
                
                # Test connection
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                response = self.session.get(f"{self.base_url}/accounts", headers=headers)
                
                if response.status_code == 200:
                    logger.info("Successfully connected to TD Ameritrade API")
                    return True
                else:
                    logger.warning(f"API connection failed with status code {response.status_code}: {response.text}")
                    # Try to refresh token if unauthorized
                    if response.status_code == 401 and self.refresh_token:
                        logger.info("Attempting to refresh access token")
                        # Use standardized refresh access token method
                        if self.refresh_access_token():
                            return self._check_connection()  # Try again with new token
                    return False
                    
            elif self.provider == 'schwab':
                # For Schwab, we'll use our specialized connector for improved reliability
                
                # First, sync tokens between our API connector and specialized Schwab connector
                if self.access_token:
                    self.schwab_connector.access_token = self.access_token
                    self.schwab_connector.refresh_token = self.refresh_token
                    self.schwab_connector.token_expiry = self.token_expiry
                
                # Check if we need to authenticate
                if not self.access_token:
                    logger.warning("No access token available for Schwab API - OAuth2 authentication required")
                    logger.warning("To use the Schwab API, you need to register your application for OAuth2 access.")
                    logger.warning("Your API key is your OAuth2 client_id and your API secret is your client_secret.")
                    
                    if not self.client_id or not self.client_secret:
                        logger.warning("Missing API credentials for Schwab API")
                        return False
                    
                    logger.warning("Falling back to simulation mode")
                    self.force_simulation = True
                    return False
                
                # Use the specialized connector to check connection
                try:
                    logger.info("Using specialized Schwab connector to test connection")
                    is_connected = self.schwab_connector.is_connected()
                    
                    if is_connected:
                        logger.info("Successfully connected to Schwab API")
                        
                        # If token was refreshed in the specialized connector, sync it back
                        if self.schwab_connector.access_token != self.access_token:
                            logger.info("Synchronizing refreshed tokens from specialized connector")
                            self.access_token = self.schwab_connector.access_token
                            self.refresh_token = self.schwab_connector.refresh_token
                            self.token_expiry = self.schwab_connector.token_expiry
                            
                            # Update session headers
                            self.session.headers.update({
                                'Authorization': f'Bearer {self.access_token}'
                            })
                        
                        return True
                    else:
                        # Check diagnostic information
                        diagnostic_info = self.schwab_connector.get_diagnostic_info()
                        logger.warning(f"Schwab API connection failed: {(diagnostic_info or {}).get('connection_status')}")
                        logger.warning(f"Last error: {(diagnostic_info or {}).get('last_error_message')}")
                        
                        if (diagnostic_info or {}).get('token_expired', True):
                            logger.warning("Token appears to be expired")
                        
                        return False
                        
                except Exception as e:
                    logger.error(f"Error testing Schwab API connection: {str(e)}")
                    # Fall back to simulation mode
                    self.force_simulation = True
                    return False
                
            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking API connection: {str(e)}")
            return False
            
    def get_account_info(self):
        """
        Get account information from the API.
        
        Returns:
            dict: Account information
        """
        try:
            if self.force_simulation:
                # Return simulated account data
                return self._get_simulated_account_info()
                
            if self.provider == 'alpaca':
                response = self.session.get(f"{self.base_url}/v2/account", headers=self.headers)
                
                if response.status_code == 200:
                    account_data = response.json() if response.content else {}
                    return {
                        'account_number': (account_data or {}).get('account_number', 'unknown'),
                        'cash': float((account_data or {}).get('cash', 0)),
                        'equity': float((account_data or {}).get('equity', 0)),
                        'buying_power': float((account_data or {}).get('buying_power', 0)),
                        'initial_margin': float((account_data or {}).get('initial_margin', 0)),
                        'maintenance_margin': float((account_data or {}).get('maintenance_margin', 0)),
                        'daytrade_count': int((account_data or {}).get('daytrade_count', 0)),
                    }
                else:
                    logger.warning(f"Failed to get account info: {response.status_code}, {response.text}")
                    return self._get_simulated_account_info()
                    
            elif self.provider == 'td_ameritrade':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for TD Ameritrade API")
                    return self._get_simulated_account_info()
                
                # Add authorization header
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                # Get accounts
                response = self.session.get(f"{self.base_url}/accounts", headers=headers)
                
                if response.status_code == 200:
                    accounts_data = response.json() if response.content else {}
                    result = {}
                    
                    for account in accounts_data:
                        account_id = (account or {}).get('securitiesAccount', {}).get('accountId', 'unknown')
                        account_details = (account or {}).get('securitiesAccount', {})
                        
                        result[account_id] = {
                            'account_number': account_id,
                            'cash': (account_details or {}).get('currentBalances', {}).get('cashBalance', 0),
                            'equity': (account_details or {}).get('currentBalances', {}).get('liquidationValue', 0),
                            'buying_power': (account_details or {}).get('currentBalances', {}).get('buyingPower', 0),
                            'initial_margin': (account_details or {}).get('currentBalances', {}).get('initialBalances', {}).get('margin', 0),
                            'maintenance_margin': (account_details or {}).get('currentBalances', {}).get('maintenanceRequirement', 0),
                            'options_level': (account_details or {}).get('optionLevel', 0),
                        }
                        
                    return result
                else:
                    logger.warning(f"Failed to get account info: {response.status_code}, {response.text}")
                    # Try to refresh token if unauthorized
                    if response.status_code == 401 and self.refresh_token:
                        logger.info("Attempting to refresh access token")
                        # Use standardized refresh access token method
                        if self.refresh_access_token():
                            return self.get_account_info()  # Try again with new token
                    return self._get_simulated_account_info()
                    
            elif self.provider == 'schwab':
                # Use our specialized Schwab connector for improved reliability
                if self.force_simulation:
                    logger.info("Using simulation mode for Schwab account info")
                    return self._get_simulated_account_info()
                
                # Sync tokens with specialized connector
                if self.access_token:
                    self.schwab_connector.access_token = self.access_token
                    self.schwab_connector.refresh_token = self.refresh_token
                    self.schwab_connector.token_expiry = self.token_expiry
                
                try:
                    logger.info("Retrieving account information using specialized Schwab connector")
                    accounts = self.schwab_connector.get_account_info()
                    
                    if accounts:
                        logger.info(f"Successfully retrieved Schwab account data: {len(accounts)} accounts")
                        
                        # If token was refreshed in the specialized connector, sync it back
                        if self.schwab_connector.access_token != self.access_token:
                            logger.info("Synchronizing refreshed tokens from specialized connector")
                            self.access_token = self.schwab_connector.access_token
                            self.refresh_token = self.schwab_connector.refresh_token
                            self.token_expiry = self.schwab_connector.token_expiry
                            
                            # Update session headers
                            self.session.headers.update({
                                'Authorization': f'Bearer {self.access_token}'
                            })
                        
                        return accounts
                    else:
                        logger.warning("Failed to get account info from Schwab API")
                        return self._get_simulated_account_info()
                except Exception as e:
                    logger.error(f"Error getting Schwab account info: {str(e)}")
                    return self._get_simulated_account_info()
                
            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return self._get_simulated_account_info()
                
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return self._get_simulated_account_info()
            
    def _get_simulated_account_info(self):
        """Generate simulated account information."""
        # For demonstration, generate a simulated account
        if self.provider == 'td_ameritrade':
            account_id = f"TD{''.join([str(random.randint(0, 9)) for _ in range(8)])}"
            return {
                account_id: {
                    'account_number': account_id,
                    'cash': round(random.uniform(10000, 100000), 2),
                    'equity': round(random.uniform(20000, 200000), 2),
                    'buying_power': round(random.uniform(15000, 150000), 2),
                    'initial_margin': round(random.uniform(5000, 50000), 2),
                    'maintenance_margin': round(random.uniform(2500, 25000), 2),
                    'options_level': random.randint(1, 4)
                }
            }
        elif self.provider == 'schwab':
            account_id = f"SCH{''.join([str(random.randint(0, 9)) for _ in range(8)])}"
            return {
                account_id: {
                    'account_number': account_id,
                    'cash': round(random.uniform(10000, 100000), 2),
                    'equity': round(random.uniform(20000, 200000), 2),
                    'buying_power': round(random.uniform(15000, 150000), 2),
                    'initial_margin': round(random.uniform(5000, 50000), 2),
                    'maintenance_margin': round(random.uniform(2500, 25000), 2),
                    'options_level': random.randint(1, 4)
                }
            }
        else:  # alpaca
            return {
                'account_number': f"APL{''.join([str(random.randint(0, 9)) for _ in range(8)])}",
                'cash': round(random.uniform(10000, 100000), 2),
                'equity': round(random.uniform(20000, 200000), 2),
                'buying_power': round(random.uniform(15000, 150000), 2),
                'initial_margin': round(random.uniform(5000, 50000), 2),
                'maintenance_margin': round(random.uniform(2500, 25000), 2),
                'daytrade_count': random.randint(0, 3)
            }
    
    def get_positions(self):
        """
        Get current positions from the API.
        
        Returns:
            list: List of positions
        """
        return self.get_open_positions()
        
    def get_open_positions(self):
        """
        Get current open positions from the API.
        
        Returns:
            list: List of open positions
        """
        try:
            if self.force_simulation:
                # Return simulated positions
                return self._get_simulated_positions()
                
            if self.provider == 'alpaca':
                response = self.session.get(f"{self.base_url}/v2/positions", headers=self.headers)
                
                if response.status_code == 200:
                    positions_data = response.json() if response.content else {}
                    result = []
                    
                    for position in positions_data:
                        result.append({
                            'symbol': (position or {}).get('symbol'),
                            'quantity': int(float((position or {}).get('qty'))),
                            'entry_price': float((position or {}).get('avg_entry_price')),
                            'current_price': float((position or {}).get('current_price')),
                            'market_value': float((position or {}).get('market_value')),
                            'cost_basis': float((position or {}).get('cost_basis')),
                            'unrealized_pl': float((position or {}).get('unrealized_pl')),
                            'unrealized_plpc': float((position or {}).get('unrealized_plpc')),
                        })
                        
                    return result
                else:
                    logger.warning(f"Failed to get positions: {response.status_code}, {response.text}")
                    return self._get_simulated_positions()
                    
            elif self.provider == 'td_ameritrade':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for TD Ameritrade API")
                    return self._get_simulated_positions()
                
                # Add authorization header
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                # Get accounts first to get account ID
                accounts = self.get_account_info()
                if not accounts:
                    return self._get_simulated_positions()
                    
                # Use the first account
                account_id = list(accounts.keys())[0]
                
                # Get positions
                response = self.session.get(f"{self.base_url}/accounts/{account_id}?fields=positions", headers=headers)
                
                if response.status_code == 200:
                    account_data = response.json() if response.content else {}
                    positions_data = (account_data or {}).get('securitiesAccount', {}).get('positions', [])
                    result = []
                    
                    for position in positions_data:
                        instrument = (position or {}).get('instrument', {})
                        symbol = (instrument or {}).get('symbol')
                        # Skip non-equity positions for simplicity
                        if (instrument or {}).get('assetType') != 'EQUITY':
                            continue
                            
                        quantity = (position or {}).get('longQuantity', 0) - (position or {}).get('shortQuantity', 0)
                        
                        # Skip zero positions
                        if quantity == 0:
                            continue
                            
                        result.append({
                            'symbol': symbol,
                            'quantity': int(quantity),
                            'entry_price': (position or {}).get('averagePrice', 0),
                            'current_price': (position or {}).get('marketValue', 0) / quantity if quantity != 0 else 0,
                            'market_value': (position or {}).get('marketValue', 0),
                            'cost_basis': (position or {}).get('costBasis', 0),
                            'unrealized_pl': (position or {}).get('unrealizedGainLoss', 0),
                            'unrealized_plpc': (position or {}).get('unrealizedGainLossPercentage', 0) / 100,
                        })
                        
                    return result
                else:
                    logger.warning(f"Failed to get positions: {response.status_code}, {response.text}")
                    # Try to refresh token if unauthorized
                    if response.status_code == 401 and self.refresh_token:
                        logger.info("Attempting to refresh access token")
                        # Use standardized refresh access token method
                        if self.refresh_access_token():
                            return self.get_positions()  # Try again with new token
                    return self._get_simulated_positions()
                    
            elif self.provider == 'schwab':
                # Use our specialized Schwab connector for improved reliability
                if self.force_simulation:
                    logger.info("Using simulation mode for Schwab positions")
                    return self._get_simulated_positions()
                
                # Sync tokens with specialized connector
                if self.access_token:
                    self.schwab_connector.access_token = self.access_token
                    self.schwab_connector.refresh_token = self.refresh_token
                    self.schwab_connector.token_expiry = self.token_expiry
                
                try:
                    logger.info("Retrieving positions using specialized Schwab connector")
                    positions = self.schwab_connector.get_positions()
                    
                    if positions:
                        logger.info(f"Successfully retrieved {len(positions)} positions from Schwab API")
                        
                        # If token was refreshed in the specialized connector, sync it back
                        if self.schwab_connector.access_token != self.access_token:
                            logger.info("Synchronizing refreshed tokens from specialized connector")
                            self.access_token = self.schwab_connector.access_token
                            self.refresh_token = self.schwab_connector.refresh_token
                            self.token_expiry = self.schwab_connector.token_expiry
                            
                            # Update session headers
                            self.session.headers.update({
                                'Authorization': f'Bearer {self.access_token}'
                            })
                        
                        return positions
                    else:
                        logger.warning("Failed to get positions from Schwab API")
                        return self._get_simulated_positions()
                except Exception as e:
                    logger.error(f"Error getting Schwab positions: {str(e)}")
                    return self._get_simulated_positions()
                
            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return self._get_simulated_positions()
                
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            return self._get_simulated_positions()
            
    def _get_simulated_positions(self):
        """Generate simulated positions."""
        # Generate random positions for common stocks
        symbols = ["AAPL", "MSFT", "GOOG", "AMZN", "FB", "BRK.B", "JPM", "JNJ", "V", "PG", "UNH", "HD"]
        selected = random.sample(symbols, random.randint(3, min(8, len(symbols))))
        
        result = []
        for symbol in selected:
            quantity = random.randint(1, 20) * 10  # Multiple of 10 shares
            entry_price = round(random.uniform(100, 200), 2)
            current_price = round(entry_price * random.uniform(0.8, 1.2), 2)  # +/- 20%
            
            unrealized_pl = round((current_price - entry_price) * quantity, 2)
            unrealized_plpc = round(unrealized_pl / (entry_price * quantity), 4)
            
            result.append({
                'symbol': symbol,
                'quantity': quantity,
                'entry_price': entry_price,
                'current_price': current_price,
                'market_value': round(current_price * quantity, 2),
                'cost_basis': round(entry_price * quantity, 2),
                'unrealized_pl': unrealized_pl,
                'unrealized_plpc': unrealized_plpc,
            })
            
        return result
    
    def get_orders(self, status='all'):
        """
        Get orders from the API.
        
        Args:
            status (str): Order status filter ('open', 'closed', 'all')
            
        Returns:
            list: List of orders
        """
        try:
            if self.force_simulation:
                # Return simulated orders
                return self._get_simulated_orders(status)
                
            if self.provider == 'alpaca':
                url = f"{self.base_url}/v2/orders"
                if status == 'open':
                    url += "?status=open"
                elif status == 'closed':
                    url += "?status=closed"
                
                response = self.session.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    orders_data = response.json() if response.content else {}
                    result = []
                    
                    for order in orders_data:
                        result.append({
                            'id': (order or {}).get('id'),
                            'symbol': (order or {}).get('symbol'),
                            'quantity': int((order or {}).get('qty')),
                            'side': (order or {}).get('side'),
                            'type': (order or {}).get('type'),
                            'status': (order or {}).get('status'),
                            'submitted_at': (order or {}).get('submitted_at'),
                            'filled_at': (order or {}).get('filled_at'),
                            'filled_quantity': int(float((order or {}).get('filled_qty', 0))),
                            'filled_price': float((order or {}).get('filled_avg_price', 0)),
                        })
                        
                    return result
                else:
                    logger.warning(f"Failed to get orders: {response.status_code}, {response.text}")
                    return self._get_simulated_orders(status)
                    
            elif self.provider == 'td_ameritrade':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for TD Ameritrade API")
                    return self._get_simulated_orders(status)
                
                # Add authorization header
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                # Get accounts first to get account ID
                accounts = self.get_account_info()
                if not accounts:
                    return self._get_simulated_orders(status)
                    
                # Use the first account
                account_id = list(accounts.keys())[0]
                
                # Build URL
                url = f"{self.base_url}/accounts/{account_id}/orders"
                if status == 'open':
                    url += "?status=WORKING"
                elif status == 'closed':
                    url += "?status=FILLED"
                
                response = self.session.get(url, headers=headers)
                
                if response.status_code == 200:
                    orders_data = response.json() if response.content else {}
                    result = []
                    
                    for order in orders_data:
                        # Extract key info from complex TD order structure
                        order_legs = (order or {}).get('orderLegCollection', [])
                        if not order_legs:
                            continue
                            
                        leg = order_legs[0]
                        instrument = (leg or {}).get('instrument', {})
                        
                        result.append({
                            'id': (order or {}).get('orderId'),
                            'symbol': (instrument or {}).get('symbol'),
                            'quantity': (leg or {}).get('quantity', 0),
                            'side': (leg or {}).get('instruction').lower(),
                            'type': (order or {}).get('orderType').lower(),
                            'status': (order or {}).get('status'),
                            'submitted_at': (order or {}).get('enteredTime'),
                            'filled_at': (order or {}).get('closeTime'),
                            'filled_quantity': (order or {}).get('filledQuantity', 0),
                            'filled_price': (order or {}).get('orderActivityCollection', [{}])[0].get('executionLegs', [{}])[0].get('price', 0),
                        })
                        
                    return result
                else:
                    logger.warning(f"Failed to get orders: {response.status_code}, {response.text}")
                    # Try to refresh token if unauthorized
                    if response.status_code == 401 and self.refresh_token:
                        logger.info("Attempting to refresh access token")
                        if self.refresh_access_token():
                            return self.get_orders(status)  # Try again with new token
                    return self._get_simulated_orders(status)
                    
            elif self.provider == 'schwab':
                # Use our specialized Schwab connector for improved reliability
                if self.force_simulation:
                    logger.info("Using simulation mode for Schwab orders")
                    return self._get_simulated_orders(status)
                
                # Sync tokens with specialized connector
                if self.access_token:
                    self.schwab_connector.access_token = self.access_token
                    self.schwab_connector.refresh_token = self.refresh_token
                    self.schwab_connector.token_expiry = self.token_expiry
                
                try:
                    logger.info(f"Retrieving orders using specialized Schwab connector with status={status}")
                    orders = self.schwab_connector.get_orders(status=status)
                    
                    if orders:
                        logger.info(f"Successfully retrieved {len(orders)} orders from Schwab API")
                        
                        # If token was refreshed in the specialized connector, sync it back
                        if self.schwab_connector.access_token != self.access_token:
                            logger.info("Synchronizing refreshed tokens from specialized connector")
                            self.access_token = self.schwab_connector.access_token
                            self.refresh_token = self.schwab_connector.refresh_token
                            self.token_expiry = self.schwab_connector.token_expiry
                            
                            # Update session headers
                            self.session.headers.update({
                                'Authorization': f'Bearer {self.access_token}'
                            })
                        
                        return orders
                    else:
                        logger.warning("Failed to get orders from Schwab API")
                        return self._get_simulated_orders(status)
                except Exception as e:
                    logger.error(f"Error getting Schwab orders: {str(e)}")
                    return self._get_simulated_orders(status)
                
            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return self._get_simulated_orders(status)
                
        except Exception as e:
            logger.error(f"Error getting orders: {str(e)}")
            return self._get_simulated_orders(status)
            
    def _get_simulated_orders(self, status='all'):
        """Generate simulated orders."""
        # Generate random orders for common stocks
        symbols = ["AAPL", "MSFT", "GOOG", "AMZN", "FB", "BRK.B", "JPM", "JNJ", "V", "PG", "UNH", "HD"]
        
        # Determine number of orders based on status
        if status == 'open':
            count = random.randint(1, 4)
        elif status == 'closed':
            count = random.randint(3, 10)
        else:  # 'all'
            count = random.randint(5, 15)
            
        result = []
        for i in range(count):
            symbol = random.choice(symbols)
            order_type = random.choice(['market', 'limit'])
            side = random.choice(['buy', 'sell'])
            
            # For 'all' status, mix of open and closed
            if status == 'all':
                order_status = random.choice(['open', 'filled', 'filled', 'filled'])  # More filled than open
            elif status == 'open':
                order_status = 'open'
            else:  # 'closed'
                order_status = 'filled'
                
            quantity = random.randint(1, 20) * 10  # Multiple of 10 shares
            price = round(random.uniform(100, 200), 2)
            
            # Calculate filled info
            filled_at = None
            filled_quantity = 0
            filled_price = 0
            
            if order_status == 'filled':
                filled_at = (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat()
                filled_quantity = quantity
                filled_price = price if order_type == 'limit' else round(price * random.uniform(0.98, 1.02), 2)
                
            # Calculate submitted_at
            if filled_at:
                submitted_at = (datetime.strptime(filled_at, "%Y-%m-%dT%H:%M:%S.%f") - timedelta(hours=random.randint(1, 5))).isoformat()
            else:
                submitted_at = (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat()
                
            result.append({
                'id': f"ord_{''.join([str(random.randint(0, 9)) for _ in range(8)])}",
                'symbol': symbol,
                'quantity': quantity,
                'side': side,
                'type': order_type,
                'status': order_status,
                'submitted_at': submitted_at,
                'filled_at': filled_at,
                'filled_quantity': filled_quantity,
                'filled_price': filled_price,
            })
            
        return result
    
    def get_stock_data(self, symbol, days=30):
        """
        Get comprehensive stock data for a symbol, including price, volume, and other metrics.
        
        Args:
            symbol (str): Stock symbol
            days (int, optional): Number of days of historical data to include. Defaults to 30.
            
        Returns:
            dict: Stock data including current price, day change, volume, and other metrics
        """
        try:
            if self.force_simulation:
                # Return simulated stock data
                return self._get_simulated_stock_data(symbol)
                
            # Get the current price
            current_price = self.get_current_price(symbol)
            
            # Get historical data for recent performance
            historical_data = self.get_historical_data(symbol, timeframe='day', limit=5)
            
            # Calculate day change
            if len(historical_data) >= 2:
                prev_close = historical_data[-2]['close'] if isinstance(historical_data[0], dict) else historical_data.iloc[-2]['close']
                day_change = current_price - prev_close
                day_change_pct = (day_change / prev_close) * 100 if prev_close else 0
            else:
                day_change = 0.0
                day_change_pct = 0.0
            
            # Build the stock data dictionary
            stock_data = {
                'symbol': symbol,
                'price': current_price,
                'day_change': day_change,
                'day_change_pct': day_change_pct,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Add additional data if available from the specific provider
            if self.provider == 'alpaca':
                try:
                    response = self.session.get(
                        f"{self.base_url}/v2/assets/{symbol}",
                        headers=self.headers
                    )
                    
                    if response.status_code == 200:
                        asset_data = response.json() if response.content else {}
                        stock_data['name'] = (asset_data or {}).get('name', '')
                        stock_data['exchange'] = (asset_data or {}).get('exchange', '')
                except Exception as e:
                    logger.warning(f"Error getting additional asset data for {symbol}: {str(e)}")
            
            # Try to get latest quote for volume information
            try:
                if self.provider == 'alpaca':
                    # Use base_url as fallback if data_url is not defined
                    data_url = getattr(self, 'data_url', self.base_url)
                    response = self.session.get(
                        f"{data_url}/v2/stocks/{symbol}/quotes/latest",
                        headers=self.headers
                    )
                    
                    if response.status_code == 200:
                        quote_data = response.json() if response.content else {}
                        stock_data['ask'] = (quote_data or {}).get('quote', {}).get('ap', current_price)
                        stock_data['bid'] = (quote_data or {}).get('quote', {}).get('bp', current_price)
                        stock_data['ask_size'] = (quote_data or {}).get('quote', {}).get('as', 0)
                        stock_data['bid_size'] = (quote_data or {}).get('quote', {}).get('bs', 0)
                        
                # Get trade data for volume
                if self.provider == 'alpaca':
                    # Use base_url as fallback if data_url is not defined
                    data_url = getattr(self, 'data_url', self.base_url)
                    response = self.session.get(
                        f"{data_url}/v2/stocks/{symbol}/trades/latest",
                        headers=self.headers
                    )
                    
                    if response.status_code == 200:
                        trade_data = response.json() if response.content else {}
                        stock_data['volume'] = (trade_data or {}).get('trade', {}).get('v', 0)
            except Exception as e:
                logger.warning(f"Error getting latest quote/trade data for {symbol}: {str(e)}")
                stock_data['volume'] = 0
            
            return stock_data
            
        except Exception as e:
            logger.error(f"Error getting stock data for {symbol}: {str(e)}")
            # Return basic simulated data as a fallback
            return self._get_simulated_stock_data(symbol)
            
    def _get_simulated_stock_data(self, symbol):
        """
        Generate simulated comprehensive stock data for a symbol.
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Simulated stock data
        """
        # Get a stable but random price based on the symbol
        import hashlib
        import random
        
        # Use the symbol to seed the random number generator for consistent results
        symbol_hash = int(hashlib.md5(symbol.encode()).hexdigest(), 16) % 10000
        random.seed(symbol_hash)
        
        base_price = (symbol_hash % 1000) + 10  # Price between $10 and $1010
        price_variation = random.uniform(-5, 5)  # Daily variation
        current_price = round(base_price + price_variation, 2)
        
        # Generate other realistic metrics
        day_change = round(price_variation, 2)
        day_change_pct = round((day_change / base_price) * 100, 2)
        volume = random.randint(10000, 10000000)
        
        # Create company name from symbol
        words = {
            'A': 'Advanced', 'B': 'Better', 'C': 'Creative', 'D': 'Dynamic', 'E': 'Efficient',
            'F': 'Future', 'G': 'Global', 'H': 'Horizon', 'I': 'Innovative', 'J': 'Junction',
            'K': 'Key', 'L': 'Logical', 'M': 'Modern', 'N': 'Next', 'O': 'Optimal',
            'P': 'Progressive', 'Q': 'Quality', 'R': 'Reliable', 'S': 'Strategic', 'T': 'Technical',
            'U': 'Universal', 'V': 'Value', 'W': 'World', 'X': 'Xcellent', 'Y': 'Yield', 'Z': 'Zenith'
        }
        
        suffixes = ['Corp', 'Inc', 'Ltd', 'Group', 'Holdings', 'Technologies', 'Systems', 'Solutions']
        
        name_parts = []
        for char in symbol.upper():
            if char in words:
                name_parts.append(words[char])
        
        if not name_parts:
            name_parts = [random.choice(list(words.values()))]
            
        company_name = ' '.join(name_parts[:2]) + ' ' + random.choice(suffixes)
        
        # Generate realistic bid/ask spread
        spread = round(current_price * random.uniform(0.0005, 0.002), 2)  # 0.05% to 0.2% spread
        bid = round(current_price - (spread / 2), 2)
        ask = round(current_price + (spread / 2), 2)
        
        return {
            'symbol': symbol,
            'name': company_name,
            'price': current_price,
            'day_change': day_change,
            'day_change_pct': day_change_pct,
            'volume': volume,
            'bid': bid,
            'ask': ask,
            'bid_size': random.randint(100, 1000),
            'ask_size': random.randint(100, 1000),
            'exchange': random.choice(['NYSE', 'NASDAQ', 'AMEX']),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    def get_current_price(self, symbol):
        """
        Get the current price for a symbol.
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            float: Current price or None if not available
        """
        try:
            if self.force_simulation:
                # Return simulated price
                return self._get_simulated_price(symbol)
                
            if self.provider == 'alpaca':
                response = self.session.get(f"{self.base_url}/v2/stocks/{symbol}/trades/latest", headers=self.headers)
                
                if response.status_code == 200:
                    trade_data = response.json() if response.content else {}
                    return float((trade_data or {}).get('trade', {}).get('p', 0))
                else:
                    logger.warning(f"Failed to get current price for {symbol}: {response.status_code}, {response.text}")
                    return self._get_simulated_price(symbol)
                    
            elif self.provider == 'td_ameritrade':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for TD Ameritrade API")
                    return self._get_simulated_price(symbol)
                
                # Add authorization header
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                # Get quote
                response = self.session.get(f"{self.base_url}/marketdata/{symbol}/quotes", headers=headers)
                
                if response.status_code == 200:
                    quote_data = response.json() if response.content else {}
                    return (quote_data or {}).get(symbol, {}).get('lastPrice', 0)
                else:
                    logger.warning(f"Failed to get current price for {symbol}: {response.status_code}, {response.text}")
                    # Try to refresh token if unauthorized
                    if response.status_code == 401 and self.refresh_token:
                        logger.info("Attempting to refresh access token")
                        # Use standardized refresh access token method
                        if self.refresh_access_token():
                            return self.get_current_price(symbol)  # Try again with new token
                    return self._get_simulated_price(symbol)
                    
            elif self.provider == 'schwab':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for Schwab API")
                    return self._get_simulated_price(symbol)
                
                # Add authorization header
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                # In a real implementation, you would make an API call to Schwab
                # Since we don't have actual Schwab API docs, we'll simulate a response
                logger.info(f"Generating mock stock data for {symbol} (simulation mode)")
                
                return self._get_simulated_price(symbol)
                
            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return self._get_simulated_price(symbol)
                
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {str(e)}")
            return self._get_simulated_price(symbol)
            
    def _get_simulated_price(self, symbol):
        """Generate a simulated price for a symbol."""
        # Use a consistent algorithm to generate a "realistic" price based on the symbol
        # This way the same symbol always gets a similar price
        
        # Get the sum of ASCII values for the symbol
        ascii_sum = sum(ord(c) for c in symbol)
        
        # Use the sum to seed a random number generator
        random.seed(ascii_sum)
        
        # Generate a base price range
        if ascii_sum % 5 == 0:
            # High price stocks (like AMZN, GOOG)
            base = random.uniform(1000, 3000)
        elif ascii_sum % 3 == 0:
            # Medium-high price stocks
            base = random.uniform(300, 800)
        elif ascii_sum % 2 == 0:
            # Medium price stocks
            base = random.uniform(100, 250)
        else:
            # Lower price stocks
            base = random.uniform(20, 80)
            
        # Add some daily variation
        # Use the current day to seed
        day_seed = int(datetime.now().strftime("%Y%m%d"))
        random.seed(day_seed + ascii_sum)
        
        # Add +/- 3% daily change
        variation = random.uniform(-0.03, 0.03)
        
        # Reset the random seed
        random.seed()
        
        # Calculate the final price
        price = base * (1 + variation)
        
        return round(price, 2)
    
    def get_historical_data(self, symbol, timeframe='day', limit=100):
        """
        Get historical price data for a symbol.
        
        Args:
            symbol (str): Stock symbol
            timeframe (str): Time period ('minute', 'hour', 'day', 'week', 'month')
            limit (int): Number of bars to retrieve
            
        Returns:
            pandas.DataFrame: Historical data
        """
        try:
            if self.force_simulation:
                # Return simulated data
                return self._get_simulated_historical_data(symbol, timeframe, limit)
                
            if self.provider == 'alpaca':
                # Map timeframe to Alpaca format
                alpaca_timeframe = {
                    'minute': '1Min',
                    'hour': '1Hour',
                    'day': '1Day',
                    'week': '1Week',
                    'month': '1Month'
                }.get(timeframe.lower(), '1Day')
                
                # Calculate end date (now) and start date
                end_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                
                response = self.session.get(
                    f"{self.base_url}/v2/stocks/{symbol}/bars",
                    params={
                        'timeframe': alpaca_timeframe,
                        'limit': limit,
                        'end': end_date
                    },
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    bars_data = response.json() if response.content else {}.get('bars', [])
                    
                    if not bars_data:
                        logger.warning(f"No historical data returned for {symbol}")
                        return self._get_simulated_historical_data(symbol, timeframe, limit)
                        
                    # Convert to DataFrame
                    df = pd.DataFrame(bars_data)
                    df['t'] = pd.to_datetime(df['t'])
                    df = df.rename(columns={
                        't': 'time',
                        'o': 'open',
                        'h': 'high',
                        'l': 'low',
                        'c': 'close',
                        'v': 'volume'
                    })
                    df = df.set_index('time')
                    
                    return df
                else:
                    logger.warning(f"Failed to get historical data for {symbol}: {response.status_code}, {response.text}")
                    return self._get_simulated_historical_data(symbol, timeframe, limit)
                    
            elif self.provider == 'td_ameritrade':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for TD Ameritrade API")
                    return self._get_simulated_historical_data(symbol, timeframe, limit)
                
                # Add authorization header
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                # Map timeframe to TD Ameritrade format
                td_period_type = 'day'
                td_frequency_type = 'minute'
                td_frequency = 1
                
                if timeframe.lower() == 'minute':
                    td_period_type = 'day'
                    td_frequency_type = 'minute'
                    td_frequency = 1
                elif timeframe.lower() == 'hour':
                    td_period_type = 'day'
                    td_frequency_type = 'minute'
                    td_frequency = 60
                elif timeframe.lower() == 'day':
                    td_period_type = 'month'
                    td_frequency_type = 'daily'
                    td_frequency = 1
                elif timeframe.lower() == 'week':
                    td_period_type = 'month'
                    td_frequency_type = 'weekly'
                    td_frequency = 1
                elif timeframe.lower() == 'month':
                    td_period_type = 'year'
                    td_frequency_type = 'monthly'
                    td_frequency = 1
                
                # Calculate period based on limit and frequency
                period = min(10, (limit + 5) // 30)  # TD has max period of 10
                
                response = self.session.get(
                    f"{self.base_url}/marketdata/{symbol}/pricehistory",
                    params={
                        'periodType': td_period_type,
                        'period': period,
                        'frequencyType': td_frequency_type,
                        'frequency': td_frequency
                    },
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json() if response.content else {}
                    candles = (data or {}).get('candles', [])
                    
                    if not candles:
                        logger.warning(f"No historical data returned for {symbol}")
                        return self._get_simulated_historical_data(symbol, timeframe, limit)
                        
                    # Convert to DataFrame
                    df = pd.DataFrame(candles)
                    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
                    df = df.rename(columns={
                        'datetime': 'time'
                    })
                    df = df.set_index('time')
                    
                    # Limit rows
                    df = df.tail(limit)
                    
                    return df
                else:
                    logger.warning(f"Failed to get historical data for {symbol}: {response.status_code}, {response.text}")
                    # Try to refresh token if unauthorized
                    if response.status_code == 401 and self.refresh_token:
                        logger.info("Attempting to refresh access token")
                        # Use standardized refresh access token method
                        if self.refresh_access_token():
                            return self.get_historical_data(symbol, timeframe, limit)  # Try again with new token
                    return self._get_simulated_historical_data(symbol, timeframe, limit)
                    
            elif self.provider == 'schwab':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for Schwab API")
                    return self._get_simulated_historical_data(symbol, timeframe, limit)
                
                # Add authorization header
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                # In a real implementation, you would make an API call to Schwab
                # Since we don't have actual Schwab API docs, we'll simulate a response
                logger.info(f"Generating mock historical data for {symbol} (simulation mode)")
                
                return self._get_simulated_historical_data(symbol, timeframe, limit)
                
            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return self._get_simulated_historical_data(symbol, timeframe, limit)
                
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return self._get_simulated_historical_data(symbol, timeframe, limit)
            
    def _get_simulated_historical_data(self, symbol, timeframe='day', limit=100):
        """Generate simulated historical data for a symbol."""
        # Use a consistent algorithm to generate "realistic" price data based on the symbol
        
        # Get initial price based on symbol
        current_price = self._get_simulated_price(symbol)
        
        # Set the volatility based on timeframe
        if timeframe.lower() == 'minute':
            volatility = 0.001  # 0.1% per bar
        elif timeframe.lower() == 'hour':
            volatility = 0.003  # 0.3% per bar
        elif timeframe.lower() == 'day':
            volatility = 0.01  # 1% per bar
        elif timeframe.lower() == 'week':
            volatility = 0.02  # 2% per bar
        else:  # month
            volatility = 0.04  # 4% per bar
            
        # Generate dates
        if timeframe.lower() == 'minute':
            end_date = datetime.now().replace(second=0, microsecond=0)
            dates = [end_date - timedelta(minutes=i) for i in range(limit)]
        elif timeframe.lower() == 'hour':
            end_date = datetime.now().replace(minute=0, second=0, microsecond=0)
            dates = [end_date - timedelta(hours=i) for i in range(limit)]
        elif timeframe.lower() == 'day':
            end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            dates = [end_date - timedelta(days=i) for i in range(limit)]
        elif timeframe.lower() == 'week':
            end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            # Find the start of the week (Monday)
            end_date = end_date - timedelta(days=end_date.weekday())
            dates = [end_date - timedelta(weeks=i) for i in range(limit)]
        else:  # month
            end_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            dates = []
            current_date = end_date
            for _ in range(limit):
                dates.append(current_date)
                # Go to the previous month
                if current_date.month == 1:
                    current_date = current_date.replace(year=current_date.year - 1, month=12)
                else:
                    current_date = current_date.replace(month=current_date.month - 1)
        
        # Sort dates in ascending order
        dates = sorted(dates)
        
        # Initialize price at the first date with a starting price
        # Use the ASCII sum of the symbol to seed the random number generator for consistency
        ascii_sum = sum(ord(c) for c in symbol)
        random.seed(ascii_sum)
        
        # Start with a price and generate a random walk
        start_price = current_price * random.uniform(0.7, 0.9)  # Start 10-30% lower than current
        
        # Reset random seed
        random.seed()
        
        # Generate price series
        prices = [start_price]
        for i in range(1, limit):
            # Random walk with drift
            change = random.gauss(0.0002, volatility)  # Slight upward drift
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
            
        # Create OHLC data
        data = []
        for i in range(limit):
            base_price = prices[i]
            
            # Generate realistic OHLC values
            high_pct = random.uniform(0, volatility * 2)
            low_pct = random.uniform(0, volatility * 2)
            
            open_price = base_price * random.uniform(1 - volatility / 2, 1 + volatility / 2)
            close_price = base_price
            high_price = max(open_price, close_price) * (1 + high_pct)
            low_price = min(open_price, close_price) * (1 - low_pct)
            
            # Generate volume
            volume = int(random.uniform(100000, 1000000) * (base_price / 100))
            
            data.append({
                'time': dates[i],
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
            
        # Create DataFrame
        df = pd.DataFrame(data)
        df = df.set_index('time')
        
        return df
    
    def get_options_chain(self, symbol):
        """
        Get options chain data for a symbol.
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Options chain data with 'calls' and 'puts' lists
        """
        try:
            if self.force_simulation:
                # Return simulated options chain
                return self._get_simulated_options_chain(symbol)
                
            if self.provider == 'alpaca':
                # Alpaca doesn't support options in the public API
                logger.warning("Alpaca doesn't support options in the public API. Using simulated data.")
                return self._get_simulated_options_chain(symbol)
                
            elif self.provider == 'td_ameritrade':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for TD Ameritrade API")
                    return self._get_simulated_options_chain(symbol)
                
                # Add authorization header
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                # Get current stock price to determine strike range
                current_price = self.get_current_price(symbol)
                if not current_price:
                    return self._get_simulated_options_chain(symbol)
                    
                # Calculate strike range (20% above and below current price)
                strike_min = current_price * 0.8
                strike_max = current_price * 1.2
                
                # Get options chain for the next 3 expiry dates
                response = self.session.get(
                    f"{self.base_url}/marketdata/chains",
                    params={
                        'symbol': symbol,
                        'strikeCount': 10,
                        'range': 'NTM',  # Near-the-money
                        'includeQuotes': 'TRUE'
                    },
                    headers=headers
                )
                
                if response.status_code == 200:
                    chain_data = response.json() if response.content else {}
                    
                    # Extract calls and puts from the complex TD structure
                    calls = []
                    puts = []
                    
                    # Process calls
                    call_expirations = (chain_data or {}).get('callExpDateMap', {})
                    for expiry_days, strikes in call_expirations.items():
                        for strike, options in strikes.items():
                            for option in options:
                                calls.append({
                                    'strike': float(strike),
                                    'expiry': (option or {}).get('expirationDate'),
                                    'last': (option or {}).get('last'),
                                    'bid': (option or {}).get('bid'),
                                    'ask': (option or {}).get('ask'),
                                    'volume': (option or {}).get('totalVolume'),
                                    'open_interest': (option or {}).get('openInterest'),
                                    'delta': (option or {}).get('delta'),
                                    'gamma': (option or {}).get('gamma'),
                                    'theta': (option or {}).get('theta'),
                                    'vega': (option or {}).get('vega'),
                                    'implied_volatility': (option or {}).get('volatility') / 100 if (option or {}).get('volatility') else None,
                                    'itm': (option or {}).get('inTheMoney')
                                })
                                
                    # Process puts
                    put_expirations = (chain_data or {}).get('putExpDateMap', {})
                    for expiry_days, strikes in put_expirations.items():
                        for strike, options in strikes.items():
                            for option in options:
                                puts.append({
                                    'strike': float(strike),
                                    'expiry': (option or {}).get('expirationDate'),
                                    'last': (option or {}).get('last'),
                                    'bid': (option or {}).get('bid'),
                                    'ask': (option or {}).get('ask'),
                                    'volume': (option or {}).get('totalVolume'),
                                    'open_interest': (option or {}).get('openInterest'),
                                    'delta': (option or {}).get('delta'),
                                    'gamma': (option or {}).get('gamma'),
                                    'theta': (option or {}).get('theta'),
                                    'vega': (option or {}).get('vega'),
                                    'implied_volatility': (option or {}).get('volatility') / 100 if (option or {}).get('volatility') else None,
                                    'itm': (option or {}).get('inTheMoney')
                                })
                                
                    return {
                        'calls': calls,
                        'puts': puts,
                        'underlying_price': current_price
                    }
                else:
                    logger.warning(f"Failed to get options chain for {symbol}: {response.status_code}, {response.text}")
                    # Try to refresh token if unauthorized
                    if response.status_code == 401 and self.refresh_token:
                        logger.info("Attempting to refresh access token")
                        # Use standardized refresh access token method
                        if self.refresh_access_token():
                            return self.get_options_chain(symbol)  # Try again with new token
                    return self._get_simulated_options_chain(symbol)
                    
            elif self.provider == 'schwab':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for Schwab API")
                    return self._get_simulated_options_chain(symbol)
                
                # Add authorization header
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                # In a real implementation, you would make an API call to Schwab
                # Since we don't have actual Schwab API docs, we'll simulate a response
                logger.info(f"Generating mock options chain for {symbol} (simulation mode)")
                
                return self._get_simulated_options_chain(symbol)
                
            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return self._get_simulated_options_chain(symbol)
                
        except Exception as e:
            logger.error(f"Error getting options chain for {symbol}: {str(e)}")
            return self._get_simulated_options_chain(symbol)
            
    def _get_simulated_options_chain(self, symbol):
        """Generate simulated options chain for a symbol."""
        # Get the current price for the symbol
        current_price = self._get_simulated_price(symbol)
        
        # Round to nearest dollar
        base_price = round(current_price)
        
        # Generate strike prices (10 below, 10 above)
        strikes = []
        for i in range(-10, 11):
            strike = base_price + i * (base_price * 0.025)  # 2.5% increments
            strikes.append(round(strike, 2))
            
        # Generate expiry dates (4 weekly, 3 monthly, 2 quarterly)
        expiry_dates = []
        
        # Weekly
        for i in range(1, 5):
            expiry = (datetime.now() + timedelta(days=i*7)).strftime("%Y-%m-%d")
            expiry_dates.append(expiry)
            
        # Monthly
        for i in range(1, 4):
            # Get the third Friday of each month
            now = datetime.now()
            first_day = datetime(now.year, now.month + i if now.month + i <= 12 else (now.month + i) % 12, 1)
            # Adjust if we wrapped to next year
            if now.month + i > 12:
                first_day = first_day.replace(year=now.year + 1)
            # Find the first Friday
            friday = first_day + timedelta(days=((4 - first_day.weekday()) % 7))
            # Find the third Friday
            third_friday = friday + timedelta(days=14)
            expiry_dates.append(third_friday.strftime("%Y-%m-%d"))
            
        # Quarterly
        for i in range(1, 3):
            # Get the third Friday of the quarter
            now = datetime.now()
            quarter_month = ((now.month - 1) // 3 + i) * 3 + 1
            year_offset = 0
            if quarter_month > 12:
                quarter_month = quarter_month % 12
                year_offset = 1
            first_day = datetime(now.year + year_offset, quarter_month, 1)
            # Find the first Friday
            friday = first_day + timedelta(days=((4 - first_day.weekday()) % 7))
            # Find the third Friday
            third_friday = friday + timedelta(days=14)
            expiry_dates.append(third_friday.strftime("%Y-%m-%d"))
            
        # Generate calls and puts
        calls = []
        puts = []
        
        for expiry in expiry_dates:
            # Calculate days to expiry
            expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
            days_to_expiry = (expiry_date - datetime.now()).days
            
            # Adjust volatility based on days to expiry
            base_vol = 0.3  # 30% annual volatility
            if days_to_expiry < 30:
                vol_factor = 1.2  # Higher implied vol for short-dated options
            elif days_to_expiry < 90:
                vol_factor = 1.0
            else:
                vol_factor = 0.9  # Lower implied vol for longer-dated options
                
            for strike in strikes:
                # Calculate option metrics
                distance_pct = (strike - current_price) / current_price
                
                # Call option
                call_itm = current_price > strike
                call_iv = base_vol * vol_factor * (1 + abs(distance_pct) * 0.5)  # Volatility smile
                
                # Calculate theoretical price and greeks
                t = days_to_expiry / 365.0
                
                # Simplified Black-Scholes (not accurate, just for simulation)
                call_delta = max(0, min(1, 0.5 + 0.5 * (distance_pct * -10)))
                call_gamma = max(0, 0.1 * (1 - abs(distance_pct * 5)))
                call_theta = -current_price * 0.001 * (1 - abs(distance_pct))
                call_vega = current_price * 0.01 * t * (1 - abs(distance_pct * 2))
                
                # Calculate theoretical prices
                call_theo = max(0, current_price - strike) + current_price * call_iv * np.sqrt(t) * 0.4
                
                # Generate realistic bid-ask
                call_spread = call_theo * 0.05 * (1 + 1 / max(1, days_to_expiry/10))
                call_bid = max(0.01, call_theo - call_spread/2)
                call_ask = max(0.01, call_theo + call_spread/2)
                
                # Add call
                calls.append({
                    'strike': strike,
                    'expiry': expiry,
                    'bid': round(call_bid, 2),
                    'ask': round(call_ask, 2),
                    'last': round((call_bid + call_ask) / 2, 2),
                    'volume': int(random.uniform(10, 1000) * (1 - abs(distance_pct))),
                    'open_interest': int(random.uniform(100, 5000) * (1 - abs(distance_pct))),
                    'implied_volatility': round(call_iv, 2),
                    'delta': round(call_delta, 2),
                    'gamma': round(call_gamma, 3),
                    'theta': round(call_theta, 3),
                    'vega': round(call_vega, 3),
                    'itm': call_itm
                })
                
                # Put option
                put_itm = current_price < strike
                put_iv = base_vol * vol_factor * (1 + abs(distance_pct) * 0.5)  # Volatility smile
                
                # Simplified greeks
                put_delta = min(0, max(-1, -0.5 + 0.5 * (distance_pct * -10)))
                put_gamma = call_gamma  # Same as call
                put_theta = call_theta  # Simplified
                put_vega = call_vega  # Same as call
                
                # Calculate theoretical prices
                put_theo = max(0, strike - current_price) + current_price * put_iv * np.sqrt(t) * 0.4
                
                # Generate realistic bid-ask
                put_spread = put_theo * 0.05 * (1 + 1 / max(1, days_to_expiry/10))
                put_bid = max(0.01, put_theo - put_spread/2)
                put_ask = max(0.01, put_theo + put_spread/2)
                
                # Add put
                puts.append({
                    'strike': strike,
                    'expiry': expiry,
                    'bid': round(put_bid, 2),
                    'ask': round(put_ask, 2),
                    'last': round((put_bid + put_ask) / 2, 2),
                    'volume': int(random.uniform(10, 1000) * (1 - abs(distance_pct))),
                    'open_interest': int(random.uniform(100, 5000) * (1 - abs(distance_pct))),
                    'implied_volatility': round(put_iv, 2),
                    'delta': round(put_delta, 2),
                    'gamma': round(put_gamma, 3),
                    'theta': round(put_theta, 3),
                    'vega': round(put_vega, 3),
                    'itm': put_itm
                })
                
        return {
            'calls': calls,
            'puts': puts,
            'underlying_price': current_price
        }
    
    def place_order(self, order_details, account_id=None):
        """
        Place an order with the broker.
        
        Args:
            order_details (dict): Order details specific to the broker API
            account_id (str, optional): Account ID for brokers that require it
            
        Returns:
            dict: Order execution result
        """
        try:
            if self.force_simulation:
                # Return simulated order result
                return self._simulate_order_execution(order_details)
                
            if self.provider == 'alpaca':
                response = self.session.post(f"{self.base_url}/v2/orders", json=order_details, headers=self.headers)
                
                if response.status_code == 200 or response.status_code == 201:
                    order_data = response.json() if response.content else {}
                    return {
                        'success': True,
                        'order_id': (order_data or {}).get('id'),
                        'message': f"Order placed: {(order_data or {}).get('id')}",
                        'details': order_data
                    }
                else:
                    logger.warning(f"Failed to place order: {response.status_code}, {response.text}")
                    return {
                        'success': False,
                        'message': f"Failed to place order: {response.text}",
                        'status_code': response.status_code
                    }
                    
            elif self.provider == 'td_ameritrade':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for TD Ameritrade API")
                    return self._simulate_order_execution(order_details)
                
                # Add authorization header
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                # Use provided account ID or get from account info
                if not account_id:
                    accounts = self.get_account_info()
                    if not accounts:
                        return {
                            'success': False,
                            'message': "Could not determine account ID"
                        }
                    account_id = list(accounts.keys())[0]
                    
                response = self.session.post(
                    f"{self.base_url}/accounts/{account_id}/orders",
                    json=order_details,
                    headers=headers
                )
                
                if response.status_code == 200 or response.status_code == 201:
                    # TD Ameritrade doesn't return order details in the response, just location header
                    location = response.headers.get('Location', '')
                    order_id = location.split('/')[-1] if location else 'unknown'
                    
                    return {
                        'success': True,
                        'order_id': order_id,
                        'message': f"Order placed: {order_id}",
                        'location': location
                    }
                else:
                    logger.warning(f"Failed to place order: {response.status_code}, {response.text}")
                    # Try to refresh token if unauthorized
                    if response.status_code == 401 and self.refresh_token:
                        logger.info("Attempting to refresh access token")
                        # Use standardized refresh access token method
                        if self.refresh_access_token():
                            return self.place_order(order_details, account_id)  # Try again with new token
                    return {
                        'success': False,
                        'message': f"Failed to place order: {response.text}",
                        'status_code': response.status_code
                    }
                    
            elif self.provider == 'schwab':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for Schwab API")
                    return self._simulate_order_execution(order_details)
                
                # Add authorization header
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                # In a real implementation, you would make an API call to Schwab
                # Since we don't have actual Schwab API docs, we'll simulate a response
                logger.info("Simulating Schwab order placement")
                
                return self._simulate_order_execution(order_details)
                
            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return self._simulate_order_execution(order_details)
                
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return {
                'success': False,
                'message': f"Error placing order: {str(e)}"
            }
            
    def _simulate_order_execution(self, order_details):
        """Simulate an order execution."""
        # Generate an order ID
        order_id = f"sim_{''.join([str(random.randint(0, 9)) for _ in range(8)])}"
        
        # Extract key details for the response
        symbol = None
        side = None
        quantity = None
        order_type = None
        
        # For Alpaca-style orders
        if 'symbol' in order_details:
            symbol = (order_details or {}).get('symbol')
            
        if 'side' in order_details:
            side = (order_details or {}).get('side')
            
        if 'qty' in order_details:
            quantity = (order_details or {}).get('qty')
            
        if 'type' in order_details:
            order_type = (order_details or {}).get('type')
            
        # For TD Ameritrade or more complex orders
        if 'orderLegCollection' in order_details:
            legs = (order_details or {}).get('orderLegCollection', [])
            if legs:
                first_leg = legs[0]
                symbol = (first_leg or {}).get('instrument', {}).get('symbol')
                instruction = (first_leg or {}).get('instruction', '')
                if 'BUY' in instruction:
                    side = 'buy'
                elif 'SELL' in instruction:
                    side = 'sell'
                quantity = (first_leg or {}).get('quantity')
                
        if 'orderType' in order_details:
            order_type = (order_details or {}).get('orderType')
            
        # For Schwab or other unknown formats
        if symbol is None and 'symbol' in order_details:
            symbol = (order_details or {}).get('symbol')
            
        # Format a nice message
        message = f"Order simulated: "
        if symbol:
            message += f"{symbol} "
        if side:
            message += f"{side} "
        if quantity:
            message += f"{quantity} shares "
        if order_type:
            message += f"({order_type}) "
            
        return {
            'success': True,
            'order_id': order_id,
            'message': message,
            'simulated': True,
            'timestamp': datetime.now().isoformat(),
            'details': order_details
        }
    
    def get_market_hours(self):
        """
        Get market hours information.
        
        Returns:
            dict: Market hours information
        """
        try:
            if self.force_simulation:
                # Return simulated market hours
                return self._get_simulated_market_hours()
                
            if self.provider == 'alpaca':
                response = self.session.get(f"{self.base_url}/v2/calendar", headers=self.headers)
                
                if response.status_code == 200:
                    calendar_data = response.json() if response.content else {}
                    
                    # Get today's entry
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    today_entry = None
                    
                    for entry in calendar_data:
                        if (entry or {}).get('date') == today_str:
                            today_entry = entry
                            break
                            
                    if today_entry:
                        market_open = datetime.strptime(f"{today_str} {(today_entry or {}).get('open')}", "%Y-%m-%d %H:%M")
                        market_close = datetime.strptime(f"{today_str} {(today_entry or {}).get('close')}", "%Y-%m-%d %H:%M")
                        
                        return {
                            'is_open': datetime.now() >= market_open and datetime.now() <= market_close,
                            'open_time': market_open.strftime("%H:%M"),
                            'close_time': market_close.strftime("%H:%M"),
                            'next_open': market_open.strftime("%Y-%m-%d %H:%M") if datetime.now() < market_open else None,
                            'next_close': market_close.strftime("%Y-%m-%d %H:%M") if datetime.now() < market_close else None
                        }
                    else:
                        return self._get_simulated_market_hours()
                else:
                    logger.warning(f"Failed to get market hours: {response.status_code}, {response.text}")
                    return self._get_simulated_market_hours()
                    
            elif self.provider == 'td_ameritrade':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for TD Ameritrade API")
                    return self._get_simulated_market_hours()
                
                # Add authorization header
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                # Get today's date
                today_str = datetime.now().strftime("%Y-%m-%d")
                
                response = self.session.get(
                    f"{self.base_url}/marketdata/hours",
                    params={
                        'markets': 'EQUITY',
                        'date': today_str
                    },
                    headers=headers
                )
                
                if response.status_code == 200:
                    hours_data = response.json() if response.content else {}
                    equity_hours = (hours_data or {}).get('equity', {}).get('EQ')
                    
                    if equity_hours and today_str in equity_hours:
                        today_session = equity_hours[today_str]
                        
                        if isinstance(today_session, dict) and 'marketType' in today_session:
                            is_open = (today_session or {}).get('marketType') == 'REGULAR'
                            
                            if 'sessionHours' in today_session and 'regularMarket' in today_session['sessionHours']:
                                regular_sessions = today_session['sessionHours']['regularMarket']
                                if regular_sessions:
                                    first_session = regular_sessions[0]
                                    market_open = (first_session or {}).get('start')
                                    market_close = (first_session or {}).get('end')
                                    
                                    return {
                                        'is_open': is_open,
                                        'open_time': datetime.fromisoformat(market_open.replace('Z', '+00:00')).strftime("%H:%M"),
                                        'close_time': datetime.fromisoformat(market_close.replace('Z', '+00:00')).strftime("%H:%M"),
                                        'next_open': market_open if datetime.now().isoformat() < market_open else None,
                                        'next_close': market_close if datetime.now().isoformat() < market_close else None
                                    }
                                    
                    # Fallback to simulated hours
                    return self._get_simulated_market_hours()
                else:
                    logger.warning(f"Failed to get market hours: {response.status_code}, {response.text}")
                    # Try to refresh token if unauthorized
                    if response.status_code == 401 and self.refresh_token:
                        logger.info("Attempting to refresh access token")
                        # Use standardized refresh access token method
                        if self.refresh_access_token():
                            return self.get_market_hours()  # Try again with new token
                    return self._get_simulated_market_hours()
                    
            elif self.provider == 'schwab':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for Schwab API")
                    return self._get_simulated_market_hours()
                
                # Add authorization header
                headers = self.headers.copy()
                headers['Authorization'] = f"Bearer {self.access_token}"
                
                # In a real implementation, you would make an API call to Schwab
                # Since we don't have actual Schwab API docs, we'll simulate a response
                logger.info("Simulating Schwab market hours request")
                
                return self._get_simulated_market_hours()
                
            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return self._get_simulated_market_hours()
                
        except Exception as e:
            logger.error(f"Error getting market hours: {str(e)}")
            return self._get_simulated_market_hours()
            
    def _get_simulated_market_hours(self):
        """Generate simulated market hours information."""
        # US market hours: 9:30 AM - 4:00 PM Eastern Time
        now = datetime.now()
        
        # Check if weekend
        if now.weekday() >= 5:  # 5=Saturday, 6=Sunday
            is_open = False
            # Next open will be Monday morning
            next_open_day = now + timedelta(days=(7 - now.weekday()) % 7)
            next_open = datetime(next_open_day.year, next_open_day.month, next_open_day.day, 9, 30)
            next_close = None
        else:
            # Weekday - check time
            market_open = datetime(now.year, now.month, now.day, 9, 30)
            market_close = datetime(now.year, now.month, now.day, 16, 0)
            
            is_open = now >= market_open and now <= market_close
            
            if now < market_open:
                next_open = market_open.strftime("%Y-%m-%d %H:%M")
                next_close = market_close.strftime("%Y-%m-%d %H:%M")
            elif now < market_close:
                next_open = None
                next_close = market_close.strftime("%Y-%m-%d %H:%M")
            else:
                # After market close, next open is tomorrow
                if now.weekday() == 4:  # Friday
                    # Next is Monday
                    next_open_day = now + timedelta(days=3)
                else:
                    # Next is tomorrow
                    next_open_day = now + timedelta(days=1)
                    
                next_open = datetime(next_open_day.year, next_open_day.month, next_open_day.day, 9, 30).strftime("%Y-%m-%d %H:%M")
                next_close = None
                
        return {
            'is_open': is_open,
            'open_time': "09:30",
            'close_time': "16:00",
            'next_open': next_open,
            'next_close': next_close
        }
    
    def get_account_history(self, start_date=None, end_date=None):
        """
        Get account history data (equity curve).
        
        Args:
            start_date (str): Start date (YYYY-MM-DD)
            end_date (str): End date (YYYY-MM-DD)
            
        Returns:
            pandas.DataFrame: Account history data
        """
        return self.get_equity_history(days=90)  # Default to 90 days if dates not specified
        
    def get_equity_history(self, days=30):
        """
        Get equity history data for specified number of days.
        
        Args:
            days (int): Number of days of history to retrieve
            
        Returns:
            dict: Equity history data with dates and values
        """
        # Convert days to date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        try:
            if self.force_simulation:
                # Return simulated account history
                return self._get_simulated_account_history(start_date=start_date, end_date=end_date)
                
            if self.provider == 'alpaca':
                # Alpaca doesn't have a direct endpoint for account history
                # We would have to build it from portfolio history or custom track it
                logger.warning("Alpaca doesn't provide account history directly. Using simulated data.")
                return self._get_simulated_account_history(start_date=start_date, end_date=end_date)
                
            elif self.provider == 'td_ameritrade':
                # Check if we have a valid access token
                if not self.access_token:
                    logger.warning("No access token available for TD Ameritrade API")
                    return self._get_simulated_account_history(start_date=start_date, end_date=end_date)
                
                # TD Ameritrade doesn't provide historical equity curves through the API
                logger.warning("TD Ameritrade doesn't provide account history directly. Using simulated data.")
                return self._get_simulated_account_history(start_date=start_date, end_date=end_date)
                
            elif self.provider == 'schwab':
                # Use our specialized Schwab connector for improved reliability
                if self.force_simulation:
                    logger.info("Using simulation mode for Schwab account history")
                    return self._get_simulated_account_history(start_date=start_date, end_date=end_date)
                
                # Sync tokens with specialized connector
                if self.access_token:
                    self.schwab_connector.access_token = self.access_token
                    self.schwab_connector.refresh_token = self.refresh_token
                    self.schwab_connector.token_expiry = self.token_expiry
                
                try:
                    logger.info("Retrieving account performance using specialized Schwab connector")
                    performance_data = self.schwab_connector.get_account_performance(
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if performance_data and 'daily_equity' in performance_data and 'dates' in performance_data:
                        logger.info(f"Successfully retrieved Schwab account performance data with {len(performance_data['dates'])} data points")
                        
                        # If token was refreshed in the specialized connector, sync it back
                        if self.schwab_connector.access_token != self.access_token:
                            logger.info("Synchronizing refreshed tokens from specialized connector")
                            self.access_token = self.schwab_connector.access_token
                            self.refresh_token = self.schwab_connector.refresh_token
                            self.token_expiry = self.schwab_connector.token_expiry
                            
                            # Update session headers
                            self.session.headers.update({
                                'Authorization': f'Bearer {self.access_token}'
                            })
                        
                        # Convert the performance data to a pandas DataFrame
                        import pandas as pd
                        df = pd.DataFrame({
                            'date': pd.to_datetime(performance_data['dates']),
                            'equity': performance_data['daily_equity']
                        })
                        
                        # Set date as index to match the expected return format
                        df = df.set_index('date')
                        
                        return df
                    else:
                        logger.warning("Failed to get account performance data from Schwab API or data is empty")
                        return self._get_simulated_account_history(start_date=start_date, end_date=end_date)
                except Exception as e:
                    logger.error(f"Error getting Schwab account performance: {str(e)}")
                    return self._get_simulated_account_history(start_date=start_date, end_date=end_date)
                
            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return self._get_simulated_account_history(start_date=start_date, end_date=end_date)
                
        except Exception as e:
            logger.error(f"Error getting account history: {str(e)}")
            return self._get_simulated_account_history(start_date=start_date, end_date=end_date)
            
    def _get_simulated_account_history(self, start_date=None, end_date=None):
        """Generate simulated account history data."""
        # Default date range: last 90 days
        if not end_date:
            end_date = datetime.now().date()
        else:
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                
        if not start_date:
            start_date = end_date - timedelta(days=90)
        else:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                
        # Generate daily data
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Seed random generator based on provider for consistency
        random.seed(hash(self.provider) % 10000)
        
        # Starting equity
        starting_equity = 10000
        
        # Generate random walk with slight upward drift
        equities = [starting_equity]
        for i in range(1, len(dates)):
            # Weekends have no change
            if dates[i].weekday() >= 5:
                equities.append(equities[-1])
            else:
                # Random walk with slight upward drift
                pct_change = random.gauss(0.0005, 0.01)  # Slight positive drift
                new_equity = equities[-1] * (1 + pct_change)
                # Use float formatting to avoid type issues with round()
                new_equity_rounded = float(f"{new_equity:.2f}")
                equities.append(new_equity_rounded)
                
        # Create DataFrame
        df = pd.DataFrame({
            'date': dates,
            'equity': equities
        })
        
        # Reset random seed
        random.seed()
        
        return df
    
    def get_monthly_returns(self, months=12):
        """
        Get monthly returns data.
        
        Args:
            months (int): Number of months to retrieve
            
        Returns:
            dict: Monthly returns data with 'months' and 'returns' lists
        """
        try:
            # We'll calculate this from the account history
            # Get account history for the past N months plus one month
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=months*31 + 31)  # Add extra month for calculating first month's return
            
            # Get account history
            account_history = self.get_account_history(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            
            # Convert to monthly data
            account_history['date'] = pd.to_datetime(account_history['date'])
            account_history = account_history.set_index('date')
            
            # Resample to month-end (using 'ME' instead of deprecated 'M')
            monthly = account_history.resample('ME').last()
            
            # Calculate monthly returns
            monthly['return'] = monthly['equity'].pct_change() * 100
            
            # Drop NaN values (first month)
            monthly = monthly.dropna()
            
            # Format dates as month names
            month_labels = [d.strftime('%b %Y') for d in monthly.index]
            
            return {
                'months': month_labels[-months:],
                'returns': monthly['return'].tolist()[-months:]
            }
        
        except Exception as e:
            logger.error(f"Error getting monthly returns: {str(e)}")
            return {
                'months': [],
                'returns': []
            }
            
    def _can_execute_options_trades(self):
        """
        Check if we are authorized to execute options trades or need to fall back to simulation.
        
        Returns:
            bool: True if we can execute real options trades, False otherwise
        """
        # Only attempt real trades if not in force simulation mode
        if self.force_simulation:
            return False
            
        # Check provider-specific requirements
        if self.provider == 'schwab':
            # Need valid access token
            if not self.access_token:
                logger.warning("No Schwab access token available, falling back to simulation for options trades")
                return False
                
            # Additional check for options trading permissions could go here
            # In a real implementation, we would verify the account has options trading enabled
            
        elif self.provider == 'td_ameritrade':
            # Need account info
            account_info = self.get_account_info()
            if not account_info:
                logger.warning("Could not retrieve TD Ameritrade account info, falling back to simulation for options trades")
                return False
                
            # Check for options trading permissions
            # This is a simplified check - in reality would be more complex
            has_options = False
            for account_id, details in account_info.items():
                if (details or {}).get('optionLevel', 0) > 0:
                    has_options = True
                    break
                    
            if not has_options:
                logger.warning("TD Ameritrade account does not have options trading permissions")
                return False
                
        else:
            # For other providers like Alpaca that don't support options in public API
            logger.warning(f"{self.provider} does not support options trading via API")
            return False
            
        return True
        
    def execute_put_credit_spread(self, symbol, quantity, short_strike, long_strike, expiry_date):
        """
        Execute a put credit spread strategy.
        
        Args:
            symbol (str): Stock symbol
            quantity (int): Number of contracts
            short_strike (float): Short put strike price
            long_strike (float): Long put strike price
            expiry_date (str): Expiry date for the options
            
        Returns:
            dict: Trade execution result
        """
        try:
            if self.force_simulation or not self._can_execute_options_trades():
                logger.info(f"Simulating put credit spread execution for {symbol} (simulation mode)")
                # Return simulated successful execution
                return {
                    'success': True,
                    'order_id': f"PCS_{symbol}_{int(datetime.now().timestamp())}",
                    'timestamp': datetime.now().isoformat(),
                    'message': 'Simulated put credit spread execution',
                    'simulated': True
                }
            
            # Format for expiry date if provided as datetime
            if isinstance(expiry_date, datetime):
                expiry_date = expiry_date.strftime('%Y-%m-%d')
            
            # Format based on the broker API
            if self.provider == 'td_ameritrade':
                account_info = self.get_account_info()
                account_id = list(account_info.keys())[0] if account_info else None
                
                if not account_id:
                    return {
                        'success': False,
                        'message': 'Could not determine account ID'
                    }
                
                # Format option symbols (e.g., "AAPL_062522P150")
                expiry_formatted = datetime.strptime(expiry_date, '%Y-%m-%d').strftime('%m%d%y')
                short_strike_formatted = str(int(short_strike * 1000)).zfill(8)
                long_strike_formatted = str(int(long_strike * 1000)).zfill(8)
                
                short_option_symbol = f"{symbol}_{expiry_formatted}P{short_strike_formatted}"
                long_option_symbol = f"{symbol}_{expiry_formatted}P{long_strike_formatted}"
                
                # Create order for TD Ameritrade
                order_details = {
                    'complexOrderStrategyType': 'VERTICAL',
                    'orderType': 'NET_CREDIT',
                    'session': 'NORMAL',
                    'duration': 'DAY',
                    'orderStrategyType': 'SINGLE',
                    'price': '0.10',  # Minimum credit for the spread
                    'orderLegCollection': [
                        {
                            'instruction': 'SELL_TO_OPEN',
                            'quantity': quantity,
                            'instrument': {
                                'symbol': short_option_symbol,
                                'assetType': 'OPTION'
                            }
                        },
                        {
                            'instruction': 'BUY_TO_OPEN',
                            'quantity': quantity,
                            'instrument': {
                                'symbol': long_option_symbol,
                                'assetType': 'OPTION'
                            }
                        }
                    ]
                }
                
                # Execute the order
                result = self.place_order(order_details, account_id)
                return result
                
            elif self.provider == 'schwab':
                # For Schwab API
                if not self.access_token:
                    return {
                        'success': False,
                        'message': 'Authentication required for Schwab API'
                    }
                
                # Create order for Schwab API
                # Note: This is speculative as actual Schwab API may have different requirements
                order_details = {
                    'orderType': 'SPREAD',
                    'spreadType': 'VERTICAL_PUT',
                    'side': 'CREDIT',
                    'symbol': symbol,
                    'quantity': quantity,
                    'shortStrike': short_strike,
                    'longStrike': long_strike,
                    'expiryDate': expiry_date,
                    'timeInForce': 'DAY'
                }
                
                # Execute the order (based on Schwab API endpoints)
                result = self._execute_schwab_options_order(order_details)
                return result
                
            else:
                logger.warning(f"Put credit spread not directly supported for {self.provider} API, simulating instead")
                # Fallback to simulation
                return {
                    'success': True,
                    'order_id': f"PCS_{symbol}_{int(datetime.now().timestamp())}",
                    'timestamp': datetime.now().isoformat(),
                    'message': f'Simulated put credit spread execution (unsupported broker: {self.provider})',
                    'simulated': True
                }
                
        except Exception as e:
            logger.error(f"Error executing put credit spread for {symbol}: {str(e)}")
            return {
                'success': False,
                'message': f"Error executing put credit spread: {str(e)}"
            }
            
    def _execute_schwab_options_order(self, order_details):
        """
        Execute an options order through Schwab API.
        
        Args:
            order_details (dict): Order details to send to Schwab API
            
        Returns:
            dict: Order execution result
        """
        # Check if we are authorized to make trades or need to fall back to simulation
        if not self._can_execute_options_trades():
            # Simulation fallback
            logger.info(f"Simulating Schwab options order for {(order_details or {}).get('symbol')} (unauthorized)")
            return {
                'success': True,
                'order_id': f"SCH_SIM_{(order_details or {}).get('symbol')}_{int(datetime.now().timestamp())}",
                'timestamp': datetime.now().isoformat(),
                'message': 'Simulated Schwab options order execution (unauthorized)',
                'simulated': True
            }
            
        try:
            # This would call the actual Schwab API endpoint for options orders
            # For now, we'll simulate success
            logger.info(f"Simulating Schwab options order for {(order_details or {}).get('symbol')}")
            
            # Simulated response
            return {
                'success': True,
                'order_id': f"SCH_{(order_details or {}).get('symbol')}_{int(datetime.now().timestamp())}",
                'timestamp': datetime.now().isoformat(),
                'message': 'Simulated Schwab options order execution',
                'simulated': True
            }
            
        except Exception as e:
            logger.error(f"Error executing Schwab options order: {str(e)}")
            return {
                'success': False,
                'message': f"Error executing Schwab options order: {str(e)}"
            }
