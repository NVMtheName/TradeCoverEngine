import os
import requests
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

class APIConnector:
    """
    Connector to trading platform APIs.
    Supports multiple providers with a common interface.
    """
    
    def __init__(self, provider='alpaca', api_key=None, api_secret=None, paper_trading=True):
        """
        Initialize the API connector.
        
        Args:
            provider (str): The API provider to use (e.g., 'alpaca', 'td_ameritrade')
            api_key (str): API key for authentication
            api_secret (str): API secret for authentication
            paper_trading (bool): Whether to use paper trading mode
        """
        self.provider = provider
        self.api_key = api_key or os.environ.get(f"{provider.upper()}_API_KEY")
        self.api_secret = api_secret or os.environ.get(f"{provider.upper()}_API_SECRET")
        self.paper_trading = paper_trading
        self.session = None
        self.base_url = None
        
        # Initialize connector based on provider
        if self.provider == 'alpaca':
            self._init_alpaca()
        elif self.provider == 'td_ameritrade':
            self._init_td_ameritrade()
        elif self.provider == 'schwab':
            self._init_schwab()
        else:
            raise ValueError(f"Unsupported API provider: {self.provider}")
    
    def _init_alpaca(self):
        """Initialize Alpaca API connection"""
        self.session = requests.Session()
        self.session.headers.update({
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.api_secret,
            'Content-Type': 'application/json'
        })
        
        # Set proper base URL based on account type
        if self.paper_trading:
            self.base_url = "https://paper-api.alpaca.markets"
            self.data_url = "https://data.alpaca.markets"
        else:
            self.base_url = "https://api.alpaca.markets"
            self.data_url = "https://data.alpaca.markets"
        
        logger.info(f"Initialized Alpaca API connector with paper trading: {self.paper_trading}")
    
    def _init_td_ameritrade(self):
        """Initialize TD Ameritrade API connection"""
        self.session = requests.Session()
        self.base_url = "https://api.tdameritrade.com/v1"
        
        # TD Ameritrade uses a different auth approach
        # This is a simplified version; in practice, OAuth flow would be needed
        self.session.params = {
            'apikey': self.api_key
        }
        
        logger.info("Initialized TD Ameritrade API connector")
        
    def _init_schwab(self):
        """Initialize Charles Schwab API connection"""
        self.session = requests.Session()
        self.base_url = "https://api.schwabapi.com/v1"
        
        # Schwab APIs typically require OAuth2 authentication
        # This is a simplified version; in practice, full OAuth2 flow would be needed
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        
        # For paper trading mode
        if self.paper_trading:
            self.base_url = "https://api-sandbox.schwabapi.com/v1"
            
        logger.info(f"Initialized Charles Schwab API connector with paper trading: {self.paper_trading}")
    
    def is_connected(self):
        """Check if the API connector is properly connected and authenticated"""
        if not self.api_key or not self.api_secret:
            logger.warning("Missing API credentials. Please configure API settings.")
            return False
            
        try:
            if self.provider == 'alpaca':
                response = self.session.get(f"{self.base_url}/v2/account")
                if response.status_code == 200:
                    return True
                else:
                    logger.warning(f"API connection failed with status code {response.status_code}: {response.text}")
                    return False
            elif self.provider == 'td_ameritrade':
                response = self.session.get(f"{self.base_url}/userprincipals")
                if response.status_code == 200:
                    return True
                else:
                    logger.warning(f"API connection failed with status code {response.status_code}: {response.text}")
                    return False
            elif self.provider == 'schwab':
                response = self.session.get(f"{self.base_url}/accounts")
                if response.status_code == 200:
                    return True
                else:
                    logger.warning(f"API connection failed with status code {response.status_code}: {response.text}")
                    return False
            return False
        except Exception as e:
            logger.error(f"Error checking API connection: {str(e)}")
            return False
    
    def get_account_info(self):
        """Get account information from the trading platform"""
        if not self.api_key or not self.api_secret:
            # Return demo/placeholder account data when no API keys are configured
            return {
                'equity': '100000.00',
                'cash': '100000.00',
                'buying_power': '200000.00',
                'daily_pl_percentage': '0.00',
                'margin_percentage': '0',
                'open_positions': 0,
                'premium_collected': '0.00',
                'account_type': 'Paper Trading',
                'status': 'ACTIVE',
                'is_pdt': False,
                'api_status': 'Not Connected'
            }
            
        try:
            if self.provider == 'alpaca':
                response = self.session.get(f"{self.base_url}/v2/account")
                if response.status_code == 200:
                    data = response.json()
                    # Format Alpaca data to match our app's format
                    return {
                        'equity': data.get('equity', '0.00'),
                        'cash': data.get('cash', '0.00'),
                        'buying_power': data.get('buying_power', '0.00'),
                        'daily_pl_percentage': data.get('portfolio_value_pct', '0.00'),
                        'margin_percentage': int(float(data.get('margin_used', '0')) / float(data.get('equity', '1')) * 100) if float(data.get('equity', '0')) > 0 else 0,
                        'open_positions': 0,  # Will be populated separately 
                        'premium_collected': '0.00',  # Custom field to be calculated
                        'account_type': 'Margin' if data.get('account_type') == 'margin' else 'Cash',
                        'status': data.get('status', 'ACTIVE'),
                        'is_pdt': data.get('pattern_day_trader', False),
                        'api_status': 'Connected'
                    }
                else:
                    logger.error(f"Failed to get account info: {response.text}")
                    return {
                        'equity': '0.00',
                        'cash': '0.00',
                        'buying_power': '0.00',
                        'daily_pl_percentage': '0.00',
                        'margin_percentage': 0,
                        'open_positions': 0,
                        'premium_collected': '0.00',
                        'account_type': 'Unknown',
                        'status': 'Unknown',
                        'is_pdt': False,
                        'api_status': 'Error'
                    }
            elif self.provider == 'td_ameritrade':
                response = self.session.get(f"{self.base_url}/accounts")
                if response.status_code == 200:
                    data = response.json()
                    # Process TD Ameritrade data
                    account = data[0] if data else {}
                    balance = account.get('securitiesAccount', {}).get('currentBalances', {})
                    
                    return {
                        'equity': str(balance.get('liquidationValue', '0.00')),
                        'cash': str(balance.get('cashBalance', '0.00')),
                        'buying_power': str(balance.get('buyingPower', '0.00')),
                        'daily_pl_percentage': '0.00',  # Not directly provided by TD Ameritrade
                        'margin_percentage': 0,  # Would need to calculate
                        'open_positions': 0,  # Will be populated separately
                        'premium_collected': '0.00',  # Custom field to be calculated
                        'account_type': account.get('securitiesAccount', {}).get('type', 'Unknown'),
                        'status': 'ACTIVE',  # TD Ameritrade doesn't provide this directly
                        'is_pdt': False,  # Would need to determine this
                        'api_status': 'Connected'
                    }
                else:
                    logger.error(f"Failed to get account info: {response.text}")
                    return {
                        'equity': '0.00',
                        'cash': '0.00',
                        'buying_power': '0.00',
                        'daily_pl_percentage': '0.00',
                        'margin_percentage': 0,
                        'open_positions': 0,
                        'premium_collected': '0.00',
                        'account_type': 'Unknown',
                        'status': 'Unknown',
                        'is_pdt': False,
                        'api_status': 'Error'
                    }
            elif self.provider == 'schwab':
                response = self.session.get(f"{self.base_url}/accounts")
                if response.status_code == 200:
                    data = response.json()
                    # Process Schwab data - note that this is a simplified version
                    # based on expected API structure, which may need adjustment
                    account = data.get('accounts', [])[0] if data.get('accounts', []) else {}
                    balance = account.get('balance', {})
                    
                    return {
                        'equity': str(balance.get('equityValue', '0.00')),
                        'cash': str(balance.get('cashBalance', '0.00')),
                        'buying_power': str(balance.get('marginBuyingPower', '0.00')),
                        'daily_pl_percentage': str(balance.get('dailyProfitLossPercentage', '0.00')),
                        'margin_percentage': int(float(balance.get('marginUsed', '0')) / float(balance.get('equityValue', '1')) * 100) if float(balance.get('equityValue', '0')) > 0 else 0,
                        'open_positions': account.get('openPositionsCount', 0),
                        'premium_collected': str(account.get('optionsPremiumCollected', '0.00')),
                        'account_type': account.get('type', 'Unknown'),
                        'status': account.get('status', 'ACTIVE'),
                        'is_pdt': account.get('isPatternDayTrader', False),
                        'api_status': 'Connected'
                    }
                else:
                    logger.error(f"Failed to get account info: {response.text}")
                    return {
                        'equity': '0.00',
                        'cash': '0.00',
                        'buying_power': '0.00',
                        'daily_pl_percentage': '0.00',
                        'margin_percentage': 0,
                        'open_positions': 0,
                        'premium_collected': '0.00',
                        'account_type': 'Unknown',
                        'status': 'Unknown',
                        'is_pdt': False,
                        'api_status': 'Error'
                    }
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return {
                'equity': '0.00',
                'cash': '0.00',
                'buying_power': '0.00',
                'daily_pl_percentage': '0.00',
                'margin_percentage': 0,
                'open_positions': 0,
                'premium_collected': '0.00',
                'account_type': 'Unknown',
                'status': 'Unknown',
                'is_pdt': False,
                'api_status': 'Error'
            }
    
    def get_stock_data(self, symbol, days=30):
        """
        Get historical stock data for a symbol
        
        Args:
            symbol (str): Stock symbol
            days (int): Number of days of historical data
            
        Returns:
            dict: Historical price data
        """
        try:
            if self.provider == 'alpaca':
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                params = {
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d'),
                    'timeframe': '1D'
                }
                
                response = self.session.get(
                    f"{self.data_url}/v2/stocks/{symbol}/bars",
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'dates': [bar['t'] for bar in data.get('bars', [])],
                        'prices': [bar['c'] for bar in data.get('bars', [])],
                        'volumes': [bar['v'] for bar in data.get('bars', [])]
                    }
                else:
                    logger.error(f"Failed to get stock data for {symbol}: {response.text}")
                    return {'dates': [], 'prices': [], 'volumes': []}
                    
            elif self.provider == 'td_ameritrade':
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                params = {
                    'periodType': 'day',
                    'frequencyType': 'daily',
                    'frequency': '1',
                    'startDate': int(start_date.timestamp() * 1000),
                    'endDate': int(end_date.timestamp() * 1000),
                    'needExtendedHoursData': 'false'
                }
                
                response = self.session.get(
                    f"{self.base_url}/marketdata/{symbol}/pricehistory",
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    candles = data.get('candles', [])
                    return {
                        'dates': [candle['datetime'] for candle in candles],
                        'prices': [candle['close'] for candle in candles],
                        'volumes': [candle['volume'] for candle in candles]
                    }
                else:
                    logger.error(f"Failed to get stock data for {symbol}: {response.text}")
                    return {'dates': [], 'prices': [], 'volumes': []}
                    
            elif self.provider == 'schwab':
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # Format dates as expected by Schwab API
                formatted_start = start_date.strftime('%Y-%m-%d')
                formatted_end = end_date.strftime('%Y-%m-%d')
                
                params = {
                    'symbol': symbol,
                    'startDate': formatted_start,
                    'endDate': formatted_end,
                    'interval': 'daily'
                }
                
                response = self.session.get(
                    f"{self.base_url}/market/history",
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    bars = data.get('bars', [])
                    return {
                        'dates': [bar.get('date') for bar in bars],
                        'prices': [bar.get('close') for bar in bars],
                        'volumes': [bar.get('volume') for bar in bars]
                    }
                else:
                    logger.error(f"Failed to get stock data for {symbol}: {response.text}")
                    return {'dates': [], 'prices': [], 'volumes': []}
        
        except Exception as e:
            logger.error(f"Error getting stock data for {symbol}: {str(e)}")
            return {'dates': [], 'prices': [], 'volumes': []}
    
    def get_options_chain(self, symbol, expiry_date=None):
        """
        Get options chain data for a stock
        
        Args:
            symbol (str): Stock symbol
            expiry_date (str, optional): Options expiry date (YYYY-MM-DD)
            
        Returns:
            dict: Options chain data
        """
        try:
            if self.provider == 'alpaca':
                # Alpaca doesn't have a direct options chain API
                # This is a placeholder for when they add options support
                # For now, return empty data
                return {
                    'calls': [],
                    'puts': []
                }
                
            elif self.provider == 'td_ameritrade':
                params = {
                    'symbol': symbol,
                    'strikeCount': 10,
                    'includeQuotes': 'TRUE',
                    'strategy': 'SINGLE',
                    'range': 'NTM',  # Near the money
                    'fromDate': expiry_date,
                    'toDate': expiry_date
                }
                
                response = self.session.get(
                    f"{self.base_url}/marketdata/chains",
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    calls = []
                    puts = []
                    
                    # Process call options
                    for expiry in data.get('callExpDateMap', {}).values():
                        for strikes in expiry.values():
                            for option in strikes:
                                calls.append({
                                    'strike': option['strikePrice'],
                                    'expiry': option['expirationDate'],
                                    'bid': option['bid'],
                                    'ask': option['ask'],
                                    'delta': option.get('delta', 0),
                                    'theta': option.get('theta', 0),
                                    'iv': option.get('volatility', 0)
                                })
                    
                    # Process put options
                    for expiry in data.get('putExpDateMap', {}).values():
                        for strikes in expiry.values():
                            for option in strikes:
                                puts.append({
                                    'strike': option['strikePrice'],
                                    'expiry': option['expirationDate'],
                                    'bid': option['bid'],
                                    'ask': option['ask'],
                                    'delta': option.get('delta', 0),
                                    'theta': option.get('theta', 0),
                                    'iv': option.get('volatility', 0)
                                })
                    
                    return {
                        'calls': calls,
                        'puts': puts
                    }
                else:
                    logger.error(f"Failed to get options chain for {symbol}: {response.text}")
                    return {'calls': [], 'puts': []}
                    
            elif self.provider == 'schwab':
                # Set a default expiry date if none provided
                if not expiry_date:
                    future_date = datetime.now() + timedelta(days=30)  # Default to ~1 month out
                    expiry_date = future_date.strftime('%Y-%m-%d')
                
                params = {
                    'symbol': symbol,
                    'expirationDate': expiry_date,
                    'strikeCount': 10  # Number of strikes above and below current price
                }
                
                response = self.session.get(
                    f"{self.base_url}/market/options/chain",
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    calls = []
                    puts = []
                    
                    # Process call options
                    for option in data.get('callOptions', []):
                        calls.append({
                            'strike': option.get('strikePrice'),
                            'expiry': option.get('expirationDate'),
                            'bid': option.get('bidPrice'),
                            'ask': option.get('askPrice'),
                            'delta': option.get('delta', 0),
                            'theta': option.get('theta', 0),
                            'iv': option.get('impliedVolatility', 0)
                        })
                    
                    # Process put options
                    for option in data.get('putOptions', []):
                        puts.append({
                            'strike': option.get('strikePrice'),
                            'expiry': option.get('expirationDate'),
                            'bid': option.get('bidPrice'),
                            'ask': option.get('askPrice'),
                            'delta': option.get('delta', 0),
                            'theta': option.get('theta', 0),
                            'iv': option.get('impliedVolatility', 0)
                        })
                    
                    return {
                        'calls': calls,
                        'puts': puts
                    }
                else:
                    logger.error(f"Failed to get options chain for {symbol}: {response.text}")
                    return {'calls': [], 'puts': []}
        
        except Exception as e:
            logger.error(f"Error getting options chain for {symbol}: {str(e)}")
            return {'calls': [], 'puts': []}
    
    def get_current_price(self, symbol):
        """
        Get the current price of a stock
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            float: Current price or None if error
        """
        try:
            if self.provider == 'alpaca':
                response = self.session.get(
                    f"{self.data_url}/v2/stocks/{symbol}/quotes/latest"
                )
                
                if response.status_code == 200:
                    quote = response.json().get('quote', {})
                    return (quote.get('ap') + quote.get('bp')) / 2  # Midpoint of ask and bid
                else:
                    logger.error(f"Failed to get current price for {symbol}: {response.text}")
                    return None
                    
            elif self.provider == 'td_ameritrade':
                response = self.session.get(
                    f"{self.base_url}/marketdata/{symbol}/quotes"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get(symbol, {}).get('lastPrice')
                else:
                    logger.error(f"Failed to get current price for {symbol}: {response.text}")
                    return None
                    
            elif self.provider == 'schwab':
                response = self.session.get(
                    f"{self.base_url}/market/quotes",
                    params={'symbols': symbol}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    quote = data.get('quotes', {}).get(symbol, {})
                    return quote.get('lastPrice')
                else:
                    logger.error(f"Failed to get current price for {symbol}: {response.text}")
                    return None
        
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {str(e)}")
            return None
    
    def place_order(self, order_details):
        """
        Place an order on the trading platform
        
        Args:
            order_details (dict): Order details
            
        Returns:
            dict: Order response with success status
        """
        try:
            if self.provider == 'alpaca':
                response = self.session.post(
                    f"{self.base_url}/v2/orders",
                    json=order_details
                )
                
                if response.status_code in (200, 201):
                    return {
                        'success': True,
                        'order_id': response.json().get('id'),
                        'message': 'Order placed successfully'
                    }
                else:
                    logger.error(f"Failed to place order: {response.text}")
                    return {
                        'success': False,
                        'message': response.text
                    }
                    
            elif self.provider == 'td_ameritrade':
                response = self.session.post(
                    f"{self.base_url}/accounts/{order_details.get('accountId')}/orders",
                    json=order_details
                )
                
                if response.status_code in (200, 201):
                    return {
                        'success': True,
                        'order_id': response.headers.get('Location', '').split('/')[-1],
                        'message': 'Order placed successfully'
                    }
                else:
                    logger.error(f"Failed to place order: {response.text}")
                    return {
                        'success': False,
                        'message': response.text
                    }
                    
            elif self.provider == 'schwab':
                response = self.session.post(
                    f"{self.base_url}/trading/orders",
                    json=order_details
                )
                
                if response.status_code in (200, 201):
                    return {
                        'success': True,
                        'order_id': response.json().get('orderId'),
                        'message': 'Order placed successfully'
                    }
                else:
                    logger.error(f"Failed to place order: {response.text}")
                    return {
                        'success': False,
                        'message': response.text
                    }
        
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_open_positions(self):
        """
        Get open positions from the trading platform
        
        Returns:
            list: Open positions
        """
        try:
            if self.provider == 'alpaca':
                response = self.session.get(f"{self.base_url}/v2/positions")
                
                if response.status_code == 200:
                    positions = response.json()
                    return [
                        {
                            'symbol': position['symbol'],
                            'quantity': int(position['qty']),
                            'avg_entry_price': float(position['avg_entry_price']),
                            'current_price': float(position['current_price']),
                            'market_value': float(position['market_value']),
                            'unrealized_pl': float(position['unrealized_pl']),
                            'unrealized_plpc': float(position['unrealized_plpc']) * 100  # Convert to percentage
                        }
                        for position in positions
                    ]
                else:
                    logger.error(f"Failed to get positions: {response.text}")
                    return []
                    
            elif self.provider == 'td_ameritrade':
                # Get account ID from account info
                account_info = self.get_account_info()
                if not account_info:
                    return []
                
                account_id = list(account_info.keys())[0]
                
                response = self.session.get(
                    f"{self.base_url}/accounts/{account_id}/positions"
                )
                
                if response.status_code == 200:
                    positions_data = response.json()
                    positions = []
                    
                    for position in positions_data.get('securitiesAccount', {}).get('positions', []):
                        instrument = position.get('instrument', {})
                        if instrument.get('assetType') == 'EQUITY':
                            positions.append({
                                'symbol': instrument.get('symbol'),
                                'quantity': position.get('longQuantity', 0),
                                'avg_entry_price': position.get('averagePrice', 0),
                                'current_price': position.get('marketValue', 0) / position.get('longQuantity', 1),
                                'market_value': position.get('marketValue', 0),
                                'unrealized_pl': position.get('currentDayProfitLoss', 0),
                                'unrealized_plpc': position.get('currentDayProfitLossPercentage', 0)
                            })
                    
                    return positions
                else:
                    logger.error(f"Failed to get positions: {response.text}")
                    return []
                    
            elif self.provider == 'schwab':
                # Get account ID from account info
                account_info = self.get_account_info()
                if not account_info:
                    return []
                    
                account_id = account_info.get('account_id')
                
                response = self.session.get(
                    f"{self.base_url}/accounts/{account_id}/positions"
                )
                
                if response.status_code == 200:
                    positions_data = response.json()
                    positions = []
                    
                    for position in positions_data.get('positions', []):
                        if position.get('assetType') == 'EQUITY':
                            positions.append({
                                'symbol': position.get('symbol'),
                                'quantity': position.get('quantity', 0),
                                'avg_entry_price': position.get('costBasis', 0) / position.get('quantity', 1),
                                'current_price': position.get('marketPrice', 0),
                                'market_value': position.get('marketValue', 0),
                                'unrealized_pl': position.get('unrealizedPL', 0),
                                'unrealized_plpc': position.get('unrealizedPLPercent', 0) * 100  # Convert to percentage
                            })
                    
                    return positions
                else:
                    logger.error(f"Failed to get positions: {response.text}")
                    return []
        
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            return []
    
    def get_equity_history(self, days=30):
        """
        Get account equity history
        
        Args:
            days (int): Number of days of history
            
        Returns:
            dict: Dates and equity values
        """
        try:
            if self.provider == 'alpaca':
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                params = {
                    'period': '1D',
                    'timeframe': 'D',
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d')
                }
                
                response = self.session.get(
                    f"{self.base_url}/v2/account/portfolio/history",
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'dates': [datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d') for timestamp in data.get('timestamp', [])],
                        'equity': data.get('equity', [])
                    }
                else:
                    logger.error(f"Failed to get equity history: {response.text}")
                    # Return mock data for demonstration
                    return self._generate_mock_equity_history(days)
                    
            elif self.provider == 'td_ameritrade':
                # TD Ameritrade doesn't have a direct equity history endpoint
                # This would require pulling transactions and calculating manually
                # Return mock data for demonstration
                return self._generate_mock_equity_history(days)
        
        except Exception as e:
            logger.error(f"Error getting equity history: {str(e)}")
            return {
                'dates': [],
                'equity': []
            }
    
    def _generate_mock_equity_history(self, days):
        """Generate mock equity history data for demonstration"""
        end_date = datetime.now()
        dates = [(end_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days, -1, -1)]
        
        # Start with a base value and add some random variations
        base_equity = 10000.0
        equity = [base_equity]
        
        for i in range(1, len(dates)):
            # Add some random daily variation (-1% to +1%)
            daily_change = equity[-1] * (1 + (np.random.random() * 0.02 - 0.01))
            equity.append(daily_change)
        
        return {
            'dates': dates,
            'equity': equity
        }
    
    def get_monthly_returns(self, months=12):
        """
        Get monthly returns data
        
        Args:
            months (int): Number of months of returns data
            
        Returns:
            dict: Month labels and return percentages
        """
        try:
            # Calculate monthly returns based on equity history
            # Get daily equity for a longer period
            equity_history = self.get_equity_history(days=months * 30)
            
            # If we don't have data, return empty
            if not equity_history.get('dates') or not equity_history.get('equity'):
                return {
                    'months': [],
                    'returns': []
                }
            
            # Convert to DataFrame for easier processing
            df = pd.DataFrame({
                'date': pd.to_datetime(equity_history['dates']),
                'equity': equity_history['equity']
            })
            
            # Set date as index and resample to monthly
            df.set_index('date', inplace=True)
            monthly = df.resample('M').last()
            
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
