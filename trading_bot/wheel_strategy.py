"""
Wheel Strategy Module

Implements the "Wheel Strategy" options trading approach, which is a systematic 
strategy for generating income by cycling through different options positions:

1. Cash-secured put selling
2. Covered call selling (if assigned on puts)
3. Repeat

This strategy is designed for investors who are willing to own the underlying stock
but also want to generate income through option premiums.
"""

import logging
from datetime import datetime, timedelta
import math
import numpy as np
from trading_bot.strategies import OptionsStrategy

# Configure logging
logger = logging.getLogger(__name__)

class WheelStrategy(OptionsStrategy):
    """
    Implements the Wheel Strategy for options trading.
    
    The Wheel Strategy (also known as "Triple Income Strategy") combines:
    1. Cash-secured put selling
    2. Covered call selling (if put is assigned)
    3. Rinse and repeat
    """
    
    def __init__(self, risk_level='moderate', profit_target_percentage=5.0, 
                 stop_loss_percentage=3.0, options_expiry_days=30):
        """
        Initialize the wheel strategy.
        
        Args:
            risk_level (str): Risk level - 'conservative', 'moderate', or 'aggressive'
            profit_target_percentage (float): Target profit percentage for early exit
            stop_loss_percentage (float): Stop loss percentage to limit downside
            options_expiry_days (int): Target days until expiration for options
        """
        super().__init__(risk_level, profit_target_percentage, stop_loss_percentage, options_expiry_days)
        logger.info(f"Initialized wheel strategy with risk level: {risk_level}")
        self.current_phase = "PUT_SELLING"  # Start with put selling phase
    
    def _configure_risk_parameters(self):
        """Configure strategy parameters based on the selected risk level"""
        if self.risk_level == 'conservative':
            # Conservative: Sell puts farther OTM with lower premium but higher probability
            self.put_delta_target = 0.20      # Target delta for put selling (farther OTM)
            self.call_delta_target = 0.20     # Target delta for call selling (farther OTM)
            self.premium_min_percentage = 0.5  # Minimum premium as % of stock price
            self.put_strike_distance = 5.0    # % below current price for put
            self.call_strike_distance = 5.0   # % above purchase price for call
            self.best_options_count = 1       # Consider only the most conservative option
        
        elif self.risk_level == 'aggressive':
            # Aggressive: Sell puts closer to ATM with higher premium but higher assignment risk
            self.put_delta_target = 0.40      # Target delta for put selling (closer to ATM)
            self.call_delta_target = 0.40     # Target delta for call selling (closer to ATM)
            self.premium_min_percentage = 1.5  # Minimum premium as % of stock price
            self.put_strike_distance = 2.0    # % below current price for put
            self.call_strike_distance = 2.0   # % above purchase price for call
            self.best_options_count = 3       # Consider more options
        
        else:  # moderate (default)
            # Moderate: Balanced approach
            self.put_delta_target = 0.30      # Target delta for put selling
            self.call_delta_target = 0.30     # Target delta for call selling
            self.premium_min_percentage = 1.0  # Minimum premium as % of stock price
            self.put_strike_distance = 3.0    # % below current price for put
            self.call_strike_distance = 3.0   # % above purchase price for call
            self.best_options_count = 2       # Consider a couple of options
    
    def select_options(self, stock_price, options_data):
        """
        Select the best option for current phase of the wheel strategy.
        
        Args:
            stock_price (float): Current stock price
            options_data (dict): Available options for the stock
            
        Returns:
            dict: The selected option or None if no suitable option found
        """
        if not options_data:
            return None
            
        if self.current_phase == "PUT_SELLING":
            if 'puts' not in options_data:
                return None
            return self.select_cash_secured_put(stock_price, options_data['puts'])
        elif self.current_phase == "CALL_SELLING":
            if 'calls' not in options_data:
                return None
            return self.select_covered_call(stock_price, options_data['calls'])
            
        return None
    
    def select_cash_secured_put(self, stock_price, put_options):
        """
        Select the best put option for the cash-secured put phase.
        
        Args:
            stock_price (float): Current stock price
            put_options (list): Available put options for the stock
            
        Returns:
            dict: The selected put option or None if no suitable option found
        """
        if not put_options:
            logger.warning("No put options available for selection")
            return None
        
        suitable_options = []
        
        for option in put_options:
            # Skip options that don't meet basic criteria
            if 'strike' not in option or 'premium' not in option:
                continue
            
            strike_price = option['strike']
            premium = option['premium']
            days_to_expiry = option.get('days_to_expiry', 30)
            
            # Calculate metrics
            strike_percentage = ((stock_price - strike_price) / stock_price) * 100
            premium_percentage = (premium / stock_price) * 100
            
            # Check if option meets basic criteria
            if (strike_percentage < self.put_strike_distance or 
                premium_percentage < self.premium_min_percentage):
                continue
            
            # Check expiry is within our target range
            if not self.is_within_expiry_range(days_to_expiry):
                # Only skip if we have other good options
                if len(suitable_options) >= self.best_options_count:
                    continue
            
            # Calculate a score for this option based on our strategy parameters
            delta_score = 1 - abs(option.get('delta', 0.3) - self.put_delta_target) * 2
            premium_score = premium_percentage / 2  # Scale premium percentage
            expiry_score = 1 - abs(days_to_expiry - self.options_expiry_days) / 30
            
            # Adjust weights based on risk level
            if self.risk_level == 'conservative':
                option['score'] = delta_score * 0.5 + premium_score * 0.2 + expiry_score * 0.3
            elif self.risk_level == 'aggressive':
                option['score'] = delta_score * 0.2 + premium_score * 0.6 + expiry_score * 0.2
            else:  # moderate
                option['score'] = delta_score * 0.3 + premium_score * 0.4 + expiry_score * 0.3
            
            suitable_options.append(option)
        
        # Sort by score (highest first)
        suitable_options.sort(key=lambda x: x['score'], reverse=True)
        
        # Return the highest-scoring option or None if no suitable options
        return suitable_options[0] if suitable_options else None
    
    def select_covered_call(self, stock_price, call_options):
        """
        Select the best call option for the covered call phase.
        
        Args:
            stock_price (float): Current stock price
            call_options (list): Available call options for the stock
            
        Returns:
            dict: The selected call option or None if no suitable option found
        """
        if not call_options:
            logger.warning("No call options available for selection")
            return None
        
        suitable_options = []
        
        for option in call_options:
            # Skip options that don't meet basic criteria
            if 'strike' not in option or 'premium' not in option:
                continue
            
            strike_price = option['strike']
            premium = option['premium']
            days_to_expiry = option.get('days_to_expiry', 30)
            
            # Calculate metrics
            strike_percentage = ((strike_price - stock_price) / stock_price) * 100
            premium_percentage = (premium / stock_price) * 100
            
            # Check if option meets basic criteria
            if (strike_percentage < self.call_strike_distance or 
                premium_percentage < self.premium_min_percentage):
                continue
            
            # Check expiry is within our target range
            if not self.is_within_expiry_range(days_to_expiry):
                # Only skip if we have other good options
                if len(suitable_options) >= self.best_options_count:
                    continue
            
            # Calculate a score for this option based on our strategy parameters
            delta_score = 1 - abs(option.get('delta', 0.3) - self.call_delta_target) * 2
            premium_score = premium_percentage / 2  # Scale premium percentage
            expiry_score = 1 - abs(days_to_expiry - self.options_expiry_days) / 30
            
            # Adjust weights based on risk level
            if self.risk_level == 'conservative':
                option['score'] = delta_score * 0.5 + premium_score * 0.2 + expiry_score * 0.3
            elif self.risk_level == 'aggressive':
                option['score'] = delta_score * 0.2 + premium_score * 0.6 + expiry_score * 0.2
            else:  # moderate
                option['score'] = delta_score * 0.3 + premium_score * 0.4 + expiry_score * 0.3
            
            suitable_options.append(option)
        
        # Sort by score (highest first)
        suitable_options.sort(key=lambda x: x['score'], reverse=True)
        
        # Return the highest-scoring option or None if no suitable options
        return suitable_options[0] if suitable_options else None
    
    def adjust_position(self, position, current_price):
        """
        Determine if a position needs adjustment based on price movement.
        
        Args:
            position (dict): Position details including option details and entry price
            current_price (float): Current stock price
            
        Returns:
            dict: Action recommendation for the position
        """
        # Determine current phase based on position details
        if 'put_strike' in position and position.get('put_strike') > 0:
            self.current_phase = "PUT_SELLING"
            return self._adjust_put_position(position, current_price)
            
        elif 'call_strike' in position and position.get('call_strike') > 0:
            self.current_phase = "CALL_SELLING"
            return self._adjust_call_position(position, current_price)
            
        # Default if we can't determine the phase
        return {
            'action': 'NO_ACTION',
            'reason': 'Unable to determine position type for wheel strategy'
        }
    
    def _adjust_put_position(self, position, current_price):
        """
        Determine if a put position needs adjustment.
        
        Args:
            position (dict): Put position details
            current_price (float): Current stock price
            
        Returns:
            dict: Action recommendation for the put position
        """
        strike_price = position.get('put_strike', 0)
        premium = position.get('put_premium', 0)
        expiry_date = position.get('put_expiry')
        
        # If no put details, return None
        if not strike_price or not premium or not expiry_date:
            return {
                'action': 'NO_ACTION',
                'reason': 'No put option details found'
            }
        
        # Calculate metrics
        days_to_expiry = self.calculate_days_to_expiry(expiry_date)
        profit_percentage = (premium / strike_price) * 100
        
        # Check if we need to take action
        
        # If stock price falls significantly below strike
        if current_price <= strike_price * (1 - self.stop_loss_percentage/100):
            # Stop loss triggered
            return {
                'action': 'BUY_TO_CLOSE_PUT',
                'reason': f'Stop loss triggered: price fell {round((strike_price - current_price) / strike_price * 100, 2)}% below strike'
            }
        
        # If profit target reached (premium decay)
        if days_to_expiry < self.options_expiry_days * 0.3 and profit_percentage >= self.profit_target_percentage * 0.8:
            # Early profit taking
            return {
                'action': 'BUY_TO_CLOSE_PUT',
                'reason': f'Profit target nearly reached with {days_to_expiry} days remaining'
            }
        
        # If expiry is very close and out of the money
        if days_to_expiry <= 5 and current_price > strike_price * 1.02:
            # Close to expiration and price above strike
            return {
                'action': 'ROLL_OUT_PUT',
                'reason': f'Option near expiry ({days_to_expiry} days) and safely out of the money'
            }
        
        # If about to be assigned
        if current_price < strike_price * 0.98 and days_to_expiry <= 7:
            # Price below strike, likely assignment
            return {
                'action': 'PREPARE_FOR_ASSIGNMENT',
                'reason': f'Price below strike by > 2%, preparing for assignment'
            }
        
        # Default: no action needed
        return {
            'action': 'NO_ACTION',
            'reason': 'Put position within parameters'
        }
    
    def _adjust_call_position(self, position, current_price):
        """
        Determine if a call position needs adjustment.
        
        Args:
            position (dict): Call position details
            current_price (float): Current stock price
            
        Returns:
            dict: Action recommendation for the call position
        """
        entry_price = position.get('entry_price', 0)
        strike_price = position.get('call_strike', 0)
        premium = position.get('call_premium', 0)
        expiry_date = position.get('call_expiry')
        
        # If no covered call details, return None
        if not strike_price or not premium or not expiry_date:
            return {
                'action': 'NO_ACTION',
                'reason': 'No covered call details found'
            }
        
        # Calculate metrics
        profit_loss_pct = ((current_price - entry_price) / entry_price) * 100
        days_to_expiry = self.calculate_days_to_expiry(expiry_date)
        
        # Check if we need to take action
        if profit_loss_pct <= -self.stop_loss_percentage:
            # Stop loss triggered
            return {
                'action': 'BUY_TO_CLOSE_CALL',
                'reason': f'Stop loss triggered: {profit_loss_pct:.2f}% loss exceeds {self.stop_loss_percentage}% threshold'
            }
        
        if profit_loss_pct >= self.profit_target_percentage:
            # Profit target reached
            return {
                'action': 'BUY_TO_CLOSE_CALL',
                'reason': f'Profit target reached: {profit_loss_pct:.2f}% gain exceeds {self.profit_target_percentage}% threshold'
            }
        
        if days_to_expiry <= 5 and current_price < strike_price * 0.98:
            # Close to expiration and price below strike
            return {
                'action': 'ROLL_OUT_CALL',
                'reason': f'Option near expiry ({days_to_expiry} days) and price below strike'
            }
        
        if current_price > strike_price * 1.02 and days_to_expiry > 7:
            # Price above strike, risk of assignment
            return {
                'action': 'ROLL_UP_AND_OUT_CALL',
                'reason': f'Stock price above strike by > 2%, risk of early assignment'
            }
        
        # Default: no action needed
        return {
            'action': 'NO_ACTION',
            'reason': 'Call position within parameters'
        }
    
    def generate_order_parameters(self, action, position, available_options=None):
        """
        Generate order parameters for trade execution.
        
        Args:
            action (str): The action to take
            position (dict): Position details
            available_options (list, optional): Available options for rolling
            
        Returns:
            dict: Order parameters for the trade executor
        """
        symbol = position.get('symbol')
        quantity = position.get('quantity', 0)
        
        # Handle PUT_SELLING phase actions
        if action == 'BUY_TO_CLOSE_PUT':
            put_strike = position.get('put_strike', 0)
            put_expiry = position.get('put_expiry')
            
            return {
                'action': 'BUY_TO_CLOSE',
                'symbol': symbol,
                'option_symbol': f"{symbol}_P_{put_strike}_{put_expiry}",
                'quantity': quantity,
                'order_type': 'MARKET'
            }
            
        elif action == 'ROLL_OUT_PUT':
            put_strike = position.get('put_strike', 0)
            put_expiry = position.get('put_expiry')
            
            if not available_options:
                return None
                
            # Filter to find suitable options for rolling puts
            filtered_options = []
            
            for option in available_options:
                if option.get('option_type', '').upper() != 'PUT':
                    continue
                    
                new_strike = option.get('strike', 0)
                new_days = option.get('days_to_expiry', 0)
                
                # For ROLL_OUT_PUT, keep same strike but longer expiry
                if (new_strike == put_strike and 
                    new_days > 21 and new_days < 45):
                    filtered_options.append(option)
            
            # Select best option based on strategy
            selected_option = self.select_cash_secured_put(0, filtered_options)
            
            if not selected_option:
                return None
                
            return {
                'action': 'ROLL_PUT',
                'symbol': symbol,
                'quantity': quantity,
                'current_option': f"{symbol}_P_{put_strike}_{put_expiry}",
                'new_option': f"{symbol}_P_{selected_option['strike']}_{selected_option['expiry']}",
                'order_type': 'NET_CREDIT',
                'min_credit': selected_option.get('premium', 0) * 0.3  # Require at least 30% of new premium as credit
            }
            
        elif action == 'PREPARE_FOR_ASSIGNMENT':
            # Just an informational action - no actual order needed
            return {
                'action': 'PREPARE_FOR_ASSIGNMENT',
                'symbol': symbol,
                'quantity': quantity,
                'order_type': 'INFO_ONLY',
                'next_phase': 'CALL_SELLING'  # Move to covered call selling after assignment
            }
            
        # Handle CALL_SELLING phase actions
        elif action == 'BUY_TO_CLOSE_CALL':
            call_strike = position.get('call_strike', 0)
            call_expiry = position.get('call_expiry')
            
            return {
                'action': 'BUY_TO_CLOSE',
                'symbol': symbol,
                'option_symbol': f"{symbol}_C_{call_strike}_{call_expiry}",
                'quantity': quantity,
                'order_type': 'MARKET'
            }
            
        elif action in ('ROLL_OUT_CALL', 'ROLL_UP_AND_OUT_CALL'):
            call_strike = position.get('call_strike', 0)
            call_expiry = position.get('call_expiry')
            
            if not available_options:
                return None
                
            # Filter to find suitable options for rolling calls
            filtered_options = []
            
            for option in available_options:
                if option.get('option_type', '').upper() != 'CALL':
                    continue
                    
                new_strike = option.get('strike', 0)
                new_days = option.get('days_to_expiry', 0)
                
                # For ROLL_OUT_CALL, keep same strike but longer expiry
                if action == 'ROLL_OUT_CALL':
                    if (new_strike == call_strike and 
                        new_days > 21 and new_days < 45):
                        filtered_options.append(option)
                
                # For ROLL_UP_AND_OUT_CALL, increase strike and expiry
                elif action == 'ROLL_UP_AND_OUT_CALL':
                    if (new_strike > call_strike and 
                        new_days > 21 and new_days < 45):
                        filtered_options.append(option)
            
            # Select best option based on strategy
            selected_option = self.select_covered_call(0, filtered_options)
            
            if not selected_option:
                return None
                
            return {
                'action': 'ROLL_CALL',
                'symbol': symbol,
                'quantity': quantity,
                'current_option': f"{symbol}_C_{call_strike}_{call_expiry}",
                'new_option': f"{symbol}_C_{selected_option['strike']}_{selected_option['expiry']}",
                'order_type': 'NET_DEBIT',
                'max_debit': selected_option.get('premium', 0) * 0.5  # Allow paying up to 50% of new premium
            }
            
        return None