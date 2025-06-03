"""
Schwab API Connector

A specialized connector for the Charles Schwab API with enhanced error handling, retry logic,
and optimized connection settings specifically for Schwab's API requirements.
"""

import logging
import json
import time
import requests
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode

# Configure logging
logger = logging.getLogger(__name__)

class SchwabConnector:
    """
    Specialized connector for the Charles Schwab API.
    
    This connector handles all API communications with Schwab's API,
    including authentication, token management, and API calls.
    It implements robust error handling and automatic retries.
    """
    
    def __init__(self, client_id=None, client_secret=None, access_token=None, 
                 refresh_token=None, token_expiry=None, is_sandbox=True,
                 auth_proxy_url=None, token_proxy_url=None):
        """
        Initialize the Schwab API connector.
        
        Args:
            client_id (str): Schwab API client ID (OAuth2 client_id)
            client_secret (str): Schwab API client secret (OAuth2 client_secret)
            access_token (str, optional): OAuth2 access token if already authenticated
            refresh_token (str, optional): OAuth2 refresh token for token renewal
            token_expiry (datetime, optional): When the access token expires
            is_sandbox (bool): Whether to use sandbox environment (default True)
            auth_proxy_url (str, optional): URL for OAuth authorization proxy
            token_proxy_url (str, optional): URL for OAuth token exchange proxy
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry
        self.is_sandbox = is_sandbox
        self.auth_proxy_url = auth_proxy_url
        self.token_proxy_url = token_proxy_url
        
        # Create a session for connection pooling and consistent headers
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Schwab Trading Bot/1.0'
        })
        
        # Set up API endpoints based on environment
        self._setup_endpoints()
        
        # Add authorization header if access token is provided
        if self.access_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}'
            })
            
        # Internal state tracking
        self.last_request_time = None
        self.request_count = 0
        self.error_count = 0
        
        # Connection diagnostic data
        self.connection_diagnostics = {
            'last_status_code': None,
            'last_error_message': None,
            'last_successful_request': None,
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'connection_status': 'initialized'
        }
        
        logger.info(f"Initialized Schwab connector in {'sandbox' if is_sandbox else 'production'} mode")
    
    def _setup_endpoints(self):
        """Set up API endpoints based on environment (sandbox or production)."""
        if self.is_sandbox:
            # Schwab Sandbox environment - Exact URLs per Schwab Developer Portal
            self.api_base_url = "https://api.schwabapi.com/trader/v1"
            self.auth_url = "https://api.schwabapi.com/v1/oauth/authorize"
            self.token_url = "https://api.schwabapi.com/v1/oauth/token"
            self.market_data_url = "https://api.schwabapi.com/marketdata/v1"
            logger.info("Using Schwab sandbox API endpoints")
        else:
            # Schwab Production environment - Exact URLs per Schwab Developer Portal
            self.api_base_url = "https://api.schwabapi.com/trader/v1"
            self.auth_url = "https://api.schwabapi.com/v1/oauth/authorize"
            self.token_url = "https://api.schwabapi.com/v1/oauth/token"
            self.market_data_url = "https://api.schwabapi.com/marketdata/v1"
            logger.info("Using Schwab production API endpoints")
    
    def is_connected(self):
        """
        Check if the connector is properly connected to the Schwab API.
        
        This method verifies both the presence of valid credentials and makes
        a test API call to confirm the connection is working.
        
        Returns:
            bool: True if connected, False otherwise
        """
        # First check if we have credentials
        if not self.access_token:
            logger.warning("No access token available for Schwab API")
            return False
        
        # Then check if the token might be expired
        if self.is_token_expired():
            logger.info("Access token has expired, attempting to refresh")
            if not self.refresh_access_token():
                logger.warning("Token refresh failed")
                return False
        
        # Make a test API call to verify connection
        try:
            # Test the accounts endpoint
            account_url = f"{self.api_base_url}/accounts"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            logger.info(f"Testing connection to Schwab API: {account_url}")
            response = self.session.get(account_url, headers=headers, timeout=10)
            
            self.connection_diagnostics['last_status_code'] = response.status_code
            self.connection_diagnostics['total_requests'] += 1
            
            if response.status_code == 200:
                # Connection successful
                logger.info("Successfully connected to Schwab API")
                self.connection_diagnostics['last_successful_request'] = datetime.now()
                self.connection_diagnostics['successful_requests'] += 1
                self.connection_diagnostics['connection_status'] = 'connected'
                return True
            elif response.status_code == 401:
                # Unauthorized, try to refresh token
                logger.info("Unauthorized response, attempting to refresh token")
                if self.refresh_access_token():
                    # Try the connection check again
                    return self.is_connected()
                else:
                    logger.warning("Failed to refresh access token")
                    self.connection_diagnostics['connection_status'] = 'unauthorized'
                    self.connection_diagnostics['failed_requests'] += 1
                    return False
            else:
                # Other error
                logger.warning(f"API connection failed with status code {response.status_code}: {response.text}")
                self.connection_diagnostics['last_error_message'] = f"Status {response.status_code}: {response.text[:100]}"
                self.connection_diagnostics['connection_status'] = 'error'
                self.connection_diagnostics['failed_requests'] += 1
                return False
        except requests.RequestException as e:
            # Network or timeout error
            logger.warning(f"Connection test failed: {str(e)}")
            self.connection_diagnostics['last_error_message'] = str(e)
            self.connection_diagnostics['connection_status'] = 'network_error'
            self.connection_diagnostics['failed_requests'] += 1
            return False
    
    def is_token_expired(self):
        """
        Check if the access token is expired or will expire soon.
        
        Considers the token expired if it's within 5 minutes of expiration
        to prevent failures in the middle of operations.
        
        Returns:
            bool: True if token is expired or will expire soon, False otherwise
        """
        if not self.token_expiry:
            # No expiry time set, consider it expired to be safe
            return True
        
        # Consider token expired if less than 5 minutes remaining
        buffer_time = timedelta(minutes=5)
        return datetime.now() + buffer_time >= self.token_expiry
    
    def refresh_access_token(self):
        """
        Refresh the access token using the refresh token.
        
        This method implements OAuth 2.0 refresh token flow as specified in
        Schwab API documentation. It includes retries and error handling.
        
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
            'refresh_token': self.refresh_token
        }
        
        # Schwab requires basic auth with client credentials
        auth = (self.client_id, self.client_secret)
        
        # Common headers for token requests
        token_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        # Use proxy URL if provided, otherwise direct connection
        url = self.token_proxy_url if self.token_proxy_url else self.token_url
        
        # Implement retry logic
        max_retries = 3
        retry_delay = 2  # seconds
        
        for retry in range(max_retries):
            try:
                # Execute the token refresh request
                logger.info(f"Attempting to refresh access token (try {retry+1}/{max_retries})")
                
                token_response = requests.post(
                    url,
                    data=token_payload,
                    headers=token_headers,
                    auth=auth,
                    timeout=15  # Longer timeout for token operations
                )
                
                logger.info(f"Token refresh response status: {token_response.status_code}")
                
                if token_response.status_code == 200:
                    # Process successful token response
                    token_data = token_response.json() if response.content else {}
                    
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
                    
                    logger.info(f"Successfully refreshed access token, expires in {expires_in} seconds")
                    return True
                    
                elif token_response.status_code in (429, 500, 502, 503, 504):
                    # Retryable errors: rate limits or server errors
                    if retry < max_retries - 1:
                        wait_time = retry_delay * (2 ** retry)  # Exponential backoff
                        logger.warning(f"Retryable error {token_response.status_code}, waiting {wait_time}s before retry")
                        time.sleep(wait_time)
                        continue
                
                # Handle error response
                try:
                    error_content = token_response.json() if token_response.content else {}
                except ValueError:
                    error_content = {}
                
                error_type = (error_content or {}).get('error', 'server_error')
                error_desc = (error_content or {}).get('error_description', token_response.text[:100])
                
                logger.warning(f"Token refresh error: {error_type} - {error_desc}")
                return False
                
            except requests.RequestException as e:
                # Network error
                logger.warning(f"Network error during token refresh: {str(e)}")
                if retry < max_retries - 1:
                    wait_time = retry_delay * (2 ** retry)  # Exponential backoff
                    logger.warning(f"Waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                    continue
                return False
        
        # If we get here, all retries failed
        logger.error("Token refresh failed after maximum retries")
        return False
    
    def get_account_info(self):
        """
        Get account information from the Schwab API.
        
        Returns:
            dict: Dictionary of account information keyed by account ID
        """
        # Check if we have a valid access token
        if not self.access_token:
            logger.warning("No access token available for Schwab API")
            return None
        
        # Refresh token if needed
        if self.is_token_expired():
            logger.info("Access token expired, refreshing before request")
            if not self.refresh_access_token():
                logger.warning("Failed to refresh token for account info request")
                return None
        
        # Make the API request
        try:
            accounts_url = f"{self.api_base_url}/accounts"
            response = self._execute_request('GET', accounts_url)
            
            if response and response.status_code == 200:
                accounts_data = response.json() if response.content else {}
                logger.info(f"Successfully retrieved Schwab account data: {len(accounts_data)} accounts")
                
                result = {}
                
                for account in accounts_data:
                    account_id = (account or {}).get('accountId', 'unknown')
                    account_details = account
                    
                    # Extract balance information with proper path for Schwab API
                    balances = (account_details or {}).get('balances', {})
                    positions = (account_details or {}).get('positions', [])
                    
                    result[account_id] = {
                        'account_number': account_id,
                        'cash': float((balances or {}).get('cashBalance', 0)),
                        'equity': float((balances or {}).get('liquidationValue', 0)),
                        'buying_power': float((balances or {}).get('buyingPower', 0)),
                        'position_count': len(positions),
                        'account_type': (account_details or {}).get('accountType', 'Unknown'),
                        'nickname': (account_details or {}).get('nickname', ''),
                    }
                
                return result
            
            logger.warning(f"Failed to get account info: {response.status_code if response else 'No response'}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting Schwab account info: {str(e)}")
            return None
    
    def get_positions(self, account_id=None):
        """
        Get positions for a specific account or the first available account.
        
        Args:
            account_id (str, optional): Specific account ID to get positions for
                If not provided, will use the first account from get_account_info()
        
        Returns:
            list: List of position dictionaries, each containing position details
        """
        # Check if we have a valid access token
        if not self.access_token:
            logger.warning("No access token available for Schwab API")
            return None
        
        # Refresh token if needed
        if self.is_token_expired():
            logger.info("Access token expired, refreshing before request")
            if not self.refresh_access_token():
                logger.warning("Failed to refresh token for positions request")
                return None
        
        # Get account ID if not provided
        if not account_id:
            accounts = self.get_account_info()
            if not accounts:
                logger.warning("Could not determine account ID for positions")
                return None
            account_id = list(accounts.keys())[0]
        
        # Make the API request
        try:
            positions_url = f"{self.api_base_url}/accounts/{account_id}/positions"
            response = self._execute_request('GET', positions_url)
            
            if response and response.status_code == 200:
                positions_data = response.json() if response.content else {}
                logger.info(f"Successfully retrieved {len(positions_data)} positions from Schwab API")
                
                result = []
                
                for position in positions_data:
                    # Extract data with proper field names for Schwab API
                    instrument = (position or {}).get('instrument', {})
                    symbol = (instrument or {}).get('symbol')
                    quantity = (position or {}).get('quantity', 0)
                    
                    # Skip zero positions
                    if quantity == 0:
                        continue
                    
                    price_data = (position or {}).get('priceData', {})
                    entry_price = (position or {}).get('averagePurchasePrice', 0)
                    current_price = (price_data or {}).get('currentPrice', 0)
                    
                    result.append({
                        'symbol': symbol,
                        'quantity': int(quantity),
                        'entry_price': float(entry_price),
                        'current_price': float(current_price),
                        'market_value': float(current_price * quantity),
                        'cost_basis': float(entry_price * quantity),
                        'unrealized_pl': float((current_price - entry_price) * quantity),
                        'unrealized_plpc': float((current_price - entry_price) / entry_price) if entry_price > 0 else 0,
                    })
                
                return result
            
            logger.warning(f"Failed to get positions: {response.status_code if response else 'No response'}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting Schwab positions: {str(e)}")
            return None
    
    def place_order(self, order_details, account_id=None):
        """
        Place an order via the Schwab API.
        
        Args:
            order_details (dict): Order details in Schwab API format
            account_id (str, optional): Account ID to place the order under
                If not provided, will use the first account from get_account_info()
        
        Returns:
            dict: Response containing order status, ID, etc.
        """
        # Check if we have a valid access token
        if not self.access_token:
            logger.warning("No access token available for Schwab API")
            return {'success': False, 'message': 'No API access token available'}
        
        # Refresh token if needed
        if self.is_token_expired():
            logger.info("Access token expired, refreshing before request")
            if not self.refresh_access_token():
                logger.warning("Failed to refresh token for order placement")
                return {'success': False, 'message': 'Failed to refresh API token'}
        
        # Get account ID if not provided
        if not account_id:
            accounts = self.get_account_info()
            if not accounts:
                logger.warning("Could not determine account ID for order placement")
                return {'success': False, 'message': 'Could not determine account ID'}
            account_id = list(accounts.keys())[0]
        
        # Make the API request
        try:
            orders_url = f"{self.api_base_url}/accounts/{account_id}/orders"
            response = self._execute_request('POST', orders_url, json=order_details)
            
            if response and (response.status_code == 200 or response.status_code == 201):
                # Successfully placed order
                order_id = None
                location = response.(headers or {}).get('Location', '')
                if location:
                    order_id = location.split('/')[-1]
                
                try:
                    response_data = response.json() if response.content else {}
                    # Some APIs return order ID in response body
                    if 'orderId' in response_data:
                        order_id = response_data['orderId']
                except ValueError:
                    pass
                
                return {
                    'success': True,
                    'order_id': order_id or 'unknown',
                    'message': f"Order placed successfully",
                    'details': response.json() if response.content else {} if 'application/json' in response.(headers or {}).get('content-type', '') else None
                }
            
            # Handle error responses
            error_message = f"Failed to place order: {response.status_code if response else 'No response'}"
            try:
                error_data = response.json() if response.content else {} if response else {}
                if 'message' in error_data:
                    error_message = f"Error: {error_data['message']}"
            except ValueError:
                pass
            
            logger.warning(error_message)
            return {'success': False, 'message': error_message}
            
        except Exception as e:
            logger.error(f"Error placing Schwab order: {str(e)}")
            return {'success': False, 'message': f"Exception: {str(e)}"}
    
    def get_orders(self, account_id=None, status='all'):
        """
        Get orders for a specific account or the first available account.
        
        Args:
            account_id (str, optional): Specific account ID to get orders for
                If not provided, will use the first account from get_account_info()
            status (str): Filter by order status ('all', 'open', 'closed')
        
        Returns:
            list: List of order dictionaries, each containing order details
        """
        # Check if we have a valid access token
        if not self.access_token:
            logger.warning("No access token available for Schwab API")
            return None
        
        # Refresh token if needed
        if self.is_token_expired():
            logger.info("Access token expired, refreshing before request")
            if not self.refresh_access_token():
                logger.warning("Failed to refresh token for orders request")
                return None
        
        # Get account ID if not provided
        if not account_id:
            accounts = self.get_account_info()
            if not accounts:
                logger.warning("Could not determine account ID for orders")
                return None
            account_id = list(accounts.keys())[0]
        
        # Prepare query parameters based on status filter
        params = {}
        if status == 'open':
            params['status'] = 'OPEN'
        elif status == 'closed':
            params['status'] = 'EXECUTED,CANCELED,REJECTED,EXPIRED'
        
        # Make the API request
        try:
            orders_url = f"{self.api_base_url}/accounts/{account_id}/orders"
            response = self._execute_request('GET', orders_url, params=params)
            
            if response and response.status_code == 200:
                orders_data = response.json() if response.content else {}
                logger.info(f"Successfully retrieved {len(orders_data)} orders from Schwab API")
                
                result = []
                
                for order in orders_data:
                    # Extract relevant order information
                    order_legs = (order or {}).get('orderLegCollection', [])
                    if not order_legs:
                        continue
                    
                    leg = order_legs[0]  # Use first leg for basic info
                    symbol = (leg or {}).get('symbol')
                    
                    # Map Schwab order statuses to our standardized format
                    status_map = {
                        'OPEN': 'open',
                        'EXECUTED': 'filled',
                        'CANCELED': 'canceled',
                        'REJECTED': 'rejected',
                        'EXPIRED': 'expired'
                    }
                    
                    result.append({
                        'id': (order or {}).get('orderId'),
                        'symbol': symbol,
                        'quantity': int((leg or {}).get('quantity', 0)),
                        'side': (leg or {}).get('side', '').lower(),
                        'type': (order or {}).get('orderType', '').lower(),
                        'status': (status_map or {}).get((order or {}).get('status'), (order or {}).get('status', '')),
                        'submitted_at': (order or {}).get('enteredTime'),
                        'filled_at': (order or {}).get('executedTime'),
                        'filled_quantity': (order or {}).get('filledQuantity', 0),
                        'filled_price': (order or {}).get('avgExecutionPrice', 0),
                    })
                
                return result
            
            logger.warning(f"Failed to get orders: {response.status_code if response else 'No response'}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting Schwab orders: {str(e)}")
            return None
    
    def get_transaction_history(self, account_id=None, start_date=None, end_date=None, transaction_type=None):
        """
        Get transaction history for a specific account.
        
        Args:
            account_id (str, optional): Specific account ID to get transactions for
                If not provided, will use the first account from get_account_info()
            start_date (str/datetime, optional): Start date for transactions (YYYY-MM-DD)
            end_date (str/datetime, optional): End date for transactions (YYYY-MM-DD)
            transaction_type (str, optional): Filter by transaction type ('TRADE', 'CASH', 'DIVIDEND', etc.)
        
        Returns:
            list: List of transaction dictionaries, each containing transaction details
        """
        # Check if we have a valid access token
        if not self.access_token:
            logger.warning("No access token available for Schwab API")
            return None
        
        # Refresh token if needed
        if self.is_token_expired():
            logger.info("Access token expired, refreshing before request")
            if not self.refresh_access_token():
                logger.warning("Failed to refresh token for transaction history request")
                return None
        
        # Get account ID if not provided
        if not account_id:
            accounts = self.get_account_info()
            if not accounts:
                logger.warning("Could not determine account ID for transaction history")
                return None
            account_id = list(accounts.keys())[0]
        
        # Format dates for API request
        if start_date:
            if isinstance(start_date, datetime):
                start_date = start_date.strftime('%Y-%m-%d')
        
        if end_date:
            if isinstance(end_date, datetime):
                end_date = end_date.strftime('%Y-%m-%d')
        
        # Prepare query parameters
        params = {}
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        if transaction_type:
            params['type'] = transaction_type
        
        # Make the API request
        try:
            # Endpoint based on Schwab API documentation
            transactions_url = f"{self.api_base_url}/accounts/{account_id}/transactions"
            response = self._execute_request('GET', transactions_url, params=params)
            
            if response and response.status_code == 200:
                transactions_data = response.json() if response.content else {}
                logger.info(f"Successfully retrieved {len(transactions_data)} transactions from Schwab API")
                
                result = []
                
                for transaction in transactions_data:
                    # Extract and normalize transaction data
                    transaction_type = (transaction or {}).get('type', '')
                    
                    # Create standardized transaction object
                    transaction_obj = {
                        'id': (transaction or {}).get('transactionId'),
                        'date': (transaction or {}).get('transactionDate'),
                        'settlement_date': (transaction or {}).get('settlementDate'),
                        'type': transaction_type,
                        'description': (transaction or {}).get('description', ''),
                        'amount': float((transaction or {}).get('amount', 0)),
                        'fees': float((transaction or {}).get('fees', 0)) if 'fees' in transaction else 0,
                    }
                    
                    # Add additional fields based on transaction type
                    if transaction_type == 'TRADE':
                        trade_info = (transaction or {}).get('transactionItem', {})
                        transaction_obj.update({
                            'symbol': (trade_info or {}).get('symbol'),
                            'quantity': float((trade_info or {}).get('quantity', 0)),
                            'price': float((trade_info or {}).get('price', 0)),
                            'instruction': (trade_info or {}).get('instruction', '').lower(),  # BUY, SELL, etc.
                            'asset_type': (trade_info or {}).get('assetType'),
                        })
                    elif transaction_type == 'DIVIDEND':
                        dividend_info = (transaction or {}).get('transactionItem', {})
                        transaction_obj.update({
                            'symbol': (dividend_info or {}).get('symbol'),
                            'dividend_rate': float((dividend_info or {}).get('dividendRate', 0)),
                        })
                    
                    result.append(transaction_obj)
                
                return result
            
            logger.warning(f"Failed to get transaction history: {response.status_code if response else 'No response'}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting Schwab transaction history: {str(e)}")
            return None
    
    def get_trade_history(self, account_id=None, start_date=None, end_date=None, symbol=None):
        """
        Get trade history for a specific account, filtered to include only actual trades.
        
        This is a specialized wrapper around get_transaction_history that only returns
        transactions of type 'TRADE' for easier trade analysis.
        
        Args:
            account_id (str, optional): Specific account ID to get transactions for
                If not provided, will use the first account from get_account_info()
            start_date (str/datetime, optional): Start date for transactions (YYYY-MM-DD)
            end_date (str/datetime, optional): End date for transactions (YYYY-MM-DD)
            symbol (str, optional): Filter by specific symbol
        
        Returns:
            list: List of trade dictionaries, each containing trade details
        """
        # Get all trade transactions
        transactions = self.get_transaction_history(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            transaction_type='TRADE'
        )
        
        if not transactions:
            return None
        
        # Filter by symbol if provided
        if symbol:
            transactions = [t for t in transactions if (t or {}).get('symbol') == symbol]
        
        return transactions
    
    def get_account_performance(self, account_id=None, start_date=None, end_date=None):
        """
        Get account performance data including daily equity values.
        
        Args:
            account_id (str, optional): Specific account ID to get performance for
                If not provided, will use the first account from get_account_info()
            start_date (str/datetime, optional): Start date (YYYY-MM-DD)
            end_date (str/datetime, optional): End date (YYYY-MM-DD)
        
        Returns:
            dict: Dictionary with performance data including:
                - daily_equity: List of daily equity values
                - dates: List of corresponding dates
                - performance_metrics: Dictionary of performance metrics
        """
        # Check if we have a valid access token
        if not self.access_token:
            logger.warning("No access token available for Schwab API")
            return None
        
        # Refresh token if needed
        if self.is_token_expired():
            logger.info("Access token expired, refreshing before request")
            if not self.refresh_access_token():
                logger.warning("Failed to refresh token for account performance request")
                return None
        
        # Get account ID if not provided
        if not account_id:
            accounts = self.get_account_info()
            if not accounts:
                logger.warning("Could not determine account ID for account performance")
                return None
            account_id = list(accounts.keys())[0]
        
        # Format dates for API request
        if not start_date:
            # Default to last 30 days
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        elif isinstance(start_date, datetime):
            start_date = start_date.strftime('%Y-%m-%d')
        
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        elif isinstance(end_date, datetime):
            end_date = end_date.strftime('%Y-%m-%d')
        
        # Make the API request
        try:
            # Endpoint based on Schwab API documentation
            performance_url = f"{self.api_base_url}/accounts/{account_id}/performance"
            params = {
                'startDate': start_date,
                'endDate': end_date
            }
            
            response = self._execute_request('GET', performance_url, params=params)
            
            if response and response.status_code == 200:
                performance_data = response.json() if response.content else {}
                logger.info("Successfully retrieved account performance data from Schwab API")
                
                # Extract and format daily equity values
                daily_equity = []
                dates = []
                
                if 'equity' in performance_data:
                    equity_data = performance_data['equity']
                    for entry in equity_data:
                        if 'date' in entry and 'value' in entry:
                            dates.append(entry['date'])
                            daily_equity.append(float(entry['value']))
                
                # Extract performance metrics
                performance_metrics = {}
                if 'metrics' in performance_data:
                    metrics = performance_data['metrics']
                    performance_metrics = {
                        'total_return': float((metrics or {}).get('totalReturn', 0)) * 100,  # Convert to percentage
                        'annualized_return': float((metrics or {}).get('annualizedReturn', 0)) * 100,  # Convert to percentage
                        'max_drawdown': float((metrics or {}).get('maxDrawdown', 0)) * 100,  # Convert to percentage
                        'sharpe_ratio': float((metrics or {}).get('sharpeRatio', 0)),
                        'alpha': float((metrics or {}).get('alpha', 0)),
                        'beta': float((metrics or {}).get('beta', 0)),
                    }
                
                return {
                    'daily_equity': daily_equity,
                    'dates': dates,
                    'performance_metrics': performance_metrics
                }
            
            logger.warning(f"Failed to get account performance: {response.status_code if response else 'No response'}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting Schwab account performance: {str(e)}")
            return None
    
    def get_market_data(self, symbols, fields=None):
        """
        Get market data for specified symbols.
        
        Args:
            symbols (list): List of symbol strings
            fields (list, optional): List of fields to retrieve
                If not provided, gets all available fields
        
        Returns:
            dict: Market data keyed by symbol
        """
        # Check if we have a valid access token
        if not self.access_token:
            logger.warning("No access token available for Schwab API")
            return None
        
        # Refresh token if needed
        if self.is_token_expired():
            logger.info("Access token expired, refreshing before request")
            if not self.refresh_access_token():
                logger.warning("Failed to refresh token for market data request")
                return None
        
        # Prepare parameters
        params = {
            'symbols': ','.join(symbols)
        }
        if fields:
            params['fields'] = ','.join(fields)
        
        # Make the API request
        try:
            market_data_url = f"{self.api_base_url}/marketdata"
            response = self._execute_request('GET', market_data_url, params=params)
            
            if response and response.status_code == 200:
                market_data = response.json() if response.content else {}
                logger.info(f"Successfully retrieved market data for {len(symbols)} symbols")
                
                # Process and normalize the data
                result = {}
                for quote in market_data:
                    symbol = (quote or {}).get('symbol')
                    if symbol:
                        result[symbol] = quote
                
                return result
            
            logger.warning(f"Failed to get market data: {response.status_code if response else 'No response'}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting Schwab market data: {str(e)}")
            return None
    
    def get_diagnostic_info(self):
        """
        Get diagnostic information about the Schwab connection.
        
        Returns:
            dict: Connection diagnostics and status
        """
        now = datetime.now()
        
        # Update connection status
        if self.access_token:
            if self.is_token_expired():
                self.connection_diagnostics['connection_status'] = 'token_expired'
            elif self.connection_diagnostics['connection_status'] in ('initialized', 'unauthorized', 'error', 'network_error'):
                # Try to update status with a connection check
                self.is_connected()
        else:
            self.connection_diagnostics['connection_status'] = 'no_token'
        
        # Build complete diagnostic info
        diagnostics = {
            'provider': 'schwab',
            'environment': 'sandbox' if self.is_sandbox else 'production',
            'authenticated': bool(self.access_token),
            'token_expired': self.is_token_expired() if self.token_expiry else True,
            'token_expiry': self.token_expiry.isoformat() if self.token_expiry else None,
            'time_until_expiry': str(self.token_expiry - now) if self.token_expiry and self.token_expiry > now else 'expired',
            'has_refresh_token': bool(self.refresh_token),
            'connection_status': self.connection_diagnostics['connection_status'],
            'api_base_url': self.api_base_url,
            'last_status_code': self.connection_diagnostics['last_status_code'],
            'last_error_message': self.connection_diagnostics['last_error_message'],
            'last_successful_request': self.connection_diagnostics['last_successful_request'].isoformat() if self.connection_diagnostics['last_successful_request'] else None,
            'request_statistics': {
                'total': self.connection_diagnostics['total_requests'],
                'successful': self.connection_diagnostics['successful_requests'],
                'failed': self.connection_diagnostics['failed_requests'],
                'success_rate': round(self.connection_diagnostics['successful_requests'] / self.connection_diagnostics['total_requests'] * 100, 2) if self.connection_diagnostics['total_requests'] > 0 else 0
            },
            'timestamp': now.isoformat()
        }
        
        return diagnostics
    
    def _execute_request(self, method, url, params=None, data=None, json=None, headers=None, timeout=10, retry_count=2):
        """
        Execute an API request with error handling and automatic retry.
        
        Args:
            method (str): HTTP method ('GET', 'POST', etc.)
            url (str): API endpoint URL
            params (dict, optional): Query parameters
            data (dict, optional): Form data for the request
            json (dict, optional): JSON data for the request
            headers (dict, optional): Additional headers to include
            timeout (int): Timeout in seconds
            retry_count (int): Number of retries for certain failures
        
        Returns:
            requests.Response: Response object or None on failure
        """
        # Rate limiting - wait if needed
        self._rate_limit_check()
        
        # Update request count
        self.last_request_time = datetime.now()
        self.request_count += 1
        self.connection_diagnostics['total_requests'] += 1
        
        # Prepare complete headers - use current session headers and add any request-specific ones
        complete_headers = self.session.headers.copy()
        if headers:
            complete_headers.update(headers)
        
        # Make sure we have authorization if token exists
        if self.access_token and 'Authorization' not in complete_headers:
            complete_headers['Authorization'] = f'Bearer {self.access_token}'
        
        # Execute request with retry logic
        for retry in range(retry_count + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json,
                    headers=complete_headers,
                    timeout=timeout
                )
                
                # Update diagnostics
                self.connection_diagnostics['last_status_code'] = response.status_code
                
                # Handle response based on status code
                if 200 <= response.status_code < 300:
                    # Success
                    self.connection_diagnostics['last_successful_request'] = datetime.now()
                    self.connection_diagnostics['successful_requests'] += 1
                    return response
                
                elif response.status_code == 401:
                    # Unauthorized - token might be expired
                    logger.warning(f"Unauthorized response from Schwab API (401)")
                    self.connection_diagnostics['failed_requests'] += 1
                    
                    if retry < retry_count and self.refresh_token:
                        # Try to refresh token and retry
                        logger.info(f"Attempting to refresh token (retry {retry+1}/{retry_count})")
                        if self.refresh_access_token():
                            # Update authorization header for the retry
                            complete_headers['Authorization'] = f'Bearer {self.access_token}'
                            continue
                    
                    # If we get here, token refresh failed or we're out of retries
                    self.connection_diagnostics['last_error_message'] = "Unauthorized access (401)"
                    return response
                
                elif response.status_code == 429:
                    # Rate limited - back off and retry
                    retry_after = int(response.(headers or {}).get('Retry-After', retry * 5 + 1))
                    logger.warning(f"Rate limited by Schwab API, waiting {retry_after}s before retry")
                    
                    if retry < retry_count:
                        time.sleep(retry_after)
                        continue
                    
                    # Out of retries
                    self.connection_diagnostics['last_error_message'] = "Rate limited (429)"
                    self.connection_diagnostics['failed_requests'] += 1
                    return response
                
                elif 500 <= response.status_code < 600:
                    # Server error - may be transient
                    logger.warning(f"Server error from Schwab API ({response.status_code})")
                    
                    if retry < retry_count:
                        # Exponential backoff
                        wait_time = (2 ** retry) * 2
                        logger.info(f"Waiting {wait_time}s before retry")
                        time.sleep(wait_time)
                        continue
                    
                    # Out of retries
                    self.connection_diagnostics['last_error_message'] = f"Server error ({response.status_code})"
                    self.connection_diagnostics['failed_requests'] += 1
                    return response
                
                else:
                    # Other error, don't retry
                    logger.warning(f"Error response from Schwab API: {response.status_code}")
                    try:
                        error_details = response.json() if response.content else {} if 'application/json' in response.(headers or {}).get('content-type', '') else {'text': response.text[:100]}
                        logger.warning(f"Error details: {error_details}")
                    except Exception:
                        pass
                    
                    self.connection_diagnostics['last_error_message'] = f"Error ({response.status_code})"
                    self.connection_diagnostics['failed_requests'] += 1
                    return response
            
            except requests.RequestException as e:
                # Network error
                logger.warning(f"Request exception: {str(e)}")
                
                if retry < retry_count:
                    # Exponential backoff for network errors
                    wait_time = (2 ** retry) * 2
                    logger.info(f"Waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                    continue
                
                # Out of retries
                self.error_count += 1
                self.connection_diagnostics['last_error_message'] = f"Network error: {str(e)}"
                self.connection_diagnostics['failed_requests'] += 1
                return None
        
        # Should never get here, but just in case
        return None
    
    def _rate_limit_check(self):
        """
        Simple rate limiting mechanism to prevent hitting API limits.
        Schwab's exact rate limits aren't clearly documented, so we're
        being conservative here.
        """
        if not self.last_request_time:
            return
        
        # Try to maintain no more than 2 requests per second
        elapsed = (datetime.now() - self.last_request_time).total_seconds()
        if elapsed < 0.5 and self.request_count > 10:
            sleep_time = 0.5 - elapsed
            logger.debug(f"Rate limiting - sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

# Helper function to create a connector from settings
def create_connector_from_settings(settings):
    """
    Create a Schwab connector from user settings.
    
    Args:
        settings: User settings containing OAuth tokens and API credentials
        
    Returns:
        SchwabConnector: Configured connector instance
    """
    # Extract token information
    access_token = settings.oauth_access_token
    refresh_token = settings.oauth_refresh_token
    token_expiry = settings.oauth_token_expiry
    
    # Extract client credentials
    client_id = settings.api_key
    client_secret = settings.api_secret
    
    # Determine environment
    is_sandbox = settings.is_paper_trading
    
    # Create and return connector
    connector = SchwabConnector(
        client_id=client_id,
        client_secret=client_secret,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expiry=token_expiry,
        is_sandbox=is_sandbox
    )
    
    return connector