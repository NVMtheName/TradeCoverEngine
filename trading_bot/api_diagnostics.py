"""
API Diagnostics Module

Provides detailed diagnostic capabilities for troubleshooting API connection issues
with various broker APIs including Alpaca, TD Ameritrade, and Charles Schwab.
"""

import logging
import json
import requests
import socket
import datetime
import re
import ssl
import sys
import os
import traceback
import urllib.parse

# Configure logging
logger = logging.getLogger(__name__)

class APIDiagnostics:
    """
    Provides comprehensive API diagnostics for trading platform connections.
    This class helps identify and resolve connection issues with various broker APIs.
    """
    
    def __init__(self, provider='alpaca'):
        """
        Initialize the API diagnostics.
        
        Args:
            provider (str): The API provider to diagnose ('alpaca', 'td_ameritrade', 'schwab')
        """
        self.provider = provider.lower()
        self.results = {
            'status': 'unknown',
            'connection': False,
            'errors': [],
            'warnings': [],
            'info': [],
            'timestamp': datetime.datetime.now().isoformat(),
            'provider': self.provider,
            'suggestions': [],
            'endpoints_tested': [],
            'network_info': {}
        }
        
        # Provider-specific endpoints to test
        self.endpoints = self._get_provider_endpoints()
        
        # Common error patterns and solutions
        self.error_patterns = {
            'alpaca': {
                'authentication_error': {
                    'patterns': ['authentication failed', 'forbidden', '401', '403'],
                    'message': 'Authentication failed. Your API keys may be invalid or expired.',
                    'solutions': [
                        'Verify your API key and secret are correctly entered',
                        'Ensure you are using the correct keys for paper/live trading',
                        'Check if your Alpaca account is active and in good standing',
                        'Generate new API keys from the Alpaca dashboard if needed'
                    ]
                },
                'connection_error': {
                    'patterns': ['connection refused', 'timeout', 'could not connect'],
                    'message': 'Could not connect to Alpaca servers.',
                    'solutions': [
                        'Check your internet connection',
                        'Verify that Alpaca services are not experiencing downtime',
                        'Try again in a few minutes'
                    ]
                },
                'rate_limit': {
                    'patterns': ['rate limit', 'too many requests', '429'],
                    'message': 'Rate limit exceeded. You are making too many requests to the API.',
                    'solutions': [
                        'Reduce the frequency of your API requests',
                        'Implement rate limiting in your application'
                    ]
                }
            },
            'td_ameritrade': {
                'authentication_error': {
                    'patterns': ['unauthorized', 'invalid credentials', '401', '403'],
                    'message': 'Authentication failed. Your TD Ameritrade credentials may be invalid.',
                    'solutions': [
                        'Verify your API key is correct',
                        'Your OAuth token may have expired - try refreshing',
                        'Check if your TD Ameritrade app is properly registered',
                        'Ensure redirect URI matches what you registered with TD Ameritrade'
                    ]
                },
                'connection_error': {
                    'patterns': ['connection refused', 'timeout', 'could not connect'],
                    'message': 'Could not connect to TD Ameritrade servers.',
                    'solutions': [
                        'Check your internet connection',
                        'Verify that TD Ameritrade services are not experiencing downtime',
                        'Try again in a few minutes'
                    ]
                },
                'rate_limit': {
                    'patterns': ['rate limit', 'too many requests', '429'],
                    'message': 'Rate limit exceeded. You are making too many requests to the API.',
                    'solutions': [
                        'Reduce the frequency of your API requests',
                        'Implement rate limiting in your application'
                    ]
                }
            },
            'schwab': {
                'authentication_error': {
                    'patterns': ['unauthorized', 'invalid credentials', 'oauth', '401', '403'],
                    'message': 'Authentication failed. Your Schwab OAuth credentials may be invalid.',
                    'solutions': [
                        'Verify your API key (client_id) and secret (client_secret) are correct',
                        'Your OAuth token may have expired - try the OAuth authorization flow again',
                        'Check if your Schwab app is properly registered',
                        'Ensure redirect URI matches what you registered with Schwab',
                        'Make sure your app has the correct scope permissions'
                    ]
                },
                'connection_error': {
                    'patterns': ['connection refused', 'timeout', 'could not connect', 'gateway'],
                    'message': 'Could not connect to Schwab API servers.',
                    'solutions': [
                        'Check your internet connection',
                        'Verify that Schwab API services are not experiencing downtime',
                        'Try again in a few minutes',
                        'Ensure you are using the correct API endpoints for sandbox/production'
                    ]
                },
                'oauth_error': {
                    'patterns': ['invalid_grant', 'invalid_token', 'expired token'],
                    'message': 'OAuth token issue. Your token may be invalid or expired.',
                    'solutions': [
                        'Go through the OAuth authorization flow again to get a new token',
                        'Check if your refresh token is valid',
                        'Verify your redirect URI is correctly configured'
                    ]
                }
            }
        }
    
    def _get_provider_endpoints(self):
        """Get the endpoints to test for the current provider."""
        if self.provider == 'alpaca':
            return {
                'base_urls': [
                    'https://paper-api.alpaca.markets',
                    'https://api.alpaca.markets',
                    'https://data.alpaca.markets'
                ],
                'test_endpoints': {
                    'account': '/v2/account',
                    'assets': '/v2/assets',
                    'orders': '/v2/orders',
                    'positions': '/v2/positions',
                    'clock': '/v2/clock',
                    'calendar': '/v2/calendar'
                }
            }
        elif self.provider == 'td_ameritrade':
            return {
                'base_urls': [
                    'https://api.tdameritrade.com',
                    'https://auth.tdameritrade.com'
                ],
                'test_endpoints': {
                    'accounts': '/v1/accounts',
                    'instruments': '/v1/instruments',
                    'market_hours': '/v1/marketdata/hours',
                    'price_history': '/v1/marketdata/{symbol}/pricehistory',
                    'quotes': '/v1/marketdata/quotes'
                }
            }
        elif self.provider == 'schwab':
            return {
                'base_urls': [
                    'https://api.schwab.com',
                    'https://api.schwabapi.com',
                    'https://sandbox.schwabapi.com',
                    'https://developer.schwab.com'
                ],
                'test_endpoints': {
                    'oauth': '/v1/oauth/authorize',
                    'token': '/v1/oauth/token',
                    'accounts': '/v1/accounts',
                    'orders': '/v1/accounts/{account_id}/orders',
                    'positions': '/v1/accounts/{account_id}/positions',
                    'marketdata': '/v1/marketdata'
                }
            }
        else:
            return {
                'base_urls': [],
                'test_endpoints': {}
            }
    
    def test_network_connectivity(self):
        """Test basic network connectivity to API endpoints."""
        for base_url in self.endpoints['base_urls']:
            try:
                # Parse the URL to get the hostname
                parsed_url = urllib.parse.urlparse(base_url)
                hostname = parsed_url.netloc
                
                # Test DNS resolution
                try:
                    ip_address = socket.gethostbyname(hostname)
                    self.results['info'].append(f"DNS resolution for {hostname}: Success ({ip_address})")
                    self.results['network_info'][hostname] = {'ip': ip_address, 'dns_resolution': True}
                except socket.gaierror:
                    self.results['errors'].append(f"DNS resolution for {hostname}: Failed")
                    self.results['network_info'][hostname] = {'dns_resolution': False}
                    continue
                
                # Test basic HTTPS connection
                try:
                    context = ssl.create_default_context()
                    with socket.create_connection((hostname, 443), timeout=5) as sock:
                        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                            cert = ssock.getpeercert()
                            # Check if certificate is valid
                            if cert:
                                # Certificate is valid
                                self.results['info'].append(f"SSL connection to {hostname}: Success")
                                self.results['network_info'][hostname]['ssl_connection'] = True
                            else:
                                self.results['warnings'].append(f"SSL connection to {hostname}: No valid certificate found")
                                self.results['network_info'][hostname]['ssl_connection'] = False
                except (socket.timeout, ConnectionRefusedError, ssl.SSLError) as e:
                    self.results['errors'].append(f"SSL connection to {hostname}: Failed ({str(e)})")
                    self.results['network_info'][hostname]['ssl_connection'] = False
                    continue
                
                # Make a basic HTTP request
                try:
                    response = requests.get(base_url, timeout=5)
                    status = response.status_code
                    self.results['info'].append(f"HTTP connection to {base_url}: Status {status}")
                    self.results['network_info'][hostname]['http_status'] = status
                    self.results['endpoints_tested'].append({'url': base_url, 'status': status})
                except requests.exceptions.RequestException as e:
                    self.results['errors'].append(f"HTTP connection to {base_url}: Failed ({str(e)})")
                    self.results['network_info'][hostname]['http_connection'] = False
                    continue
                
            except Exception as e:
                self.results['errors'].append(f"Network test for {base_url} failed: {str(e)}")
    
    def test_api_connection(self, api_key, api_secret, paper_trading=True, access_token=None):
        """
        Test API connection with the provided credentials.
        
        Args:
            api_key (str): API key or client ID
            api_secret (str): API secret or client secret
            paper_trading (bool): Whether to use paper trading endpoints
            access_token (str, optional): OAuth access token if available
        
        Returns:
            dict: Testing results
        """
        self.results['paper_trading'] = paper_trading
        
        # Clear any previous test results
        self.results['errors'] = []
        self.results['warnings'] = []
        self.results['info'] = []
        self.results['suggestions'] = []
        self.results['endpoints_tested'] = []
        self.results['timestamp'] = datetime.datetime.now().isoformat()
        
        # Test basic network connectivity first
        self.test_network_connectivity()
        
        # Check credentials format
        self._validate_credentials(api_key, api_secret)
        
        # Provider-specific tests
        if self.provider == 'alpaca':
            self._test_alpaca_connection(api_key, api_secret, paper_trading)
        elif self.provider == 'td_ameritrade':
            self._test_td_ameritrade_connection(api_key, api_secret, access_token)
        elif self.provider == 'schwab':
            self._test_schwab_connection(api_key, api_secret, access_token)
        else:
            self.results['errors'].append(f"Unsupported provider: {self.provider}")
            self.results['suggestions'].append("Use 'alpaca', 'td_ameritrade', or 'schwab' as the provider")
        
        # Analyze errors and provide suggestions
        self._analyze_errors()
        
        # Set final status
        if not self.results['errors']:
            self.results['status'] = 'success'
            self.results['connection'] = True
        elif len(self.results['errors']) > len(self.results['endpoints_tested']) / 2:
            self.results['status'] = 'failure'
            self.results['connection'] = False
        else:
            self.results['status'] = 'partial'
            self.results['connection'] = True
            self.results['warnings'].append("Connection succeeded but with some issues")
        
        return self.results
    
    def _validate_credentials(self, api_key, api_secret):
        """Validate the format of credentials."""
        # Check if API key is provided
        if not api_key:
            self.results['errors'].append("API key/client ID not provided")
            self.results['suggestions'].append("Provide a valid API key/client ID")
        elif len(api_key) < 8:
            self.results['warnings'].append("API key/client ID seems too short")
        
        # Check if API secret is provided for providers that need it
        if self.provider in ['alpaca', 'schwab'] and not api_secret:
            self.results['errors'].append("API secret/client secret not provided")
            self.results['suggestions'].append("Provide a valid API secret/client secret")
        elif self.provider in ['alpaca', 'schwab'] and len(api_secret) < 8:
            self.results['warnings'].append("API secret/client secret seems too short")
    
    def _test_alpaca_connection(self, api_key, api_secret, paper_trading):
        """Test connection to Alpaca API."""
        base_url = 'https://paper-api.alpaca.markets' if paper_trading else 'https://api.alpaca.markets'
        
        # Set headers for Alpaca API
        headers = {
            'APCA-API-KEY-ID': api_key,
            'APCA-API-SECRET-KEY': api_secret,
            'Content-Type': 'application/json'
        }
        
        # Test endpoints
        for endpoint_name, endpoint_path in self.endpoints['test_endpoints'].items():
            url = f"{base_url}{endpoint_path}"
            try:
                response = requests.get(url, headers=headers, timeout=10)
                status = response.status_code
                self.results['endpoints_tested'].append({
                    'name': endpoint_name,
                    'url': url,
                    'status': status,
                    'success': 200 <= status < 300
                })
                
                if status == 200:
                    self.results['info'].append(f"Successfully connected to {endpoint_name} endpoint")
                elif status == 401 or status == 403:
                    self.results['errors'].append(f"Authentication failed for {endpoint_name} endpoint: {response.text}")
                else:
                    self.results['warnings'].append(f"Unexpected response from {endpoint_name} endpoint: {status}, {response.text}")
                
            except requests.exceptions.RequestException as e:
                self.results['errors'].append(f"Connection to {endpoint_name} endpoint failed: {str(e)}")
                self.results['endpoints_tested'].append({
                    'name': endpoint_name,
                    'url': url,
                    'status': 'error',
                    'success': False,
                    'error': str(e)
                })
    
    def _test_td_ameritrade_connection(self, api_key, api_secret, access_token):
        """Test connection to TD Ameritrade API."""
        base_url = 'https://api.tdameritrade.com'
        
        # Set headers for TD Ameritrade API
        headers = {
            'Content-Type': 'application/json'
        }
        
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
        
        # Test endpoints that don't require OAuth if no access token
        endpoints_to_test = {}
        if access_token:
            endpoints_to_test = self.endpoints['test_endpoints']
        else:
            # Limited tests without authentication
            endpoints_to_test = {
                'market_hours': '/v1/marketdata/hours',
                'instruments': '/v1/instruments'
            }
        
        # Test endpoints
        for endpoint_name, endpoint_path in endpoints_to_test.items():
            # Replace placeholder in URL if needed
            if '{symbol}' in endpoint_path:
                endpoint_path = endpoint_path.replace('{symbol}', 'AAPL')
            
            # Add API key as query parameter
            separator = '?' if '?' not in endpoint_path else '&'
            url = f"{base_url}{endpoint_path}{separator}apikey={api_key}"
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                status = response.status_code
                self.results['endpoints_tested'].append({
                    'name': endpoint_name,
                    'url': url.replace(api_key, '***'),  # Hide API key in results
                    'status': status,
                    'success': 200 <= status < 300
                })
                
                if status == 200:
                    self.results['info'].append(f"Successfully connected to {endpoint_name} endpoint")
                elif status == 401 or status == 403:
                    self.results['errors'].append(f"Authentication failed for {endpoint_name} endpoint: {response.text}")
                else:
                    self.results['warnings'].append(f"Unexpected response from {endpoint_name} endpoint: {status}, {response.text}")
                
            except requests.exceptions.RequestException as e:
                self.results['errors'].append(f"Connection to {endpoint_name} endpoint failed: {str(e)}")
                self.results['endpoints_tested'].append({
                    'name': endpoint_name,
                    'url': url.replace(api_key, '***'),  # Hide API key in results
                    'status': 'error',
                    'success': False,
                    'error': str(e)
                })
    
    def _test_schwab_connection(self, client_id, client_secret, access_token):
        """Test connection to Schwab API."""
        # For Schwab, we have different endpoints for sandbox vs. production
        base_urls = {
            'production': 'https://api.schwabapi.com',
            'sandbox': 'https://sandbox.schwabapi.com',
            'developer': 'https://developer.schwab.com'
        }
        
        # Set headers
        headers = {
            'Content-Type': 'application/json'
        }
        
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
        
        # First, test OAuth endpoints
        oauth_endpoints = {
            'oauth_authorize': '/v1/oauth/authorize',
            'oauth_token': '/v1/oauth/token'
        }
        
        # For each environment (sandbox and production)
        for env_name, base_url in base_urls.items():
            for endpoint_name, endpoint_path in oauth_endpoints.items():
                url = f"{base_url}{endpoint_path}"
                
                try:
                    # Just check if endpoint exists (HEAD request)
                    response = requests.head(url, timeout=10)
                    status = response.status_code
                    
                    # For OAuth endpoints, even a 302 or 400 is somewhat expected
                    is_success = status in [200, 302, 400, 401]
                    
                    self.results['endpoints_tested'].append({
                        'name': f"{env_name}_{endpoint_name}",
                        'url': url,
                        'status': status,
                        'success': is_success
                    })
                    
                    if is_success:
                        self.results['info'].append(f"Successfully verified {endpoint_name} endpoint in {env_name}")
                    else:
                        self.results['warnings'].append(f"Unexpected response from {endpoint_name} endpoint in {env_name}: {status}")
                    
                except requests.exceptions.RequestException as e:
                    self.results['errors'].append(f"Connection to {endpoint_name} endpoint in {env_name} failed: {str(e)}")
                    self.results['endpoints_tested'].append({
                        'name': f"{env_name}_{endpoint_name}",
                        'url': url,
                        'status': 'error',
                        'success': False,
                        'error': str(e)
                    })
        
        # If we have an access token, test authenticated endpoints
        if access_token:
            # Assume we're using production endpoint
            base_url = base_urls['production']
            
            # We need to query accounts first to get account_id
            accounts_url = f"{base_url}/v1/accounts"
            account_id = None
            
            try:
                response = requests.get(accounts_url, headers=headers, timeout=10)
                status = response.status_code
                
                self.results['endpoints_tested'].append({
                    'name': 'accounts',
                    'url': accounts_url,
                    'status': status,
                    'success': 200 <= status < 300
                })
                
                if status == 200:
                    self.results['info'].append("Successfully connected to accounts endpoint")
                    try:
                        data = response.json()
                        if data and isinstance(data, list) and len(data) > 0:
                            account_id = data[0].get('accountId')
                            self.results['info'].append(f"Successfully retrieved account ID: {account_id[:4]}...{account_id[-4:]}")
                    except Exception as e:
                        self.results['warnings'].append(f"Could not parse account information: {str(e)}")
                elif status == 401 or status == 403:
                    self.results['errors'].append(f"Authentication failed for accounts endpoint: {response.text}")
                else:
                    self.results['warnings'].append(f"Unexpected response from accounts endpoint: {status}, {response.text}")
                
            except requests.exceptions.RequestException as e:
                self.results['errors'].append(f"Connection to accounts endpoint failed: {str(e)}")
                self.results['endpoints_tested'].append({
                    'name': 'accounts',
                    'url': accounts_url,
                    'status': 'error',
                    'success': False,
                    'error': str(e)
                })
            
            # Only test other endpoints if we have an account ID
            if account_id:
                # Test other endpoints
                for endpoint_name, endpoint_path in self.endpoints['test_endpoints'].items():
                    if endpoint_name in ['oauth', 'token', 'accounts']:
                        continue  # Skip endpoints we've already tested
                    
                    # Replace account_id placeholder
                    if '{account_id}' in endpoint_path:
                        endpoint_path = endpoint_path.replace('{account_id}', account_id)
                    
                    url = f"{base_url}{endpoint_path}"
                    
                    try:
                        response = requests.get(url, headers=headers, timeout=10)
                        status = response.status_code
                        
                        self.results['endpoints_tested'].append({
                            'name': endpoint_name,
                            'url': url,
                            'status': status,
                            'success': 200 <= status < 300
                        })
                        
                        if status == 200:
                            self.results['info'].append(f"Successfully connected to {endpoint_name} endpoint")
                        elif status == 401 or status == 403:
                            self.results['errors'].append(f"Authentication failed for {endpoint_name} endpoint: {response.text}")
                        else:
                            self.results['warnings'].append(f"Unexpected response from {endpoint_name} endpoint: {status}, {response.text}")
                        
                    except requests.exceptions.RequestException as e:
                        self.results['errors'].append(f"Connection to {endpoint_name} endpoint failed: {str(e)}")
                        self.results['endpoints_tested'].append({
                            'name': endpoint_name,
                            'url': url,
                            'status': 'error',
                            'success': False,
                            'error': str(e)
                        })
    
    def _analyze_errors(self):
        """Analyze errors and provide targeted suggestions."""
        if not self.results['errors'] and not self.results['warnings']:
            return
        
        # Convert all errors and warnings to lowercase for easier matching
        all_messages = [err.lower() for err in self.results['errors']] + [warn.lower() for warn in self.results['warnings']]
        error_text = ' '.join(all_messages)
        
        # Match against known error patterns
        if self.provider in self.error_patterns:
            for error_type, error_info in self.error_patterns[self.provider].items():
                if any(pattern.lower() in error_text for pattern in error_info['patterns']):
                    # If not already in suggestions, add it
                    if error_info['message'] not in self.results['suggestions']:
                        self.results['suggestions'].append(error_info['message'])
                    
                    # Add all solutions
                    for solution in error_info['solutions']:
                        if solution not in self.results['suggestions']:
                            self.results['suggestions'].append(solution)
        
        # Add general suggestions based on error count
        if len(self.results['errors']) > 3:
            self.results['suggestions'].append("There seem to be multiple issues with your API connection. Consider using simulation mode temporarily while troubleshooting.")
        
        # Add provider-specific general suggestions
        if self.provider == 'alpaca':
            self.results['suggestions'].append("Verify that you are using the correct API URLs for paper/live trading.")
        elif self.provider == 'td_ameritrade':
            self.results['suggestions'].append("TD Ameritrade's API requires OAuth authentication for most endpoints.")
        elif self.provider == 'schwab':
            self.results['suggestions'].append("Schwab's API has a complex OAuth flow. Ensure your app is registered correctly and the callback URL exactly matches.")

