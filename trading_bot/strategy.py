import logging
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

class CoveredCallStrategy:
    """
    Implements a covered call options strategy to generate income from stock holdings.
    """
    
    def __init__(self, risk_level='moderate', profit_target_percentage=5.0, 
                 stop_loss_percentage=3.0, options_expiry_days=30):
        """
        Initialize the covered call strategy.
        
        Args:
            risk_level (str): Risk level - 'conservative', 'moderate', or 'aggressive'
            profit_target_percentage (float): Target profit percentage for early exit
            stop_loss_percentage (float): Stop loss percentage to limit downside
            options_expiry_days (int): Target days until expiration for options
        """
        self.risk_level = risk_level
        self.profit_target_percentage = profit_target_percentage
        self.stop_loss_percentage = stop_loss_percentage
        self.options_expiry_days = options_expiry_days
        
        # Configure strategy parameters based on risk level
        self._configure_risk_parameters()
        
        logger.info(f"Initialized covered call strategy with risk level: {risk_level}")
    
    def _configure_risk_parameters(self):
        """Configure strategy parameters based on the selected risk level"""
        if self.risk_level == 'conservative':
            # Conservative: Sell calls with higher probability of profit but lower premium
            self.delta_target = 0.2  # Target delta for conservative approach
            self.premium_min_percentage = 0.5  # Minimum premium as % of stock price
            self.strike_min_percentage = 5.0  # Minimum % above current price
            self.best_options_count = 1  # Consider only the most conservative option
        
        elif self.risk_level == 'aggressive':
            # Aggressive: Sell calls with higher premium but higher assignment risk
            self.delta_target = 0.4  # Target delta for aggressive approach
            self.premium_min_percentage = 1.5  # Minimum premium as % of stock price
            self.strike_min_percentage = 2.0  # Minimum % above current price
            self.best_options_count = 3  # Consider more options
        
        else:  # moderate (default)
            # Moderate: Balanced approach
            self.delta_target = 0.3  # Target delta for moderate approach
            self.premium_min_percentage = 1.0  # Minimum premium as % of stock price
            self.strike_min_percentage = 3.0  # Minimum % above current price
            self.best_options_count = 2  # Consider a couple of options
    
    def select_covered_call(self, stock_price, call_options):
        """
        Select the best call option for a covered call strategy.
        
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
            if (strike_percentage < self.strike_min_percentage or 
                premium_percentage < self.premium_min_percentage):
                continue
            
            # Check expiry is within our target range
            expiry_min = max(7, self.options_expiry_days - 10)
            expiry_max = self.options_expiry_days + 10
            
            if days_to_expiry < expiry_min or days_to_expiry > expiry_max:
                # Only skip if we have other good options
                if len(suitable_options) >= self.best_options_count:
                    continue
            
            # Calculate a score for this option based on our strategy parameters
            # Higher score = better fit for our strategy
            delta_score = 1 - abs(option.get('delta', 0.3) - self.delta_target) * 2
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
            position (dict): Position details including entry price and call details
            current_price (float): Current stock price
            
        Returns:
            dict: Action recommendation for the position
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
        days_to_expiry = (datetime.fromisoformat(expiry_date.replace('Z', '+00:00')) - datetime.now()).days
        
        # Check if we need to take action
        if profit_loss_pct <= -self.stop_loss_percentage:
            # Stop loss triggered
            return {
                'action': 'BUY_TO_CLOSE',
                'reason': f'Stop loss triggered: {profit_loss_pct:.2f}% loss exceeds {self.stop_loss_percentage}% threshold'
            }
        
        if profit_loss_pct >= self.profit_target_percentage:
            # Profit target reached
            return {
                'action': 'BUY_TO_CLOSE',
                'reason': f'Profit target reached: {profit_loss_pct:.2f}% gain exceeds {self.profit_target_percentage}% threshold'
            }
        
        if days_to_expiry <= 5 and current_price < strike_price * 0.98:
            # Close to expiration and price below strike
            return {
                'action': 'ROLL_OUT',
                'reason': f'Option near expiry ({days_to_expiry} days) and price below strike'
            }
        
        if current_price > strike_price * 1.02 and days_to_expiry > 7:
            # Price above strike, risk of assignment
            return {
                'action': 'ROLL_UP_AND_OUT',
                'reason': f'Stock price above strike by > 2%, risk of early assignment'
            }
        
        # Default: no action needed
        return {
            'action': 'NO_ACTION',
            'reason': 'Position within parameters'
        }
    
    def generate_order_parameters(self, action, position, available_options=None):
        """
        Generate order parameters for trade execution.
        
        Args:
            action (str): The action to take (BUY_TO_CLOSE, ROLL_OUT, etc.)
            position (dict): Position details
            available_options (list, optional): Available options for rolling
            
        Returns:
            dict: Order parameters for the trade executor
        """
        symbol = position.get('symbol')
        quantity = position.get('quantity', 0)
        current_strike = position.get('call_strike', 0)
        current_expiry = position.get('call_expiry')
        
        if action == 'BUY_TO_CLOSE':
            return {
                'action': 'BUY_TO_CLOSE',
                'symbol': symbol,
                'option_symbol': f"{symbol}_C_{current_strike}_{current_expiry}",
                'quantity': quantity,
                'order_type': 'MARKET'
            }
        
        elif action in ('ROLL_OUT', 'ROLL_UP_AND_OUT'):
            if not available_options:
                return None
            
            # Filter to find suitable options for rolling
            filtered_options = []
            
            for option in available_options:
                new_strike = option.get('strike', 0)
                new_days = option.get('days_to_expiry', 0)
                
                # For ROLL_OUT, keep same strike but longer expiry
                if action == 'ROLL_OUT':
                    if (new_strike == current_strike and 
                        new_days > 21 and new_days < 45):
                        filtered_options.append(option)
                
                # For ROLL_UP_AND_OUT, increase strike and expiry
                elif action == 'ROLL_UP_AND_OUT':
                    if (new_strike > current_strike and 
                        new_days > 21 and new_days < 45):
                        filtered_options.append(option)
            
            # Select best option based on strategy
            selected_option = self.select_covered_call(0, filtered_options)
            
            if not selected_option:
                return None
            
            # Create order parameters for rolling
            return {
                'action': action,
                'symbol': symbol,
                'quantity': quantity,
                'current_option': f"{symbol}_C_{current_strike}_{current_expiry}",
                'new_option': f"{symbol}_C_{selected_option['strike']}_{selected_option['expiry']}",
                'order_type': 'NET_DEBIT',
                'max_debit': selected_option.get('premium', 0) * 0.5  # Allow paying up to 50% of new premium
            }
        
        return None
