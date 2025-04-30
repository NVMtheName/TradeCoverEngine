import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class TradeExecutor:
    """
    Executes trades on trading platforms based on strategy signals.
    """
    
    def __init__(self, api_connector, max_position_size=5000):
        """
        Initialize the trade executor.
        
        Args:
            api_connector: An instance of APIConnector for trade execution
            max_position_size (float): Maximum position size in dollars
        """
        self.api_connector = api_connector
        self.max_position_size = max_position_size
        
        logger.info(f"Initialized trade executor with max position size: ${max_position_size}")
    
    def execute_covered_call(self, symbol, quantity=None, strike_price=None, expiry_date=None):
        """
        Execute a covered call strategy by buying stock and selling a call option.
        
        Args:
            symbol (str): Stock symbol
            quantity (int, optional): Number of shares to buy
            strike_price (float, optional): Strike price for the call option
            expiry_date (str, optional): Expiry date for the call option
            
        Returns:
            dict: Trade execution result
        """
        try:
            # Validate parameters
            if not symbol:
                return {
                    'success': False,
                    'message': 'Symbol is required'
                }
            
            # Get current price if we need it
            current_price = self.api_connector.get_current_price(symbol)
            
            if not current_price:
                return {
                    'success': False,
                    'message': f"Failed to get current price for {symbol}"
                }
            
            # Determine quantity if not provided
            if not quantity:
                # Calculate based on max position size
                calculated_quantity = int(self.max_position_size / current_price)
                
                # Ensure it's a multiple of 100 (standard options contract size)
                quantity = (calculated_quantity // 100) * 100
                
                if quantity < 100:
                    return {
                        'success': False,
                        'message': f"Calculated quantity ({calculated_quantity}) is less than minimum (100)"
                    }
            
            # Check if we need to find a suitable strike/expiry
            if not strike_price or not expiry_date:
                # Get options chain
                options_chain = self.api_connector.get_options_chain(symbol)
                
                if not options_chain or not options_chain.get('calls'):
                    return {
                        'success': False,
                        'message': f"Could not get options chain for {symbol}"
                    }
                
                # Find suitable call option
                from trading_bot.strategy import CoveredCallStrategy
                strategy = CoveredCallStrategy()
                selected_call = strategy.select_covered_call(current_price, options_chain.get('calls', []))
                
                if not selected_call:
                    return {
                        'success': False,
                        'message': f"Could not find suitable call option for {symbol}"
                    }
                
                strike_price = selected_call['strike']
                expiry_date = selected_call['expiry']
            
            # Execute the trades (first stock, then option)
            stock_order_result = self._execute_stock_buy(symbol, quantity, current_price)
            
            if not stock_order_result['success']:
                return {
                    'success': False,
                    'message': f"Stock buy failed: {stock_order_result['message']}"
                }
            
            # Execute the call sell
            call_order_result = self._execute_call_sell(symbol, quantity, strike_price, expiry_date)
            
            if not call_order_result['success']:
                logger.warning(f"Call sell failed but stock buy succeeded for {symbol}. Manual intervention required.")
                return {
                    'success': False,
                    'message': f"Stock buy succeeded but call sell failed: {call_order_result['message']}",
                    'partial_success': True,
                    'stock_order_id': stock_order_result.get('order_id')
                }
            
            # Return success result
            return {
                'success': True,
                'message': f"Successfully executed covered call for {symbol}",
                'entry_price': current_price,
                'quantity': quantity,
                'strike_price': strike_price,
                'expiry_date': expiry_date,
                'stock_order_id': stock_order_result.get('order_id'),
                'call_order_id': call_order_result.get('order_id')
            }
        
        except Exception as e:
            logger.error(f"Error executing covered call for {symbol}: {str(e)}")
            return {
                'success': False,
                'message': f"Error executing covered call: {str(e)}"
            }
    
    def _execute_stock_buy(self, symbol, quantity, price=None):
        """
        Execute a stock buy order
        
        Args:
            symbol (str): Stock symbol
            quantity (int): Number of shares to buy
            price (float, optional): Limit price
            
        Returns:
            dict: Order execution result
        """
        try:
            if self.api_connector.provider == 'alpaca':
                order_details = {
                    'symbol': symbol,
                    'qty': quantity,
                    'side': 'buy',
                    'type': 'market' if not price else 'limit',
                    'time_in_force': 'day'
                }
                
                # Add limit price if provided
                if price:
                    order_details['limit_price'] = price
                
                # Execute the order
                result = self.api_connector.place_order(order_details)
                return result
            
            elif self.api_connector.provider == 'td_ameritrade':
                # Get account ID
                account_info = self.api_connector.get_account_info()
                account_id = list(account_info.keys())[0] if account_info else None
                
                if not account_id:
                    return {
                        'success': False,
                        'message': 'Could not determine account ID'
                    }
                
                # Create order for TD Ameritrade
                order_details = {
                    'accountId': account_id,
                    'orderType': 'MARKET' if not price else 'LIMIT',
                    'session': 'NORMAL',
                    'duration': 'DAY',
                    'orderStrategyType': 'SINGLE',
                    'orderLegCollection': [
                        {
                            'instruction': 'BUY',
                            'quantity': quantity,
                            'instrument': {
                                'symbol': symbol,
                                'assetType': 'EQUITY'
                            }
                        }
                    ]
                }
                
                # Add limit price if provided
                if price:
                    order_details['price'] = price
                
                # Execute the order
                result = self.api_connector.place_order(order_details)
                return result
            
            else:
                return {
                    'success': False,
                    'message': f"Unsupported API provider: {self.api_connector.provider}"
                }
                
        except Exception as e:
            logger.error(f"Error executing stock buy for {symbol}: {str(e)}")
            return {
                'success': False,
                'message': f"Error executing stock buy: {str(e)}"
            }
    
    def _execute_call_sell(self, symbol, quantity, strike_price, expiry_date):
        """
        Execute a call option sell order (covered call)
        
        Args:
            symbol (str): Stock symbol
            quantity (int): Number of shares (contracts = quantity / 100)
            strike_price (float): Option strike price
            expiry_date (str): Option expiry date
            
        Returns:
            dict: Order execution result
        """
        try:
            # Calculate number of contracts
            contracts = quantity // 100
            
            if contracts < 1:
                return {
                    'success': False,
                    'message': f"Not enough shares ({quantity}) to sell a call contract (need at least 100)"
                }
            
            if self.api_connector.provider == 'alpaca':
                # Alpaca doesn't support options yet in public API
                # This is a placeholder for when they add options support
                logger.warning("Alpaca doesn't support options in the public API. Simulating success.")
                
                return {
                    'success': True,
                    'message': 'Simulated call option sell (Alpaca doesn\'t support options yet)',
                    'order_id': f"simulated_option_{datetime.now().timestamp()}"
                }
            
            elif self.api_connector.provider == 'td_ameritrade':
                # Get account ID
                account_info = self.api_connector.get_account_info()
                account_id = list(account_info.keys())[0] if account_info else None
                
                if not account_id:
                    return {
                        'success': False,
                        'message': 'Could not determine account ID'
                    }
                
                # Format option symbol (e.g., "AAPL_062522C150")
                expiry_formatted = datetime.strptime(expiry_date, '%Y-%m-%d').strftime('%m%d%y')
                strike_formatted = str(int(strike_price * 1000)).zfill(8)
                option_symbol = f"{symbol}_{expiry_formatted}C{strike_formatted}"
                
                # Create order for TD Ameritrade
                order_details = {
                    'accountId': account_id,
                    'orderType': 'MARKET',
                    'session': 'NORMAL',
                    'duration': 'DAY',
                    'orderStrategyType': 'SINGLE',
                    'orderLegCollection': [
                        {
                            'instruction': 'SELL_TO_OPEN',
                            'quantity': contracts,
                            'instrument': {
                                'symbol': option_symbol,
                                'assetType': 'OPTION'
                            }
                        }
                    ]
                }
                
                # Execute the order
                result = self.api_connector.place_order(order_details)
                return result
            
            else:
                return {
                    'success': False,
                    'message': f"Unsupported API provider: {self.api_connector.provider}"
                }
                
        except Exception as e:
            logger.error(f"Error executing call sell for {symbol}: {str(e)}")
            return {
                'success': False,
                'message': f"Error executing call sell: {str(e)}"
            }
    
    def close_position(self, position):
        """
        Close an existing position (both stock and option)
        
        Args:
            position (dict): Position details
            
        Returns:
            dict: Position close result
        """
        try:
            symbol = position.get('symbol')
            quantity = position.get('quantity')
            call_option = position.get('call_option')
            
            if not symbol or not quantity:
                return {
                    'success': False,
                    'message': 'Symbol and quantity are required'
                }
            
            results = {
                'success': True,
                'message': f"Position for {symbol} closed successfully",
                'option_close': None,
                'stock_close': None
            }
            
            # Close option position first if it exists
            if call_option:
                option_result = self.close_option_position(symbol, call_option, quantity // 100)
                
                results['option_close'] = option_result
                
                if not option_result['success']:
                    results['success'] = False
                    results['message'] = f"Failed to close option position: {option_result['message']}"
            
            # Close stock position
            stock_result = self.close_stock_position(symbol, quantity)
            
            results['stock_close'] = stock_result
            
            if not stock_result['success']:
                results['success'] = False
                results['message'] = f"Failed to close stock position: {stock_result['message']}"
            
            return results
            
        except Exception as e:
            logger.error(f"Error closing position for {position.get('symbol')}: {str(e)}")
            return {
                'success': False,
                'message': f"Error closing position: {str(e)}"
            }
    
    def close_option_position(self, symbol, option_details, contracts):
        """
        Close an option position
        
        Args:
            symbol (str): Stock symbol
            option_details (dict): Option details including strike and expiry
            contracts (int): Number of contracts to close
            
        Returns:
            dict: Option close result
        """
        try:
            strike_price = option_details.get('strike')
            expiry_date = option_details.get('expiry')
            
            if self.api_connector.provider == 'alpaca':
                # Alpaca doesn't support options yet in public API
                logger.warning("Alpaca doesn't support options in the public API. Simulating success.")
                
                return {
                    'success': True,
                    'message': 'Simulated call option buy-to-close (Alpaca doesn\'t support options yet)',
                    'order_id': f"simulated_option_close_{datetime.now().timestamp()}"
                }
            
            elif self.api_connector.provider == 'td_ameritrade':
                # Get account ID
                account_info = self.api_connector.get_account_info()
                account_id = list(account_info.keys())[0] if account_info else None
                
                if not account_id:
                    return {
                        'success': False,
                        'message': 'Could not determine account ID'
                    }
                
                # Format option symbol
                expiry_formatted = datetime.strptime(expiry_date, '%Y-%m-%d').strftime('%m%d%y')
                strike_formatted = str(int(strike_price * 1000)).zfill(8)
                option_symbol = f"{symbol}_{expiry_formatted}C{strike_formatted}"
                
                # Create order for TD Ameritrade
                order_details = {
                    'accountId': account_id,
                    'orderType': 'MARKET',
                    'session': 'NORMAL',
                    'duration': 'DAY',
                    'orderStrategyType': 'SINGLE',
                    'orderLegCollection': [
                        {
                            'instruction': 'BUY_TO_CLOSE',
                            'quantity': contracts,
                            'instrument': {
                                'symbol': option_symbol,
                                'assetType': 'OPTION'
                            }
                        }
                    ]
                }
                
                # Execute the order
                result = self.api_connector.place_order(order_details)
                return result
            
            else:
                return {
                    'success': False,
                    'message': f"Unsupported API provider: {self.api_connector.provider}"
                }
                
        except Exception as e:
            logger.error(f"Error closing option position for {symbol}: {str(e)}")
            return {
                'success': False,
                'message': f"Error closing option position: {str(e)}"
            }
    
    def close_stock_position(self, symbol, quantity):
        """
        Close a stock position
        
        Args:
            symbol (str): Stock symbol
            quantity (int): Number of shares to sell
            
        Returns:
            dict: Stock close result
        """
        try:
            if self.api_connector.provider == 'alpaca':
                order_details = {
                    'symbol': symbol,
                    'qty': quantity,
                    'side': 'sell',
                    'type': 'market',
                    'time_in_force': 'day'
                }
                
                # Execute the order
                result = self.api_connector.place_order(order_details)
                return result
            
            elif self.api_connector.provider == 'td_ameritrade':
                # Get account ID
                account_info = self.api_connector.get_account_info()
                account_id = list(account_info.keys())[0] if account_info else None
                
                if not account_id:
                    return {
                        'success': False,
                        'message': 'Could not determine account ID'
                    }
                
                # Create order for TD Ameritrade
                order_details = {
                    'accountId': account_id,
                    'orderType': 'MARKET',
                    'session': 'NORMAL',
                    'duration': 'DAY',
                    'orderStrategyType': 'SINGLE',
                    'orderLegCollection': [
                        {
                            'instruction': 'SELL',
                            'quantity': quantity,
                            'instrument': {
                                'symbol': symbol,
                                'assetType': 'EQUITY'
                            }
                        }
                    ]
                }
                
                # Execute the order
                result = self.api_connector.place_order(order_details)
                return result
            
            else:
                return {
                    'success': False,
                    'message': f"Unsupported API provider: {self.api_connector.provider}"
                }
                
        except Exception as e:
            logger.error(f"Error closing stock position for {symbol}: {str(e)}")
            return {
                'success': False,
                'message': f"Error closing stock position: {str(e)}"
            }
    
    def roll_option(self, position, new_option_details):
        """
        Roll an option position to a new expiry/strike
        
        Args:
            position (dict): Current position details
            new_option_details (dict): New option details
            
        Returns:
            dict: Option roll result
        """
        try:
            symbol = position.get('symbol')
            quantity = position.get('quantity')
            current_option = position.get('call_option')
            
            if not symbol or not quantity or not current_option:
                return {
                    'success': False,
                    'message': 'Symbol, quantity, and current option details are required'
                }
            
            # Close current option position
            close_result = self.close_option_position(symbol, current_option, quantity // 100)
            
            if not close_result['success']:
                return {
                    'success': False,
                    'message': f"Failed to close current option position: {close_result['message']}"
                }
            
            # Open new option position
            new_sell_result = self._execute_call_sell(
                symbol, 
                quantity, 
                new_option_details.get('strike'), 
                new_option_details.get('expiry')
            )
            
            if not new_sell_result['success']:
                return {
                    'success': False,
                    'message': f"Closed old option but failed to sell new option: {new_sell_result['message']}",
                    'partial_success': True,
                    'close_order_id': close_result.get('order_id')
                }
            
            return {
                'success': True,
                'message': f"Successfully rolled option for {symbol}",
                'close_order_id': close_result.get('order_id'),
                'new_order_id': new_sell_result.get('order_id')
            }
            
        except Exception as e:
            logger.error(f"Error rolling option for {position.get('symbol')}: {str(e)}")
            return {
                'success': False,
                'message': f"Error rolling option: {str(e)}"
            }