def get_network_info():
    """Gather basic network information."""
    info = {
        'platform': sys.platform,
        'python_version': sys.version,
        'network_tests': {}
    }
    
    # Test outbound internet connectivity
    for host in ['google.com', 'api.alpaca.markets', 'api.tdameritrade.com', 'api.schwabapi.com']:
        try:
            # Test DNS resolution
            ip = socket.gethostbyname(host)
            
            # Test HTTP connection
            response = requests.get(f"https://{host}", timeout=5)
            status = response.status_code
            
            info['network_tests'][host] = {
                'ip': ip,
                'status': status,
                'reachable': True
            }
        except (socket.gaierror, requests.exceptions.RequestException) as e:
            info['network_tests'][host] = {
                'error': str(e),
                'reachable': False
            }
    
    return info

def get_oauth_redirect_url(provider, app_domain):
    """
    Generate OAuth redirect URL based on provider and app domain.
    
    Args:
        provider (str): API provider ('td_ameritrade' or 'schwab')
        app_domain (str): Application domain
        
    Returns:
        str: Redirect URL for OAuth flow
    """
    if provider == 'td_ameritrade':
        return f"https://{app_domain}/oauth/callback"
    elif provider == 'schwab':
        return f"https://{app_domain}/oauth/callback"
    return None

