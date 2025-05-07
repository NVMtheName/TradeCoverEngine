"""
Collar Strategy Module

Implements the "Collar Strategy" options trading approach, which provides
protection for a long stock position by:

1. Buying a protective put to limit downside risk
2. Selling a covered call to offset the cost of the protective put

This creates a range (collar) where the strategy can profit, while limiting
both upside and downside risk.
"""

import logging
from datetime import datetime, timedelta
import math
import numpy as np
from trading_bot.strategies import OptionsStrategy

# Configure logging
logger = logging.getLogger(__name__)

class CollarStrategy(OptionsStrategy):
    """
    Implements the Collar Strategy for options trading.
    
    The Collar Strategy involves:
    1. Owning the underlying stock
    2. Buying a protective put (to limit downside)
    3. Selling a covered call (to offset put cost)
    
    This creates a 'collar' with defined upside and downside boundaries.
    """
    
    def __init__(self, risk_level='moderate', profit_target_percentage=5.0, 
                 stop_loss_percentage=3.0, options_expiry_days=30):
        """
        Initialize the collar strategy.
        
        Args:
            risk_level (str): Risk level - 'conservative', 'moderate', or 'aggressive'
            profit_target_percentage (float): Target profit percentage for early exit
            stop_loss_percentage (float): Stop loss percentage to limit downside
            options_expiry_days (int): Target days until expiration for options
        """
        super().__init__(risk_level, profit_target_percentage, stop_loss_percentage, options_expiry_days)
        logger.info(f"Initialized collar strategy with risk level: {risk_level}")
    
    def _configure_risk_parameters(self):
        """Configure strategy parameters based on the selected risk level"""
        if self.risk_level == 'conservative':
            # Conservative: Tighter collar with less risk on both sides
            self.put_delta_target = 0.30      # Target delta for put buying (closer to ATM)
            self.call_delta_target = 0.20     # Target delta for call selling (further OTM)
            self.put_strike_distance = 3.0    # % below current price for put
            self.call_strike_distance = 5.0   # % above current price for call
            self.max_net_debit_pct = 1.0      # Max net debit as % of stock price
            self.best_options_count = 1       # Consider only the most conservative collar
        
        elif self.risk_level == 'aggressive':
            # Aggressive: Wider collar with more potential profit but less protection
            self.put_delta_target = 0.15      # Target delta for put buying (further OTM)
            self.call_delta_target = 0.35     # Target delta for call selling (closer to ATM)
            self.put_strike_distance = 7.0    # % below current price for put
            self.call_strike_distance = 3.0   # % above current price for call
            self.max_net_debit_pct = 0.3      # Max net debit as % of stock price (or even a credit)
            self.best_options_count = 3       # Consider more collars
        
        else:  # moderate (default)
            # Moderate: Balanced approach
            self.put_delta_target = 0.25      # Target delta for put buying
            self.call_delta_target = 0.25     # Target delta for call selling
            self.put_strike_distance = 5.0    # % below current price for put
            self.call_strike_distance = 4.0   # % above current price for call
            self.max_net_debit_pct = 0.75     # Max net debit as % of stock price
            self.best_options_count = 2       # Consider a couple of collars
    
    def select_options(self, stock_price, options_data):
        """
        Select the best call and put options for a collar strategy.
        
        Args:
            stock_price (float): Current stock price
            options_data (dict): Available options for the stock
            
        Returns:
            dict: The selected collar (call and put options) or None if no suitable collar found
        """
        if not options_data or 'calls' not in options_data or 'puts' not in options_data:
            logger.warning("No complete options data available for collar strategy")
            return None
        
        calls = options_data['calls']
        puts = options_data['puts']
        
        if not calls or not puts:
            logger.warning("Missing call or put options for collar strategy")
            return None
        
        # Group options by expiration date to ensure both legs have same expiry
        options_by_expiry = {}
        
        # Process calls
        for call in calls:
            if 'expiry' not in call or 'strike' not in call or 'premium' not in call:
                continue
                
            expiry = call['expiry']
            if expiry not in options_by_expiry:
                options_by_expiry[expiry] = {'calls': [], 'puts': []}
            
            options_by_expiry[expiry]['calls'].append(call)
        
        # Process puts
        for put in puts:
            if 'expiry' not in put or 'strike' not in put or 'premium' not in put:
                continue
                
            expiry = put['expiry']
            if expiry not in options_by_expiry:
                options_by_expiry[expiry] = {'calls': [], 'puts': []}
            
            options_by_expiry[expiry]['puts'].append(put)
        
        # Find suitable collars
        suitable_collars = []
        
        for expiry, expiry_options in options_by_expiry.items():
            calls_list = expiry_options['calls']
            puts_list = expiry_options['puts']
            
            if not calls_list or not puts_list:
                continue
                
            days_to_expiry = self.calculate_days_to_expiry(expiry)
            
            # Only consider options with expiry close to our target
            if not self.is_within_expiry_range(days_to_expiry):
                continue
            
            # Find suitable calls (for selling)
            suitable_calls = []
            for call in calls_list:
                strike_price = call['strike']
                premium = call['premium']
                delta = abs(call.get('delta', 0.25))  # Convert to absolute value
                
                strike_percentage = ((strike_price - stock_price) / stock_price) * 100
                
                # Check if call meets our criteria
                if strike_percentage < self.call_strike_distance:
                    continue
                
                # Calculate call score
                delta_score = 1 - abs(delta - self.call_delta_target) * 2
                strike_score = 1 - abs(strike_percentage - self.call_strike_distance) / 5
                
                call['score'] = delta_score * 0.6 + strike_score * 0.4
                suitable_calls.append(call)
            
            # Find suitable puts (for buying)
            suitable_puts = []
            for put in puts_list:
                strike_price = put['strike']
                premium = put['premium']
                delta = abs(put.get('delta', 0.25))  # Convert to absolute value
                
                strike_percentage = ((stock_price - strike_price) / stock_price) * 100
                
                # Check if put meets our criteria
                if strike_percentage < self.put_strike_distance:
                    continue
                
                # Calculate put score
                delta_score = 1 - abs(delta - self.put_delta_target) * 2
                strike_score = 1 - abs(strike_percentage - self.put_strike_distance) / 5
                
                put['score'] = delta_score * 0.6 + strike_score * 0.4
                suitable_puts.append(put)
            
            # If we have both suitable calls and puts, evaluate collars
            if suitable_calls and suitable_puts:
                # Sort by score
                suitable_calls.sort(key=lambda x: x['score'], reverse=True)
                suitable_puts.sort(key=lambda x: x['score'], reverse=True)
                
                # Consider top calls and puts
                for call in suitable_calls[:3]:
                    for put in suitable_puts[:3]:
                        # Calculate net debit/credit
                        call_premium = call['premium']
                        put_premium = put['premium']
                        net_cost = put_premium - call_premium
                        net_cost_pct = (net_cost / stock_price) * 100
                        
                        # Skip collar if net debit is too high
                        if net_cost_pct > self.max_net_debit_pct:
                            continue
                        
                        # Calculate collar score
                        call_score = call['score']
                        put_score = put['score']
                        cost_score = 1 - (net_cost_pct / self.max_net_debit_pct) if self.max_net_debit_pct > 0 else 1
                        
                        # Adjust weights based on risk level
                        if self.risk_level == 'conservative':
                            collar_score = put_score * 0.5 + call_score * 0.3 + cost_score * 0.2
                        elif self.risk_level == 'aggressive':
                            collar_score = put_score * 0.3 + call_score * 0.3 + cost_score * 0.4
                        else:  # moderate
                            collar_score = put_score * 0.4 + call_score * 0.3 + cost_score * 0.3
                        
                        # Create collar object
                        collar = {
                            'call': call,
                            'put': put,
                            'expiry': expiry,
                            'days_to_expiry': days_to_expiry,
                            'net_cost': net_cost,
                            'net_cost_pct': net_cost_pct,
                            'score': collar_score
                        }
                        
                        suitable_collars.append(collar)
        
        # Sort collars by score and return the best one
        if suitable_collars:
            suitable_collars.sort(key=lambda x: x['score'], reverse=True)
            return suitable_collars[0]
        
        return None
    
    def adjust_position(self, position, current_price):
        """
        Determine if a collar position needs adjustment based on price movement.
        
        Args:
            position (dict): Position details including collar option details
            current_price (float): Current stock price
            
        Returns:
            dict: Action recommendation for the position
        """
        entry_price = position.get('entry_price', 0)
        call_strike = position.get('call_strike', 0)
        put_strike = position.get('put_strike', 0)
        call_premium = position.get('call_premium', 0)
        put_premium = position.get('put_premium', 0)
        expiry_date = position.get('option_expiry')  # Both options have same expiry
        
        # If no collar details, return None
        if not call_strike or not put_strike or not expiry_date:
            return {
                'action': 'NO_ACTION',
                'reason': 'No collar details found'
            }
        
        # Calculate metrics
        profit_loss_pct = ((current_price - entry_price) / entry_price) * 100
        days_to_expiry = self.calculate_days_to_expiry(expiry_date)
        
        # Check if we need to take action
        
        # If price is near or below put strike (downside protection activated)
        if current_price <= put_strike * 1.02:
            if days_to_expiry <= 10:
                # Close to expiration, consider closing the position to avoid assignment
                return {
                    'action': 'CLOSE_COLLAR',
                    'reason': f'Price near put strike (${put_strike}) with {days_to_expiry} days to expiry'
                }
            else:
                # Use max protection but keep position
                return {
                    'action': 'MONITOR_PUT_PROTECTION',
                    'reason': f'Price below put strike (${put_strike}), using downside protection'
                }
        
        # If price is near or above call strike (upside cap reached)
        if current_price >= call_strike * 0.98:
            if days_to_expiry <= 10:
                # Close to expiration, consider closing to avoid assignment
                return {
                    'action': 'CLOSE_COLLAR',
                    'reason': f'Price near call strike (${call_strike}) with {days_to_expiry} days to expiry'
                }
            else:
                # Consider rolling up and out for more upside
                return {
                    'action': 'ROLL_COLLAR_UP',
                    'reason': f'Price above call strike (${call_strike}), adjusting for more upside potential'
                }
        
        # If expiration is approaching
        if days_to_expiry <= 5:
            return {
                'action': 'ROLL_COLLAR_OUT',
                'reason': f'Collar near expiry ({days_to_expiry} days), rolling to new expiration'
            }
        
        # If profit target reached in the middle of the collar
        mid_point = (call_strike + put_strike) / 2
        if current_price > mid_point and profit_loss_pct >= self.profit_target_percentage:
            return {
                'action': 'CLOSE_COLLAR',
                'reason': f'Profit target reached: {profit_loss_pct:.2f}% gain exceeds {self.profit_target_percentage}% threshold'
            }
        
        # Default: no action needed
        return {
            'action': 'NO_ACTION',
            'reason': 'Collar position within parameters'
        }
    
    def generate_order_parameters(self, action, position, available_options=None):
        """
        Generate order parameters for trade execution.
        
        Args:
            action (str): The action to take (CLOSE_COLLAR, ROLL_COLLAR_OUT, etc.)
            position (dict): Position details
            available_options (dict, optional): Available options for rolling
            
        Returns:
            dict: Order parameters for the trade executor
        """
        symbol = position.get('symbol')
        quantity = position.get('quantity', 0)
        current_call_strike = position.get('call_strike', 0)
        current_put_strike = position.get('put_strike', 0)
        current_expiry = position.get('option_expiry')
        
        if action == 'CLOSE_COLLAR':
            return {
                'action': 'CLOSE_COLLAR',
                'symbol': symbol,
                'quantity': quantity,
                'call_option': f"{symbol}_C_{current_call_strike}_{current_expiry}",
                'put_option': f"{symbol}_P_{current_put_strike}_{current_expiry}",
                'order_type': 'MARKET'
            }
            
        elif action == 'MONITOR_PUT_PROTECTION':
            # Just an informational action - no actual order needed
            return {
                'action': 'MONITOR',
                'symbol': symbol,
                'quantity': quantity,
                'put_option': f"{symbol}_P_{current_put_strike}_{current_expiry}",
                'order_type': 'INFO_ONLY'
            }
            
        elif action in ('ROLL_COLLAR_OUT', 'ROLL_COLLAR_UP'):
            if not available_options or 'calls' not in available_options or 'puts' not in available_options:
                return None
                
            # Use our select_options method to find a new collar
            current_price = position.get('current_price', position.get('entry_price', 0))
            new_collar = self.select_options(current_price, available_options)
            
            if not new_collar:
                return None
                
            new_call = new_collar['call']
            new_put = new_collar['put']
            new_expiry = new_collar['expiry']
            
            # For ROLL_COLLAR_UP, ensure new call strike is higher
            if action == 'ROLL_COLLAR_UP' and new_call['strike'] <= current_call_strike:
                # Find a higher strike call if possible
                for call in available_options['calls']:
                    if call['strike'] > current_call_strike and call['expiry'] == new_expiry:
                        new_call = call
                        break
            
            return {
                'action': action,
                'symbol': symbol,
                'quantity': quantity,
                'current_call': f"{symbol}_C_{current_call_strike}_{current_expiry}",
                'current_put': f"{symbol}_P_{current_put_strike}_{current_expiry}",
                'new_call': f"{symbol}_C_{new_call['strike']}_{new_expiry}",
                'new_put': f"{symbol}_P_{new_put['strike']}_{new_expiry}",
                'order_type': 'NET_DEBIT',
                'max_debit': (new_put['premium'] - new_call['premium']) * 1.2  # Allow up to 20% more than theoretical net cost
            }
            
        return None