def test_api_endpoints(provider, base_url, api_key=None, api_secret=None, access_token=None):
    """
    Test specific API endpoints.
    
    Args:
        provider (str): API provider
        base_url (str): Base URL for API
        api_key (str, optional): API key for authentication
        api_secret (str, optional): API secret for authentication
        access_token (str, optional): OAuth access token
        
    Returns:
        dict: Test results for each endpoint
    """
    diagnostics = APIDiagnostics(provider)
    results = {'endpoints': []}
    
    # Set up headers based on provider
    headers = {'Content-Type': 'application/json'}
    
    if provider == 'alpaca':
        headers.update({
            'APCA-API-KEY-ID': api_key,
            'APCA-API-SECRET-KEY': api_secret
        })
    elif provider in ['td_ameritrade', 'schwab'] and access_token:
        headers['Authorization'] = f'Bearer {access_token}'
    
    # Get endpoints to test
    endpoints = diagnostics.endpoints['test_endpoints']
    
    # Test each endpoint
    for name, path in endpoints.items():
        # Skip OAuth endpoints for non-OAuth tests
        if name in ['oauth', 'token'] and not access_token:
            continue
        
        # Handle placeholder replacements
        if '{symbol}' in path:
            path = path.replace('{symbol}', 'AAPL')
        
        if '{account_id}' in path:
            # Skip endpoints that need account_id if we don't have it
            if not access_token:
                continue
            else:
                # Just use a dummy ID for testing - this will fail but show if the endpoint exists
                path = path.replace('{account_id}', 'test_account')
        
        # Add API key as query param for TD Ameritrade
        if provider == 'td_ameritrade' and api_key:
            separator = '?' if '?' not in path else '&'
            path = f"{path}{separator}apikey={api_key}"
        
        url = f"{base_url}{path}"
        
        try:
            # Use HEAD request to check if endpoint exists without fetching data
            method = 'HEAD'
            response = requests.request(method, url, headers=headers, timeout=5)
            
            # If HEAD not supported, try GET
            if response.status_code == 405:  # Method Not Allowed
                method = 'GET'
                response = requests.request(method, url, headers=headers, timeout=5)
            
            results['endpoints'].append({
                'name': name,
                'url': url,
                'method': method,
                'status': response.status_code,
                'success': 200 <= response.status_code < 400  # Consider redirects successful too
            })
        except requests.exceptions.RequestException as e:
            results['endpoints'].append({
                'name': name,
                'url': url,
                'method': 'GET',
                'status': 'error',
                'error': str(e),
                'success': False
            })
    
    return results