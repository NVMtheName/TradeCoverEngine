import logging
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import math
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

class OptionsStrategy(ABC):
    """
    Abstract base class for options trading strategies.
    All strategies must implement the key methods defined here.
    """
    
    def __init__(self, risk_level='moderate', profit_target_percentage=5.0, 
                 stop_loss_percentage=3.0, options_expiry_days=30):
        """
        Initialize the options strategy with common parameters.
        
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
    
    @abstractmethod
    def _configure_risk_parameters(self):
        """Configure strategy parameters based on the selected risk level"""
        pass
    
    @abstractmethod
    def select_options(self, stock_price, options_data):
        """Select the best options for the strategy"""
        pass
    
    @abstractmethod
    def adjust_position(self, position, current_price):
        """Determine if a position needs adjustment based on price movement"""
        pass
    
    @abstractmethod
    def generate_order_parameters(self, action, position, available_options=None):
        """Generate order parameters for trade execution"""
        pass
    
    def calculate_days_to_expiry(self, expiry_date):
        """Calculate days until expiration for an option"""
        if not expiry_date:
            return 0
        
        try:
            # Handle different date formats
            if 'T' in expiry_date:
                # ISO format with time component
                expiry = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
            else:
                # Date only format YYYY-MM-DD
                expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
                
            return (expiry - datetime.now()).days
        except Exception as e:
            logger.error(f"Error calculating days to expiry: {e}")
            return 0
    
    def is_within_expiry_range(self, days_to_expiry, tolerance=10):
        """Check if an option expiry is within our target range"""
        expiry_min = max(7, self.options_expiry_days - tolerance)
        expiry_max = self.options_expiry_days + tolerance
        return expiry_min <= days_to_expiry <= expiry_max

class CoveredCallStrategy(OptionsStrategy):
    """
    Implements a covered call options strategy to generate income from stock holdings.
    """
    
    def __init__(self, risk_level='moderate', profit_target_percentage=5.0, 
                 stop_loss_percentage=3.0, options_expiry_days=30):
        """
        Initialize the covered call strategy.
        """
        super().__init__(risk_level, profit_target_percentage, stop_loss_percentage, options_expiry_days)
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
    
    def select_options(self, stock_price, options_data):
        """Implementation of abstract method for CoveredCallStrategy"""
        if not options_data or 'calls' not in options_data:
            return None
        return self.select_covered_call(stock_price, options_data['calls'])
        
    def select_covered_call(self, stock_price, call_options):
        """Select the best call option for a covered call strategy"""
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
            if not self.is_within_expiry_range(days_to_expiry):
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
        """Determine if a position needs adjustment based on price movement"""
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
        """Generate order parameters for trade execution"""
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

class PutCreditSpreadStrategy(OptionsStrategy):
    """
    Implements a put credit spread options strategy (bull put spread).
    Sell a put option and buy a lower strike put option to limit risk.
    """
    
    def __init__(self, risk_level='moderate', profit_target_percentage=5.0, 
                 stop_loss_percentage=3.0, options_expiry_days=30):
        """
        Initialize the put credit spread strategy.
        """
        super().__init__(risk_level, profit_target_percentage, stop_loss_percentage, options_expiry_days)
        logger.info(f"Initialized put credit spread strategy with risk level: {risk_level}")
    
    def _configure_risk_parameters(self):
        """Configure strategy parameters based on the selected risk level"""
        if self.risk_level == 'conservative':
            # Conservative: Further OTM put spreads with lower premium but higher probability
            self.delta_target_short = 0.25  # Target delta for short put (lower risk)
            self.delta_target_long = 0.15   # Target delta for long put
            self.spread_width_percentage = 5.0  # Target width between strikes as % of stock price
            self.premium_min_percentage = 0.4   # Minimum premium as % of spread width
            self.best_spreads_count = 1  # Consider only the most conservative spread
        
        elif self.risk_level == 'aggressive':
            # Aggressive: Closer to ATM put spreads with higher premium but lower probability
            self.delta_target_short = 0.40  # Target delta for short put (higher risk)
            self.delta_target_long = 0.25   # Target delta for long put
            self.spread_width_percentage = 7.5  # Target width between strikes as % of stock price
            self.premium_min_percentage = 0.8   # Minimum premium as % of spread width
            self.best_spreads_count = 3  # Consider more spreads
        
        else:  # moderate (default)
            # Moderate: Balanced approach
            self.delta_target_short = 0.30  # Target delta for short put
            self.delta_target_long = 0.20   # Target delta for long put
            self.spread_width_percentage = 6.0  # Target width between strikes as % of stock price
            self.premium_min_percentage = 0.6   # Minimum premium as % of spread width
            self.best_spreads_count = 2  # Consider a couple of spreads
    
    def select_options(self, stock_price, options_data):
        """Select the best put options for a credit spread"""
        if not options_data or 'puts' not in options_data:
            logger.warning("No put options data available for credit spread selection")
            return None
        
        puts = options_data['puts']
        if not puts:
            logger.warning("Empty put options list for credit spread selection")
            return None
            
        # Sort puts by strike price (ascending)
        sorted_puts = sorted(puts, key=lambda x: x.get('strike', 0))
        
        suitable_spreads = []
        
        # Look for valid put credit spreads
        for i, short_put in enumerate(sorted_puts):
            # We need to look for a lower strike put to buy (long put)
            short_strike = short_put.get('strike', 0)
            short_premium = short_put.get('premium', 0)
            short_delta = abs(short_put.get('delta', 0.3))  # Convert to absolute value
            days_to_expiry = short_put.get('days_to_expiry', 30)
            
            # Skip if the short put doesn't meet delta criteria (too risky or not enough premium)
            if abs(short_delta - self.delta_target_short) > 0.15:
                continue
                
            # Skip if expiry doesn't match our target
            if not self.is_within_expiry_range(days_to_expiry):
                continue
                
            # Look for a suitable long put with lower strike
            for j in range(i-1, -1, -1):  # Look at puts with lower strikes
                long_put = sorted_puts[j]
                long_strike = long_put.get('strike', 0)
                long_premium = long_put.get('premium', 0)
                long_delta = abs(long_put.get('delta', 0.2))  # Convert to absolute value
                
                # Ensure both puts have the same expiration
                if long_put.get('days_to_expiry', 0) != days_to_expiry:
                    continue
                    
                # Calculate spread metrics
                spread_width = short_strike - long_strike
                spread_width_percent = (spread_width / stock_price) * 100
                net_credit = short_premium - long_premium
                credit_to_width_ratio = net_credit / spread_width
                
                # Skip if spread width is too small or too large
                target_width = stock_price * (self.spread_width_percentage / 100)
                if abs(spread_width - target_width) / target_width > 0.4:  # Allow 40% deviation
                    continue
                    
                # Skip if net credit is too small compared to spread width
                if credit_to_width_ratio < self.premium_min_percentage / 100:
                    continue
                    
                # Calculate a score for this spread
                short_delta_score = 1 - abs(short_delta - self.delta_target_short) * 2
                long_delta_score = 1 - abs(long_delta - self.delta_target_long) * 2
                width_score = 1 - abs(spread_width_percent - self.spread_width_percentage) / 5
                credit_score = credit_to_width_ratio * 5  # Scale up
                expiry_score = 1 - abs(days_to_expiry - self.options_expiry_days) / 30
                
                # Calculate weighted score based on risk preference
                if self.risk_level == 'conservative':
                    score = (short_delta_score * 0.3 + long_delta_score * 0.2 + 
                             width_score * 0.2 + credit_score * 0.1 + expiry_score * 0.2)
                elif self.risk_level == 'aggressive':
                    score = (short_delta_score * 0.2 + long_delta_score * 0.1 + 
                             width_score * 0.2 + credit_score * 0.4 + expiry_score * 0.1)
                else:  # moderate
                    score = (short_delta_score * 0.25 + long_delta_score * 0.15 + 
                             width_score * 0.2 + credit_score * 0.25 + expiry_score * 0.15)
                
                # Create a spread object with all needed information
                spread = {
                    'strategy': 'PUT_CREDIT_SPREAD',
                    'short_put': short_put,
                    'long_put': long_put,
                    'short_strike': short_strike,
                    'long_strike': long_strike,
                    'short_premium': short_premium,
                    'long_premium': long_premium,
                    'net_credit': net_credit,
                    'spread_width': spread_width,
                    'max_risk': spread_width - net_credit,
                    'max_reward': net_credit,
                    'risk_reward_ratio': (spread_width - net_credit) / net_credit if net_credit > 0 else float('inf'),
                    'days_to_expiry': days_to_expiry,
                    'expiry_date': short_put.get('expiry', ''),
                    'score': score
                }
                
                suitable_spreads.append(spread)
                
                # Only consider one long put per short put to avoid duplicates
                break
        
        # Sort by score (highest first)
        suitable_spreads.sort(key=lambda x: x['score'], reverse=True)
        
        # Return the highest-scoring spread or None if no suitable spreads
        return suitable_spreads[0] if suitable_spreads else None
    
    def adjust_position(self, position, current_price):
        """Determine if a position needs adjustment based on price movement"""
        # Extract relevant position details
        entry_price = position.get('entry_price', 0)
        short_strike = position.get('short_strike', 0)
        long_strike = position.get('long_strike', 0)
        net_credit = position.get('net_credit', 0)
        max_risk = position.get('max_risk', 0)
        expiry_date = position.get('expiry_date')
        
        # If missing essential details, take no action
        if not short_strike or not long_strike or not expiry_date:
            return {
                'action': 'NO_ACTION',
                'reason': 'Incomplete position details for put credit spread'
            }
        
        # Calculate days to expiry
        days_to_expiry = self.calculate_days_to_expiry(expiry_date)
        
        # Calculate current profit/loss percentage
        # For a credit spread, we need to estimate current value based on stock price
        # This is a simplification; in real trading, you'd get the current spread value from the broker
        
        # Estimate current spread value (very simplified model)
        spread_width = short_strike - long_strike
        intrinsic_short = max(0, short_strike - current_price)  # Intrinsic value of short put
        intrinsic_long = max(0, long_strike - current_price)   # Intrinsic value of long put
        
        # Calculate estimated loss based on intrinsic value and time decay
        if days_to_expiry <= 0:
            # At expiration, only intrinsic value remains
            current_value = intrinsic_short - intrinsic_long
        else:
            # Simplified time value decay (not accurate but gives a rough estimate)
            time_factor = min(1.0, days_to_expiry / 30)  # Time decay increases as expiry approaches
            short_time_value = short_strike * 0.01 * time_factor  # Very rough estimate
            long_time_value = long_strike * 0.005 * time_factor   # Long options lose value slower
            
            current_value = (intrinsic_short + short_time_value) - (intrinsic_long + long_time_value)
        
        # Profit is net credit minus current value
        current_profit = net_credit - current_value
        profit_percentage = (current_profit / max_risk) * 100
        
        # Check for adjustment conditions
        if profit_percentage >= self.profit_target_percentage:
            return {
                'action': 'CLOSE_SPREAD',
                'reason': f'Profit target reached: {profit_percentage:.2f}% profit'
            }
        
        if profit_percentage <= -self.stop_loss_percentage:
            return {
                'action': 'CLOSE_SPREAD',
                'reason': f'Stop loss triggered: {profit_percentage:.2f}% loss'
            }
        
        if days_to_expiry <= 5 and current_price > short_strike * 1.02:
            # Close to expiration and price well above short strike (safe)
            return {
                'action': 'CLOSE_SPREAD',
                'reason': f'Near expiration ({days_to_expiry} days) with low risk'
            }
        
        if days_to_expiry <= 7 and current_price < short_strike * 0.98:
            # Close to expiration and price below short strike (risk increases)
            return {
                'action': 'ROLL_SPREAD',
                'reason': f'Near expiration ({days_to_expiry} days) with increasing risk'
            }
        
        # Default: no action needed
        return {
            'action': 'NO_ACTION',
            'reason': 'Position within parameters'
        }
    
    def generate_order_parameters(self, action, position, available_options=None):
        """Generate order parameters for trade execution"""
        symbol = position.get('symbol')
        quantity = position.get('quantity', 0)
        short_strike = position.get('short_strike', 0)
        long_strike = position.get('long_strike', 0)
        expiry_date = position.get('expiry_date')
        
        if action == 'CLOSE_SPREAD':
            return {
                'action': 'CLOSE_SPREAD',
                'symbol': symbol,
                'quantity': quantity,
                'short_option': f"{symbol}_P_{short_strike}_{expiry_date}",
                'long_option': f"{symbol}_P_{long_strike}_{expiry_date}",
                'order_type': 'MARKET'
            }
        
        elif action == 'ROLL_SPREAD':
            if not available_options or 'puts' not in available_options:
                return None
            
            # Find new put credit spread
            new_spread = self.select_options(position.get('current_price', 0), available_options)
            
            if not new_spread:
                return None
            
            # Generate order for rolling the spread
            return {
                'action': 'ROLL_SPREAD',
                'symbol': symbol,
                'quantity': quantity,
                'close_short_option': f"{symbol}_P_{short_strike}_{expiry_date}",
                'close_long_option': f"{symbol}_P_{long_strike}_{expiry_date}",
                'new_short_option': f"{symbol}_P_{new_spread['short_strike']}_{new_spread['expiry_date']}",
                'new_long_option': f"{symbol}_P_{new_spread['long_strike']}_{new_spread['expiry_date']}",
                'order_type': 'NET_DEBIT',
                'max_debit': new_spread['net_credit'] * 0.3  # Allow paying up to 30% of new credit
            }
        
        return None

class IronButterflyStrategy(OptionsStrategy):
    """
    Implements an Iron Butterfly options strategy.
    This is a market-neutral strategy combining a put spread and a call spread
    with the short options at the same strike price (typically near the current stock price).
    """
    
    def __init__(self, risk_level='moderate', profit_target_percentage=5.0, 
                 stop_loss_percentage=3.0, options_expiry_days=30):
        """
        Initialize the iron butterfly strategy.
        """
        super().__init__(risk_level, profit_target_percentage, stop_loss_percentage, options_expiry_days)
        logger.info(f"Initialized iron butterfly strategy with risk level: {risk_level}")
    
    def _configure_risk_parameters(self):
        """Configure strategy parameters based on the selected risk level"""
        if self.risk_level == 'conservative':
            # Conservative: Wider iron butterfly with lower premium but higher probability
            self.center_strike_buffer = 2.0  # Target % distance from current price for center strike
            self.wings_width_percentage = 6.0  # Width of each wing as % of stock price
            self.premium_min_percentage = 1.0  # Minimum credit as % of max risk
            self.delta_tolerance = 0.05  # How close to 0.50 delta the center strike should be
        
        elif self.risk_level == 'aggressive':
            # Aggressive: Narrower iron butterfly with higher premium but lower probability
            self.center_strike_buffer = 0.5  # Target % distance from current price for center strike
            self.wings_width_percentage = 4.0  # Width of each wing as % of stock price
            self.premium_min_percentage = 2.0  # Minimum credit as % of max risk
            self.delta_tolerance = 0.1  # How close to 0.50 delta the center strike should be
        
        else:  # moderate (default)
            # Moderate: Balanced approach
            self.center_strike_buffer = 1.0  # Target % distance from current price for center strike
            self.wings_width_percentage = 5.0  # Width of each wing as % of stock price
            self.premium_min_percentage = 1.5  # Minimum credit as % of max risk
            self.delta_tolerance = 0.08  # How close to 0.50 delta the center strike should be
    
    def select_options(self, stock_price, options_data):
        """Select the best options for an iron butterfly"""
        if not options_data or 'puts' not in options_data or 'calls' not in options_data:
            logger.warning("Incomplete options data for iron butterfly selection")
            return None
        
        puts = options_data['puts']
        calls = options_data['calls']
        
        if not puts or not calls:
            logger.warning("Empty puts or calls list for iron butterfly selection")
            return None
            
        # Sort puts and calls by strike price (ascending)
        sorted_puts = sorted(puts, key=lambda x: x.get('strike', 0))
        sorted_calls = sorted(calls, key=lambda x: x.get('strike', 0))
        
        suitable_butterflies = []
        
        # For iron butterfly, first find a suitable center strike near current price
        # This will be used for both short put and short call
        for option in puts + calls:  # Check all options to find center strike
            strike = option.get('strike', 0)
            delta = abs(option.get('delta', 0.5))
            days_to_expiry = option.get('days_to_expiry', 30)
            
            # Skip if not close to ATM (near 0.50 delta, within tolerance)
            if abs(delta - 0.5) > self.delta_tolerance:
                continue
            
            # Skip if not within required distance from current price
            price_diff_pct = abs((strike - stock_price) / stock_price) * 100
            if price_diff_pct > self.center_strike_buffer:
                continue
                
            # Skip if expiry doesn't match our target
            if not self.is_within_expiry_range(days_to_expiry):
                continue
            
            # Now we have a potential center strike, look for wings
            center_strike = strike
            
            # Find appropriate puts for butterfly
            suitable_short_put = None
            suitable_long_put = None
            
            for put in sorted_puts:
                # For short put, need same strike as center and same expiry
                if (put.get('strike') == center_strike and 
                    put.get('days_to_expiry') == days_to_expiry):
                    suitable_short_put = put
                    break
            
            if not suitable_short_put:
                continue  # Skip this center strike if no short put found
            
            # Calculate wing width
            wing_width = stock_price * self.wings_width_percentage / 100
            target_long_put_strike = center_strike - wing_width
            
            # Find closest long put strike
            best_long_put = None
            best_strike_diff = float('inf')
            
            for put in sorted_puts:
                if put.get('days_to_expiry') != days_to_expiry:
                    continue
                    
                put_strike = put.get('strike', 0)
                if put_strike >= center_strike:  # Long put must be lower than center
                    continue
                    
                strike_diff = abs(put_strike - target_long_put_strike)
                if strike_diff < best_strike_diff:
                    best_strike_diff = strike_diff
                    best_long_put = put
            
            if not best_long_put:
                continue  # Skip if no long put found
                
            suitable_long_put = best_long_put
            
            # Find appropriate calls for butterfly
            suitable_short_call = None
            suitable_long_call = None
            
            for call in sorted_calls:
                # For short call, need same strike as center and same expiry
                if (call.get('strike') == center_strike and 
                    call.get('days_to_expiry') == days_to_expiry):
                    suitable_short_call = call
                    break
            
            if not suitable_short_call:
                continue  # Skip this center strike if no short call found
            
            # Calculate target long call strike
            target_long_call_strike = center_strike + wing_width
            
            # Find closest long call strike
            best_long_call = None
            best_strike_diff = float('inf')
            
            for call in sorted_calls:
                if call.get('days_to_expiry') != days_to_expiry:
                    continue
                    
                call_strike = call.get('strike', 0)
                if call_strike <= center_strike:  # Long call must be higher than center
                    continue
                    
                strike_diff = abs(call_strike - target_long_call_strike)
                if strike_diff < best_strike_diff:
                    best_strike_diff = strike_diff
                    best_long_call = call
            
            if not best_long_call:
                continue  # Skip if no long call found
                
            suitable_long_call = best_long_call
            
            # If we get here, we have all four legs of the iron butterfly
            # Calculate key metrics
            short_put_premium = suitable_short_put.get('premium', 0)
            long_put_premium = suitable_long_put.get('premium', 0)
            short_call_premium = suitable_short_call.get('premium', 0)
            long_call_premium = suitable_long_call.get('premium', 0)
            
            long_put_strike = suitable_long_put.get('strike', 0)
            long_call_strike = suitable_long_call.get('strike', 0)
            
            net_credit = (short_put_premium + short_call_premium) - (long_put_premium + long_call_premium)
            put_wing_width = center_strike - long_put_strike
            call_wing_width = long_call_strike - center_strike
            max_risk = min(put_wing_width, call_wing_width) - net_credit
            max_profit = net_credit
            
            # Skip if net credit is too small
            credit_to_risk_ratio = (net_credit / max_risk) * 100
            if credit_to_risk_ratio < self.premium_min_percentage:
                continue
            
            # Calculate score for this butterfly
            center_score = 1 - (price_diff_pct / self.center_strike_buffer)
            width_balance_score = 1 - abs(put_wing_width - call_wing_width) / max(put_wing_width, call_wing_width)
            credit_score = credit_to_risk_ratio / self.premium_min_percentage
            expiry_score = 1 - abs(days_to_expiry - self.options_expiry_days) / 30
            
            # Weight scores differently based on risk level
            if self.risk_level == 'conservative':
                final_score = center_score * 0.4 + width_balance_score * 0.3 + credit_score * 0.1 + expiry_score * 0.2
            elif self.risk_level == 'aggressive':
                final_score = center_score * 0.2 + width_balance_score * 0.2 + credit_score * 0.5 + expiry_score * 0.1
            else:  # moderate
                final_score = center_score * 0.3 + width_balance_score * 0.25 + credit_score * 0.3 + expiry_score * 0.15
            
            # Create butterfly object
            butterfly = {
                'strategy': 'IRON_BUTTERFLY',
                'center_strike': center_strike,
                'short_put': suitable_short_put,
                'long_put': suitable_long_put,
                'short_call': suitable_short_call,
                'long_call': suitable_long_call,
                'short_put_strike': center_strike,
                'long_put_strike': long_put_strike,
                'short_call_strike': center_strike,
                'long_call_strike': long_call_strike,
                'short_put_premium': short_put_premium,
                'long_put_premium': long_put_premium,
                'short_call_premium': short_call_premium,
                'long_call_premium': long_call_premium,
                'net_credit': net_credit,
                'put_wing_width': put_wing_width,
                'call_wing_width': call_wing_width,
                'max_risk': max_risk,
                'max_profit': max_profit,
                'breakeven_lower': center_strike - net_credit,
                'breakeven_upper': center_strike + net_credit,
                'days_to_expiry': days_to_expiry,
                'expiry_date': suitable_short_put.get('expiry', ''),
                'score': final_score
            }
            
            suitable_butterflies.append(butterfly)
        
        # Sort by score (highest first)
        suitable_butterflies.sort(key=lambda x: x['score'], reverse=True)
        
        # Return the highest-scoring butterfly or None if no suitable butterflies
        return suitable_butterflies[0] if suitable_butterflies else None
    
    def adjust_position(self, position, current_price):
        """Determine if a position needs adjustment based on price movement"""
        # Extract relevant position details
        center_strike = position.get('center_strike', 0)
        net_credit = position.get('net_credit', 0)
        max_risk = position.get('max_risk', 0)
        expiry_date = position.get('expiry_date')
        breakeven_lower = position.get('breakeven_lower', 0)
        breakeven_upper = position.get('breakeven_upper', 0)
        
        # If missing essential details, take no action
        if not center_strike or not expiry_date:
            return {
                'action': 'NO_ACTION',
                'reason': 'Incomplete position details for iron butterfly'
            }
        
        # Calculate days to expiry
        days_to_expiry = self.calculate_days_to_expiry(expiry_date)
        
        # Calculate estimated current value and profit
        # For iron butterfly, maximum profit occurs when price equals center strike at expiration
        
        # Calculate distance from center as percentage of wing width
        distance_pct = abs(current_price - center_strike) / center_strike
        
        if days_to_expiry <= 0:
            # At expiration
            if distance_pct < 0.01:  # At or very near center strike
                current_value = 0
            else:
                # Calculate intrinsic value at expiration
                current_value = min(abs(current_price - center_strike), max(position.get('put_wing_width', 0), position.get('call_wing_width', 0)))
        else:
            # Before expiration - simplified model
            time_factor = min(1.0, days_to_expiry / 30)
            
            if distance_pct < 0.01:  # Very close to center strike
                # Mostly time value remains
                current_value = net_credit * time_factor
            else:
                # More complex estimate based on distance from center and time remaining
                intrinsic_component = min(distance_pct * center_strike, max(position.get('put_wing_width', 0), position.get('call_wing_width', 0)))
                time_component = net_credit * time_factor * (1 - distance_pct)
                current_value = intrinsic_component - time_component
        
        # Profit is net credit minus current value
        current_profit = net_credit - current_value
        profit_percentage = (current_profit / max_risk) * 100 if max_risk > 0 else 0
        
        # Adjustment logic
        if profit_percentage >= self.profit_target_percentage:
            return {
                'action': 'CLOSE_BUTTERFLY',
                'reason': f'Profit target reached: {profit_percentage:.2f}% profit'
            }
        
        if profit_percentage <= -self.stop_loss_percentage:
            return {
                'action': 'CLOSE_BUTTERFLY',
                'reason': f'Stop loss triggered: {profit_percentage:.2f}% loss'
            }
        
        # Time-based management
        if days_to_expiry <= 5 and current_price > breakeven_lower and current_price < breakeven_upper:
            # Close to expiration and price within profit zone
            return {
                'action': 'CLOSE_BUTTERFLY',
                'reason': f'Near expiration ({days_to_expiry} days) with price in profit zone'
            }
        
        if days_to_expiry <= 7 and (current_price < breakeven_lower * 0.98 or current_price > breakeven_upper * 1.02):
            # Close to expiration and price outside breakeven points with buffer
            return {
                'action': 'CLOSE_BUTTERFLY',
                'reason': f'Near expiration ({days_to_expiry} days) with price outside profit zone'
            }
        
        # Price movement adjustment
        if days_to_expiry > 15 and distance_pct > 0.05:
            # Consider rolling to a new butterfly centered closer to current price
            return {
                'action': 'ROLL_BUTTERFLY',
                'reason': f'Price moved away from center strike by {distance_pct:.2f}%, consider recenter'
            }
        
        # Default: no action needed
        return {
            'action': 'NO_ACTION',
            'reason': 'Position within parameters'
        }
    
    def generate_order_parameters(self, action, position, available_options=None):
        """Generate order parameters for trade execution"""
        symbol = position.get('symbol')
        quantity = position.get('quantity', 0)
        center_strike = position.get('center_strike', 0)
        long_put_strike = position.get('long_put_strike', 0)
        long_call_strike = position.get('long_call_strike', 0)
        expiry_date = position.get('expiry_date')
        
        if action == 'CLOSE_BUTTERFLY':
            return {
                'action': 'CLOSE_BUTTERFLY',
                'symbol': symbol,
                'quantity': quantity,
                'short_put': f"{symbol}_P_{center_strike}_{expiry_date}",
                'long_put': f"{symbol}_P_{long_put_strike}_{expiry_date}",
                'short_call': f"{symbol}_C_{center_strike}_{expiry_date}",
                'long_call': f"{symbol}_C_{long_call_strike}_{expiry_date}",
                'order_type': 'MARKET'
            }
        
        elif action == 'ROLL_BUTTERFLY':
            if not available_options or 'puts' not in available_options or 'calls' not in available_options:
                return None
            
            # Find new iron butterfly
            new_butterfly = self.select_options(position.get('current_price', 0), available_options)
            
            if not new_butterfly:
                return None
            
            # Generate order for rolling to new butterfly
            return {
                'action': 'ROLL_BUTTERFLY',
                'symbol': symbol,
                'quantity': quantity,
                'close_short_put': f"{symbol}_P_{center_strike}_{expiry_date}",
                'close_long_put': f"{symbol}_P_{long_put_strike}_{expiry_date}",
                'close_short_call': f"{symbol}_C_{center_strike}_{expiry_date}",
                'close_long_call': f"{symbol}_C_{long_call_strike}_{expiry_date}",
                'new_short_put': f"{symbol}_P_{new_butterfly['center_strike']}_{new_butterfly['expiry_date']}",
                'new_long_put': f"{symbol}_P_{new_butterfly['long_put_strike']}_{new_butterfly['expiry_date']}",
                'new_short_call': f"{symbol}_C_{new_butterfly['center_strike']}_{new_butterfly['expiry_date']}",
                'new_long_call': f"{symbol}_C_{new_butterfly['long_call_strike']}_{new_butterfly['expiry_date']}",
                'order_type': 'NET_DEBIT',
                'max_debit': new_butterfly['net_credit'] * 0.5  # Allow paying up to 50% of new credit
            }
        
        return None
        
class CalendarSpreadStrategy(OptionsStrategy):
    """
    Implements a Calendar Spread options strategy.
    This strategy involves buying a longer-term option and selling a shorter-term option
    at the same strike price. It profits from time decay while minimizing directional risk.
    Calendar spreads can be constructed with either calls or puts.
    """
    
    def __init__(self, risk_level='moderate', profit_target_percentage=5.0, 
                 stop_loss_percentage=3.0, options_expiry_days=30, option_type='call'):
        """
        Initialize the calendar spread strategy.
        
        Args:
            option_type (str): Type of options to use - 'call' or 'put'
        """
        super().__init__(risk_level, profit_target_percentage, stop_loss_percentage, options_expiry_days)
        self.option_type = option_type.lower()
        if self.option_type not in ['call', 'put']:
            logger.warning(f"Invalid option type '{option_type}' for calendar spread. Using 'call'.")
            self.option_type = 'call'
            
        logger.info(f"Initialized {self.option_type} calendar spread strategy with risk level: {risk_level}")
    
    def _configure_risk_parameters(self):
        """Configure strategy parameters based on the selected risk level"""
        if self.risk_level == 'conservative':
            # Conservative: Further OTM calendar spreads
            self.target_delta = 0.35 if self.option_type == 'call' else -0.35  # Target delta
            self.delta_tolerance = 0.15  # How close to target delta
            self.short_term_days = 15   # Target days until expiration for short option
            self.long_term_days = 45    # Target days until expiration for long option
            self.days_between_expiries = 30  # Target difference between expiries
            self.premium_min_percentage = 15.0  # Short premium should be at least this % of long premium
        
        elif self.risk_level == 'aggressive':
            # Aggressive: More ATM calendar spreads
            self.target_delta = 0.50 if self.option_type == 'call' else -0.50  # Target delta
            self.delta_tolerance = 0.20  # How close to target delta
            self.short_term_days = 7    # Target days until expiration for short option
            self.long_term_days = 35    # Target days until expiration for long option
            self.days_between_expiries = 28  # Target difference between expiries
            self.premium_min_percentage = 25.0  # Short premium should be at least this % of long premium
        
        else:  # moderate (default)
            # Moderate: Balanced approach
            self.target_delta = 0.40 if self.option_type == 'call' else -0.40  # Target delta
            self.delta_tolerance = 0.15  # How close to target delta
            self.short_term_days = 10   # Target days until expiration for short option
            self.long_term_days = 40    # Target days until expiration for long option
            self.days_between_expiries = 30  # Target difference between expiries
            self.premium_min_percentage = 20.0  # Short premium should be at least this % of long premium
    
    def select_options(self, stock_price, options_data):
        """Select the best options for a calendar spread"""
        if not options_data:
            logger.warning("No options data available for calendar spread selection")
            return None
        
        # Determine which options to use based on the option type
        option_key = 'calls' if self.option_type == 'call' else 'puts'
        if option_key not in options_data or not options_data[option_key]:
            logger.warning(f"No {self.option_type} options available for calendar spread selection")
            return None
        
        options = options_data[option_key]
        
        # Find all available expiry dates
        all_expiries = set()
        for option in options:
            if 'days_to_expiry' in option:
                all_expiries.add(option.get('days_to_expiry'))
        
        # Sort expiries from nearest to furthest
        sorted_expiries = sorted(all_expiries)
        if len(sorted_expiries) < 2:
            logger.warning("Need at least two different expiry dates for calendar spread")
            return None
        
        # Find potential short-term and long-term expiries
        short_expiries = [exp for exp in sorted_expiries if abs(exp - self.short_term_days) <= 7 and exp >= 5]
        long_expiries = [exp for exp in sorted_expiries if abs(exp - self.long_term_days) <= 15 and exp > 21]
        
        if not short_expiries or not long_expiries:
            logger.warning("No suitable expiry dates for calendar spread")
            return None
        
        # Group options by expiry
        options_by_expiry = {}
        for option in options:
            expiry = option.get('days_to_expiry')
            if expiry not in options_by_expiry:
                options_by_expiry[expiry] = []
            options_by_expiry[expiry].append(option)
        
        suitable_spreads = []
        
        # For each potential short and long expiry combination
        for short_exp in short_expiries:
            for long_exp in long_expiries:
                # Skip if they're the same expiry
                if short_exp >= long_exp:
                    continue
                
                # Check if the time gap between expiries is appropriate
                gap = long_exp - short_exp
                if abs(gap - self.days_between_expiries) > 10:  # Allow 10 days deviation
                    continue
                
                short_options = options_by_expiry.get(short_exp, [])
                long_options = options_by_expiry.get(long_exp, [])
                
                # For each potential strike price
                for long_option in long_options:
                    strike = long_option.get('strike', 0)
                    delta = long_option.get('delta', 0)
                    
                    # Skip if the delta is too far from our target
                    if abs(delta - self.target_delta) > self.delta_tolerance:
                        continue
                    
                    # Find corresponding short option with same strike
                    short_option = None
                    for opt in short_options:
                        if opt.get('strike') == strike:
                            short_option = opt
                            break
                    
                    if not short_option:
                        continue  # No matching short option at this strike
                    
                    # Calculate key metrics
                    short_premium = short_option.get('premium', 0)
                    long_premium = long_option.get('premium', 0)
                    net_debit = long_premium - short_premium
                    
                    # Skip if short premium is too small relative to long premium
                    short_to_long_ratio = (short_premium / long_premium) * 100 if long_premium > 0 else 0
                    if short_to_long_ratio < self.premium_min_percentage:
                        continue
                    
                    # Calculate theta (time decay) advantage
                    short_theta = abs(short_option.get('theta', 0.01))
                    long_theta = abs(long_option.get('theta', 0.005))
                    theta_advantage = short_theta - long_theta
                    
                    # Calculate score for this spread
                    delta_score = 1 - abs(delta - self.target_delta) / self.delta_tolerance
                    theta_score = theta_advantage * 100  # Scale up the theta value
                    expiry_gap_score = 1 - abs(gap - self.days_between_expiries) / 10
                    premium_ratio_score = short_to_long_ratio / self.premium_min_percentage
                    
                    # Different weighting based on risk level
                    if self.risk_level == 'conservative':
                        score = delta_score * 0.3 + theta_score * 0.3 + expiry_gap_score * 0.2 + premium_ratio_score * 0.2
                    elif self.risk_level == 'aggressive':
                        score = delta_score * 0.2 + theta_score * 0.5 + expiry_gap_score * 0.1 + premium_ratio_score * 0.2
                    else:  # moderate
                        score = delta_score * 0.25 + theta_score * 0.4 + expiry_gap_score * 0.15 + premium_ratio_score * 0.2
                    
                    # Create spread object
                    spread = {
                        'strategy': f"{self.option_type.upper()}_CALENDAR_SPREAD",
                        'short_option': short_option,
                        'long_option': long_option,
                        'strike': strike,
                        'short_premium': short_premium,
                        'long_premium': long_premium,
                        'net_debit': net_debit,
                        'short_days_to_expiry': short_exp,
                        'long_days_to_expiry': long_exp,
                        'short_expiry': short_option.get('expiry', ''),
                        'long_expiry': long_option.get('expiry', ''),
                        'delta': delta,
                        'theta_advantage': theta_advantage,
                        'short_to_long_ratio': short_to_long_ratio,
                        'score': score
                    }
                    
                    suitable_spreads.append(spread)
        
        # Sort by score (highest first)
        suitable_spreads.sort(key=lambda x: x['score'], reverse=True)
        
        # Return the highest-scoring spread or None if no suitable spreads
        return suitable_spreads[0] if suitable_spreads else None
    
    def adjust_position(self, position, current_price):
        """Determine if a position needs adjustment based on price movement"""
        # Extract relevant position details
        strategy = position.get('strategy', '')
        strike = position.get('strike', 0)
        short_expiry = position.get('short_expiry', '')
        short_days_remaining = self.calculate_days_to_expiry(short_expiry)
        net_debit = position.get('net_debit', 0)
        
        # If missing essential details, take no action
        if not strike or not short_expiry:
            return {
                'action': 'NO_ACTION',
                'reason': 'Incomplete position details for calendar spread'
            }
        
        # Estimate current profit/loss (simplified model)
        # For calendar spreads, max profit typically occurs when price is near strike at short expiration
        # This is a simplified approximation; actual P/L would depend on option greeks and IV
        price_to_strike_percent = abs((current_price - strike) / strike) * 100
        
        # Three scenarios:
        # 1. Short-term option expired or very close to expiry
        if short_days_remaining <= 1:
            if price_to_strike_percent <= 2:  # Price near strike at short expiration (ideal)
                return {
                    'action': 'ROLL_SHORT_OPTION',
                    'reason': f'Short option expiring with price near strike - roll to collect more premium'
                }
            else:  # Price moved away from strike
                return {
                    'action': 'CLOSE_POSITION',
                    'reason': f'Short option expiring with price away from strike - close to limit risk'
                }
        
        # 2. Short-term option close to expiry, but not imminent
        elif short_days_remaining <= 5:
            # If price is near strike, profitable situation
            if price_to_strike_percent <= 3:
                return {
                    'action': 'MONITOR',
                    'reason': f'Short option expiring soon with price near strike - favorable position'
                }
            # If price moved far from strike, consider closing
            elif price_to_strike_percent >= 8:
                return {
                    'action': 'CLOSE_POSITION',
                    'reason': f'Price moved {price_to_strike_percent:.1f}% away from strike with expiry approaching'
                }
        
        # 3. Short-term option still has significant time value
        else:
            # If price moved dramatically, consider closing
            if price_to_strike_percent >= 15:
                return {
                    'action': 'CLOSE_POSITION',
                    'reason': f'Price moved {price_to_strike_percent:.1f}% away from strike - too much directional risk'
                }
            # If IV increased dramatically, may be profitable to close early
            if position.get('iv_change_percent', 0) > 20:
                return {
                    'action': 'CLOSE_POSITION',
                    'reason': f'Implied volatility increased significantly - favorable to close early'
                }
        
        # Default: no adjustment needed
        return {
            'action': 'NO_ACTION',
            'reason': 'Position within parameters'
        }
    
    def generate_order_parameters(self, action, position, available_options=None):
        """Generate order parameters for trade execution"""
        symbol = position.get('symbol')
        quantity = position.get('quantity', 0)
        strike = position.get('strike', 0)
        option_type_code = 'C' if self.option_type == 'call' else 'P'  # C for call, P for put
        short_expiry = position.get('short_expiry', '')
        long_expiry = position.get('long_expiry', '')
        
        if action == 'CLOSE_POSITION':
            return {
                'action': 'CLOSE_CALENDAR',
                'symbol': symbol,
                'quantity': quantity,
                'short_option': f"{symbol}_{option_type_code}_{strike}_{short_expiry}",
                'long_option': f"{symbol}_{option_type_code}_{strike}_{long_expiry}",
                'order_type': 'MARKET'
            }
        
        elif action == 'ROLL_SHORT_OPTION':
            if not available_options:
                return None
            
            # Determine which options to use based on the option type
            option_key = 'calls' if self.option_type == 'call' else 'puts'
            if option_key not in available_options or not available_options[option_key]:
                return None
            
            options = available_options[option_key]
            
            # Find a new short option with the same strike but a later expiry
            # Target ~30 days out from current date
            target_days = 30
            best_option = None
            best_days_diff = float('inf')
            
            for option in options:
                if option.get('strike') != strike:
                    continue
                    
                days = option.get('days_to_expiry', 0)
                # Must be more than 14 days out but less than the long option
                long_days = position.get('long_days_to_expiry', 120)
                if days < 14 or days >= long_days:
                    continue
                    
                days_diff = abs(days - target_days)
                if days_diff < best_days_diff:
                    best_days_diff = days_diff
                    best_option = option
            
            if not best_option:
                return None
            
            # Create order to roll the short option
            new_expiry = best_option.get('expiry', '')
            return {
                'action': 'ROLL_SHORT_OPTION',
                'symbol': symbol,
                'quantity': quantity,
                'old_option': f"{symbol}_{option_type_code}_{strike}_{short_expiry}",
                'new_option': f"{symbol}_{option_type_code}_{strike}_{new_expiry}",
                'order_type': 'NET_CREDIT',
                'min_credit': best_option.get('premium', 0) * 0.8  # Target at least 80% of theoretical premium
            }
        
        return None

class DiagonalSpreadStrategy(OptionsStrategy):
    """
    Implements a Diagonal Spread options strategy.
    This is a combination of a horizontal (calendar) spread and a vertical spread,
    using different strikes and different expiration dates.
    It can be used with either calls or puts.
    """
    
    def __init__(self, risk_level='moderate', profit_target_percentage=5.0, 
                 stop_loss_percentage=3.0, options_expiry_days=30, option_type='call'):
        """
        Initialize the diagonal spread strategy.
        
        Args:
            option_type (str): Type of options to use - 'call' or 'put'
        """
        super().__init__(risk_level, profit_target_percentage, stop_loss_percentage, options_expiry_days)
        self.option_type = option_type.lower()
        if self.option_type not in ['call', 'put']:
            logger.warning(f"Invalid option type '{option_type}' for diagonal spread. Using 'call'.")
            self.option_type = 'call'
            
        logger.info(f"Initialized {self.option_type} diagonal spread strategy with risk level: {risk_level}")
    
    def _configure_risk_parameters(self):
        """Configure strategy parameters based on the selected risk level"""
        if self.risk_level == 'conservative':
            # Conservative: Further OTM diagonal spreads
            self.short_delta_target = 0.30 if self.option_type == 'call' else -0.30  # Target delta for short option
            self.long_delta_target = 0.40 if self.option_type == 'call' else -0.40   # Target delta for long option
            self.delta_tolerance = 0.15  # How close to target delta
            self.short_term_days = 15   # Target days until expiration for short option
            self.long_term_days = 45    # Target days until expiration for long option
            self.days_between_expiries = 30  # Target difference between expiries
            self.strike_diff_target = 5.0  # Target % difference between strikes
            self.premium_min_percentage = 15.0  # Short premium should be at least this % of long premium
        
        elif self.risk_level == 'aggressive':
            # Aggressive: More ATM diagonal spreads
            self.short_delta_target = 0.45 if self.option_type == 'call' else -0.45  # Target delta for short option
            self.long_delta_target = 0.55 if self.option_type == 'call' else -0.55   # Target delta for long option
            self.delta_tolerance = 0.20  # How close to target delta
            self.short_term_days = 7    # Target days until expiration for short option
            self.long_term_days = 35    # Target days until expiration for long option
            self.days_between_expiries = 28  # Target difference between expiries
            self.strike_diff_target = 3.0  # Target % difference between strikes
            self.premium_min_percentage = 25.0  # Short premium should be at least this % of long premium
        
        else:  # moderate (default)
            # Moderate: Balanced approach
            self.short_delta_target = 0.35 if self.option_type == 'call' else -0.35  # Target delta for short option
            self.long_delta_target = 0.45 if self.option_type == 'call' else -0.45   # Target delta for long option
            self.delta_tolerance = 0.15  # How close to target delta
            self.short_term_days = 10   # Target days until expiration for short option
            self.long_term_days = 40    # Target days until expiration for long option
            self.days_between_expiries = 30  # Target difference between expiries
            self.strike_diff_target = 4.0  # Target % difference between strikes
            self.premium_min_percentage = 20.0  # Short premium should be at least this % of long premium
    
    def select_options(self, stock_price, options_data):
        """Select the best options for a diagonal spread"""
        if not options_data:
            logger.warning("No options data available for diagonal spread selection")
            return None
        
        # Determine which options to use based on the option type
        option_key = 'calls' if self.option_type == 'call' else 'puts'
        if option_key not in options_data or not options_data[option_key]:
            logger.warning(f"No {self.option_type} options available for diagonal spread selection")
            return None
        
        options = options_data[option_key]
        
        # Find all available expiry dates
        all_expiries = set()
        for option in options:
            if 'days_to_expiry' in option:
                all_expiries.add(option.get('days_to_expiry'))
        
        # Sort expiries from nearest to furthest
        sorted_expiries = sorted(all_expiries)
        if len(sorted_expiries) < 2:
            logger.warning("Need at least two different expiry dates for diagonal spread")
            return None
        
        # Find potential short-term and long-term expiries
        short_expiries = [exp for exp in sorted_expiries if abs(exp - self.short_term_days) <= 7 and exp >= 5]
        long_expiries = [exp for exp in sorted_expiries if abs(exp - self.long_term_days) <= 15 and exp > 21]
        
        if not short_expiries or not long_expiries:
            logger.warning("No suitable expiry dates for diagonal spread")
            return None
        
        # Group options by expiry
        options_by_expiry = {}
        for option in options:
            expiry = option.get('days_to_expiry')
            if expiry not in options_by_expiry:
                options_by_expiry[expiry] = []
            options_by_expiry[expiry].append(option)
        
        suitable_spreads = []
        
        # For each potential short and long expiry combination
        for short_exp in short_expiries:
            for long_exp in long_expiries:
                # Skip if they're the same expiry
                if short_exp >= long_exp:
                    continue
                
                # Check if the time gap between expiries is appropriate
                gap = long_exp - short_exp
                if abs(gap - self.days_between_expiries) > 10:  # Allow 10 days deviation
                    continue
                
                short_options = options_by_expiry.get(short_exp, [])
                long_options = options_by_expiry.get(long_exp, [])
                
                # Sort options by strike
                short_options.sort(key=lambda x: x.get('strike', 0))
                long_options.sort(key=lambda x: x.get('strike', 0))
                
                # For each potential short option
                for short_option in short_options:
                    short_strike = short_option.get('strike', 0)
                    short_delta = short_option.get('delta', 0)
                    
                    # Skip if the delta is too far from our target
                    if abs(short_delta - self.short_delta_target) > self.delta_tolerance:
                        continue
                    
                    # For call diagonals, we want a higher strike for the short option
                    # For put diagonals, we want a lower strike for the short option
                    target_strike_diff = stock_price * (self.strike_diff_target / 100)
                    
                    if self.option_type == 'call':
                        target_long_strike = short_strike - target_strike_diff
                    else:  # put
                        target_long_strike = short_strike + target_strike_diff
                    
                    # Find the closest long option strike
                    best_long_option = None
                    best_strike_diff = float('inf')
                    
                    for long_option in long_options:
                        long_strike = long_option.get('strike', 0)
                        long_delta = long_option.get('delta', 0)
                        
                        # Skip if long delta is too far from target
                        if abs(long_delta - self.long_delta_target) > self.delta_tolerance:
                            continue
                            
                        # For call, ensure long strike is lower than short strike
                        # For put, ensure long strike is higher than short strike
                        if (self.option_type == 'call' and long_strike >= short_strike) or \
                           (self.option_type == 'put' and long_strike <= short_strike):
                            continue
                        
                        strike_diff = abs(long_strike - target_long_strike)
                        if strike_diff < best_strike_diff:
                            best_strike_diff = strike_diff
                            best_long_option = long_option
                    
                    if not best_long_option:
                        continue  # No suitable long option found
                    
                    # Calculate key metrics
                    short_premium = short_option.get('premium', 0)
                    long_premium = best_long_option.get('premium', 0)
                    long_strike = best_long_option.get('strike', 0)
                    net_debit = long_premium - short_premium
                    
                    # Skip if short premium is too small relative to long premium
                    short_to_long_ratio = (short_premium / long_premium) * 100 if long_premium > 0 else 0
                    if short_to_long_ratio < self.premium_min_percentage:
                        continue
                    
                    # Calculate strike difference percentage
                    strike_diff_pct = abs((short_strike - long_strike) / stock_price) * 100
                    
                    # Calculate theta (time decay) advantage
                    short_theta = abs(short_option.get('theta', 0.01))
                    long_theta = abs(best_long_option.get('theta', 0.005))
                    theta_advantage = short_theta - long_theta
                    
                    # Calculate score for this spread
                    short_delta_score = 1 - abs(short_delta - self.short_delta_target) / self.delta_tolerance
                    long_delta_score = 1 - abs(long_delta - self.long_delta_target) / self.delta_tolerance
                    theta_score = theta_advantage * 100  # Scale up the theta value
                    expiry_gap_score = 1 - abs(gap - self.days_between_expiries) / 10
                    strike_diff_score = 1 - abs(strike_diff_pct - self.strike_diff_target) / 3
                    premium_ratio_score = short_to_long_ratio / self.premium_min_percentage
                    
                    # Different weighting based on risk level
                    if self.risk_level == 'conservative':
                        score = (short_delta_score * 0.2 + long_delta_score * 0.2 + 
                                theta_score * 0.2 + expiry_gap_score * 0.1 + 
                                strike_diff_score * 0.2 + premium_ratio_score * 0.1)
                    elif self.risk_level == 'aggressive':
                        score = (short_delta_score * 0.15 + long_delta_score * 0.15 + 
                                theta_score * 0.3 + expiry_gap_score * 0.1 + 
                                strike_diff_score * 0.15 + premium_ratio_score * 0.15)
                    else:  # moderate
                        score = (short_delta_score * 0.2 + long_delta_score * 0.15 + 
                                theta_score * 0.25 + expiry_gap_score * 0.1 + 
                                strike_diff_score * 0.15 + premium_ratio_score * 0.15)
                    
                    # Create spread object
                    spread = {
                        'strategy': f"{self.option_type.upper()}_DIAGONAL_SPREAD",
                        'short_option': short_option,
                        'long_option': best_long_option,
                        'short_strike': short_strike,
                        'long_strike': long_strike,
                        'short_premium': short_premium,
                        'long_premium': long_premium,
                        'net_debit': net_debit,
                        'short_days_to_expiry': short_exp,
                        'long_days_to_expiry': long_exp,
                        'short_expiry': short_option.get('expiry', ''),
                        'long_expiry': best_long_option.get('expiry', ''),
                        'short_delta': short_delta,
                        'long_delta': best_long_option.get('delta', 0),
                        'theta_advantage': theta_advantage,
                        'strike_diff_pct': strike_diff_pct,
                        'short_to_long_ratio': short_to_long_ratio,
                        'score': score
                    }
                    
                    suitable_spreads.append(spread)
        
        # Sort by score (highest first)
        suitable_spreads.sort(key=lambda x: x['score'], reverse=True)
        
        # Return the highest-scoring spread or None if no suitable spreads
        return suitable_spreads[0] if suitable_spreads else None
    
    def adjust_position(self, position, current_price):
        """Determine if a position needs adjustment based on price movement"""
        # Extract relevant position details
        short_strike = position.get('short_strike', 0)
        long_strike = position.get('long_strike', 0)
        short_expiry = position.get('short_expiry', '')
        short_days_remaining = self.calculate_days_to_expiry(short_expiry)
        strike_diff = abs(short_strike - long_strike)
        net_debit = position.get('net_debit', 0)
        
        # If missing essential details, take no action
        if not short_strike or not long_strike or not short_expiry:
            return {
                'action': 'NO_ACTION',
                'reason': 'Incomplete position details for diagonal spread'
            }
        
        # Calculate current position in relation to strikes
        # For calls, we want current price between the strikes, closer to long strike
        # For puts, we also want current price between strikes, closer to long strike
        is_call = self.option_type == 'call'
        if is_call:
            is_between_strikes = long_strike <= current_price <= short_strike
            price_to_short_percent = abs((current_price - short_strike) / short_strike) * 100
            price_to_long_percent = abs((current_price - long_strike) / long_strike) * 100
        else:  # put
            is_between_strikes = short_strike <= current_price <= long_strike
            price_to_short_percent = abs((current_price - short_strike) / short_strike) * 100
            price_to_long_percent = abs((current_price - long_strike) / long_strike) * 100
        
        # Three scenarios based on short option expiry
        # 1. Short-term option expired or very close to expiry
        if short_days_remaining <= 1:
            if is_between_strikes:  # Ideal scenario
                return {
                    'action': 'ROLL_SHORT_OPTION',
                    'reason': f'Short option expiring with price between strikes - roll to collect more premium'
                }
            else:  # Price moved beyond one of the strikes
                # For calls: danger if price > short strike
                # For puts: danger if price < short strike
                if (is_call and current_price > short_strike) or (not is_call and current_price < short_strike):
                    return {
                        'action': 'CLOSE_POSITION',
                        'reason': f'Short option expiring with price beyond short strike - risk of assignment'
                    }
                else:  # Less profitable but not dangerous
                    return {
                        'action': 'ROLL_SHORT_OPTION',
                        'reason': f'Short option expiring with suboptimal price - roll to reset position'
                    }
        
        # 2. Short-term option close to expiry, but not imminent
        elif short_days_remaining <= 5:
            if is_between_strikes:  # Favorable scenario
                return {
                    'action': 'MONITOR',
                    'reason': f'Short option expiring soon with price between strikes - favorable position'
                }
            # If price moved far beyond short strike, increasing risk
            elif ((is_call and current_price > short_strike * 1.03) or 
                  (not is_call and current_price < short_strike * 0.97)):
                return {
                    'action': 'CLOSE_POSITION',
                    'reason': f'Price moved significantly beyond short strike with expiry approaching'
                }
            # If price moved away from the profitable zone but not dangerously so
            else:
                return {
                    'action': 'MONITOR',
                    'reason': f'Position not optimal but manageable - continue monitoring'
                }
        
        # 3. Short-term option still has significant time value
        else:
            # If price moved dramatically beyond short strike, increasing risk
            if ((is_call and current_price > short_strike * 1.05) or 
                (not is_call and current_price < short_strike * 0.95)):
                return {
                    'action': 'CLOSE_POSITION',
                    'reason': f'Price moved significantly beyond short strike - increasing risk'
                }
            # If IV increased dramatically, may be profitable to close early
            if position.get('iv_change_percent', 0) > 20:
                return {
                    'action': 'CLOSE_POSITION',
                    'reason': f'Implied volatility increased significantly - favorable to close early'
                }
        
        # Default: no adjustment needed
        return {
            'action': 'NO_ACTION',
            'reason': 'Position within parameters'
        }
    
    def generate_order_parameters(self, action, position, available_options=None):
        """Generate order parameters for trade execution"""
        symbol = position.get('symbol')
        quantity = position.get('quantity', 0)
        short_strike = position.get('short_strike', 0)
        long_strike = position.get('long_strike', 0)
        option_type_code = 'C' if self.option_type == 'call' else 'P'  # C for call, P for put
        short_expiry = position.get('short_expiry', '')
        long_expiry = position.get('long_expiry', '')
        
        if action == 'CLOSE_POSITION':
            return {
                'action': 'CLOSE_DIAGONAL',
                'symbol': symbol,
                'quantity': quantity,
                'short_option': f"{symbol}_{option_type_code}_{short_strike}_{short_expiry}",
                'long_option': f"{symbol}_{option_type_code}_{long_strike}_{long_expiry}",
                'order_type': 'MARKET'
            }
        
        elif action == 'ROLL_SHORT_OPTION':
            if not available_options:
                return None
            
            # Determine which options to use based on the option type
            option_key = 'calls' if self.option_type == 'call' else 'puts'
            if option_key not in available_options or not available_options[option_key]:
                return None
            
            options = available_options[option_key]
            
            # Find a new short option with similar strike but later expiry
            target_days = 30
            best_option = None
            best_days_diff = float('inf')
            
            for option in options:
                # Check if strike is close enough to original short strike
                if abs(option.get('strike', 0) - short_strike) / short_strike > 0.02:  # Allow 2% difference
                    continue
                    
                days = option.get('days_to_expiry', 0)
                # Must be more than 14 days out but less than the long option
                long_days = position.get('long_days_to_expiry', 120)
                if days < 14 or days >= long_days:
                    continue
                    
                days_diff = abs(days - target_days)
                if days_diff < best_days_diff:
                    best_days_diff = days_diff
                    best_option = option
            
            if not best_option:
                return None
            
            # Create order to roll the short option
            new_strike = best_option.get('strike', 0)
            new_expiry = best_option.get('expiry', '')
            return {
                'action': 'ROLL_SHORT_OPTION',
                'symbol': symbol,
                'quantity': quantity,
                'old_option': f"{symbol}_{option_type_code}_{short_strike}_{short_expiry}",
                'new_option': f"{symbol}_{option_type_code}_{new_strike}_{new_expiry}",
                'order_type': 'NET_CREDIT',
                'min_credit': best_option.get('premium', 0) * 0.7  # Target at least 70% of theoretical premium
            }
        
        return None

class IronCondorStrategy(OptionsStrategy):
    """
    Implements an Iron Condor options strategy.
    Combines a bull put spread and a bear call spread for a market-neutral position.
    """
    
    def __init__(self, risk_level='moderate', profit_target_percentage=5.0, 
                 stop_loss_percentage=3.0, options_expiry_days=30):
        """
        Initialize the iron condor strategy.
        """
        super().__init__(risk_level, profit_target_percentage, stop_loss_percentage, options_expiry_days)
        logger.info(f"Initialized iron condor strategy with risk level: {risk_level}")
    
    def _configure_risk_parameters(self):
        """Configure strategy parameters based on the selected risk level"""
        if self.risk_level == 'conservative':
            # Conservative: Wider iron condor with lower premium but higher probability
            self.put_delta_target = 0.15  # Target delta for short put (lower risk)
            self.call_delta_target = 0.15  # Target delta for short call (lower risk)
            self.wings_width_percentage = 5.0  # Width of each wing as % of stock price
            self.premium_min_percentage = 0.7  # Minimum credit as % of max risk
            self.range_width_percentage = 15.0  # Width between short put and short call as % of stock price
        
        elif self.risk_level == 'aggressive':
            # Aggressive: Narrower iron condor with higher premium but lower probability
            self.put_delta_target = 0.30  # Target delta for short put (higher risk)
            self.call_delta_target = 0.30  # Target delta for short call (higher risk)
            self.wings_width_percentage = 4.0  # Width of each wing as % of stock price
            self.premium_min_percentage = 1.2  # Minimum credit as % of max risk
            self.range_width_percentage = 10.0  # Width between short put and short call as % of stock price
        
        else:  # moderate (default)
            # Moderate: Balanced approach
            self.put_delta_target = 0.20  # Target delta for short put
            self.call_delta_target = 0.20  # Target delta for short call
            self.wings_width_percentage = 4.5  # Width of each wing as % of stock price
            self.premium_min_percentage = 0.9  # Minimum credit as % of max risk
            self.range_width_percentage = 12.0  # Width between short put and short call as % of stock price
    
    def select_options(self, stock_price, options_data):
        """Select the best options for an iron condor"""
        if not options_data or 'puts' not in options_data or 'calls' not in options_data:
            logger.warning("Incomplete options data for iron condor selection")
            return None
        
        puts = options_data['puts']
        calls = options_data['calls']
        
        if not puts or not calls:
            logger.warning("Empty puts or calls list for iron condor selection")
            return None
            
        # Sort puts by strike price (ascending)
        sorted_puts = sorted(puts, key=lambda x: x.get('strike', 0))
        # Sort calls by strike price (ascending)
        sorted_calls = sorted(calls, key=lambda x: x.get('strike', 0))
        
        suitable_condors = []
        
        # First, find viable put spreads
        put_spreads = []
        for i, short_put in enumerate(sorted_puts):
            # Skip puts with strike price above current price (we want OTM puts)
            short_strike = short_put.get('strike', 0)
            if short_strike >= stock_price:
                continue
                
            short_premium = short_put.get('premium', 0)
            short_delta = abs(short_put.get('delta', 0.2))  # Convert to absolute value
            days_to_expiry = short_put.get('days_to_expiry', 30)
            
            # Skip if delta doesn't match our target for OTM put
            if abs(short_delta - self.put_delta_target) > 0.1:
                continue
                
            # Skip if expiry doesn't match our target
            if not self.is_within_expiry_range(days_to_expiry):
                continue
                
            # Calculate target strike for long put protection
            target_long_strike = short_strike - (stock_price * self.wings_width_percentage / 100)
            
            # Find the closest long put strike
            best_long_put = None
            best_strike_diff = float('inf')
            
            for j in range(i-1, -1, -1):  # Look at lower strikes
                long_put = sorted_puts[j]
                long_strike = long_put.get('strike', 0)
                
                # Ensure same expiry
                if long_put.get('days_to_expiry', 0) != days_to_expiry:
                    continue
                    
                strike_diff = abs(long_strike - target_long_strike)
                if strike_diff < best_strike_diff:
                    best_strike_diff = strike_diff
                    best_long_put = long_put
            
            if best_long_put:
                put_spread = {
                    'short_put': short_put,
                    'long_put': best_long_put,
                    'short_strike': short_strike,
                    'long_strike': best_long_put.get('strike', 0),
                    'days_to_expiry': days_to_expiry,
                    'expiry_date': short_put.get('expiry', ''),
                    'net_credit': short_premium - best_long_put.get('premium', 0)
                }
                put_spreads.append(put_spread)
        
        # Next, find viable call spreads with same expiry dates as our put spreads
        for put_spread in put_spreads:
            short_put_strike = put_spread['short_strike']
            days_to_expiry = put_spread['days_to_expiry']
            expiry_date = put_spread['expiry_date']
            
            # Calculate target strike for short call
            target_short_call_strike = short_put_strike + (stock_price * self.range_width_percentage / 100)
            
            # Find the closest short call strike
            best_short_call = None
            best_strike_diff = float('inf')
            
            for call in sorted_calls:
                # Skip calls with strike price below current price (we want OTM calls)
                call_strike = call.get('strike', 0)
                if call_strike <= stock_price:
                    continue
                    
                # Ensure same expiry
                if call.get('days_to_expiry', 0) != days_to_expiry or call.get('expiry', '') != expiry_date:
                    continue
                    
                call_delta = abs(call.get('delta', 0.2))  # Convert to absolute value
                
                # Skip if delta doesn't match our target for OTM call
                if abs(call_delta - self.call_delta_target) > 0.1:
                    continue
                
                strike_diff = abs(call_strike - target_short_call_strike)
                if strike_diff < best_strike_diff:
                    best_strike_diff = strike_diff
                    best_short_call = call
            
            if best_short_call:
                short_call_strike = best_short_call.get('strike', 0)
                short_call_premium = best_short_call.get('premium', 0)
                
                # Calculate target strike for long call protection
                target_long_call_strike = short_call_strike + (stock_price * self.wings_width_percentage / 100)
                
                # Find the closest long call strike
                best_long_call = None
                best_strike_diff = float('inf')
                
                for call in sorted_calls:
                    call_strike = call.get('strike', 0)
                    
                    # Ensure strike is higher than short call
                    if call_strike <= short_call_strike:
                        continue
                        
                    # Ensure same expiry
                    if call.get('days_to_expiry', 0) != days_to_expiry or call.get('expiry', '') != expiry_date:
                        continue
                    
                    strike_diff = abs(call_strike - target_long_call_strike)
                    if strike_diff < best_strike_diff:
                        best_strike_diff = strike_diff
                        best_long_call = call
                
                if best_long_call:
                    long_call_strike = best_long_call.get('strike', 0)
                    long_call_premium = best_long_call.get('premium', 0)
                    
                    # Calculate total credit for iron condor
                    put_credit = put_spread['net_credit']
                    call_credit = short_call_premium - long_call_premium
                    total_credit = put_credit + call_credit
                    
                    # Calculate max risk for iron condor (width of wider side minus total credit)
                    put_width = short_put_strike - put_spread['long_strike']
                    call_width = long_call_strike - short_call_strike
                    max_width = max(put_width, call_width)
                    max_risk = max_width - total_credit
                    
                    # Check if meets minimum credit requirement
                    if total_credit < (max_risk * self.premium_min_percentage / 100):
                        continue
                    
                    # Calculate a score for this iron condor
                    width_ratio = min(put_width, call_width) / max(put_width, call_width)  # 1.0 is ideal (equal wings)
                    range_width = short_call_strike - short_put_strike
                    range_width_percent = (range_width / stock_price) * 100
                    range_score = 1 - abs(range_width_percent - self.range_width_percentage) / 5
                    credit_ratio = total_credit / max_risk
                    credit_score = credit_ratio * 5  # Scale up
                    expiry_score = 1 - abs(days_to_expiry - self.options_expiry_days) / 30
                    
                    # Calculate weighted score based on risk preference
                    if self.risk_level == 'conservative':
                        score = width_ratio * 0.3 + range_score * 0.3 + credit_score * 0.2 + expiry_score * 0.2
                    elif self.risk_level == 'aggressive':
                        score = width_ratio * 0.2 + range_score * 0.2 + credit_score * 0.5 + expiry_score * 0.1
                    else:  # moderate
                        score = width_ratio * 0.25 + range_score * 0.25 + credit_score * 0.3 + expiry_score * 0.2
                    
                    # Create an iron condor object with all needed information
                    condor = {
                        'strategy': 'IRON_CONDOR',
                        'short_put': put_spread['short_put'],
                        'long_put': put_spread['long_put'],
                        'short_call': best_short_call,
                        'long_call': best_long_call,
                        'short_put_strike': short_put_strike,
                        'long_put_strike': put_spread['long_strike'],
                        'short_call_strike': short_call_strike,
                        'long_call_strike': long_call_strike,
                        'put_credit': put_credit,
                        'call_credit': call_credit,
                        'total_credit': total_credit,
                        'max_risk': max_risk,
                        'days_to_expiry': days_to_expiry,
                        'expiry_date': expiry_date,
                        'score': score
                    }
                    
                    suitable_condors.append(condor)
        
        # Sort by score (highest first)
        suitable_condors.sort(key=lambda x: x['score'], reverse=True)
        
        # Return the highest-scoring iron condor or None if no suitable ones
        return suitable_condors[0] if suitable_condors else None
    
    def adjust_position(self, position, current_price):
        """Determine if a position needs adjustment based on price movement"""
        # Extract relevant position details
        short_put_strike = position.get('short_put_strike', 0)
        long_put_strike = position.get('long_put_strike', 0)
        short_call_strike = position.get('short_call_strike', 0)
        long_call_strike = position.get('long_call_strike', 0)
        total_credit = position.get('total_credit', 0)
        max_risk = position.get('max_risk', 0)
        expiry_date = position.get('expiry_date')
        
        # If missing essential details, take no action
        if not short_put_strike or not long_put_strike or not short_call_strike or not long_call_strike or not expiry_date:
            return {
                'action': 'NO_ACTION',
                'reason': 'Incomplete position details for iron condor'
            }
        
        # Calculate days to expiry
        days_to_expiry = self.calculate_days_to_expiry(expiry_date)
        
        # Calculate how close the price is to either short strike
        put_distance = current_price - short_put_strike  # Positive if price above short put (good)
        call_distance = short_call_strike - current_price  # Positive if price below short call (good)
        put_distance_pct = (put_distance / short_put_strike) * 100
        call_distance_pct = (call_distance / short_call_strike) * 100
        
        # Determine which short option is more at risk
        if put_distance_pct < call_distance_pct:
            at_risk_side = 'PUT'
            at_risk_distance = put_distance_pct
        else:
            at_risk_side = 'CALL'
            at_risk_distance = call_distance_pct
        
        # Simplified profit/loss estimation (similar to credit spread logic)
        # This is a rough estimate - real trading would use actual market values
        risk_pct = 0
        
        if current_price <= long_put_strike:
            # Below long put - max loss
            risk_pct = 100
        elif current_price >= long_call_strike:
            # Above long call - max loss
            risk_pct = 100
        elif long_put_strike < current_price < short_put_strike:
            # In the put wing - partial loss
            risk_pct = ((short_put_strike - current_price) / (short_put_strike - long_put_strike)) * 100
        elif short_call_strike < current_price < long_call_strike:
            # In the call wing - partial loss
            risk_pct = ((current_price - short_call_strike) / (long_call_strike - short_call_strike)) * 100
        # Else: price is in the profit zone between short strikes
        
        # Estimate current value of the iron condor
        if risk_pct == 0:
            # In the profit zone - value decreases with time
            time_factor = min(1.0, days_to_expiry / self.options_expiry_days)
            current_value = total_credit * time_factor
        else:
            # In a wing or beyond - value increases with risk
            current_value = total_credit + (max_risk * (risk_pct / 100))
        
        # Calculate profit/loss
        profit = total_credit - current_value
        profit_percentage = (profit / max_risk) * 100
        
        # Check for adjustment conditions
        if profit_percentage >= self.profit_target_percentage:
            return {
                'action': 'CLOSE_CONDOR',
                'reason': f'Profit target reached: {profit_percentage:.2f}% profit'
            }
        
        if profit_percentage <= -self.stop_loss_percentage:
            return {
                'action': 'CLOSE_CONDOR',
                'reason': f'Stop loss triggered: {profit_percentage:.2f}% loss'
            }
        
        if days_to_expiry <= 5 and at_risk_distance > 5:
            # Close to expiration but price safely away from both short strikes
            return {
                'action': 'CLOSE_CONDOR',
                'reason': f'Near expiration ({days_to_expiry} days) with low risk'
            }
        
        if days_to_expiry <= 7 and at_risk_distance < 2:
            # Close to expiration with price near a short strike
            if at_risk_side == 'PUT':
                return {
                    'action': 'ADJUST_PUT_SIDE',
                    'reason': f'Near expiration ({days_to_expiry} days) with price close to short put strike'
                }
            else:  # CALL
                return {
                    'action': 'ADJUST_CALL_SIDE',
                    'reason': f'Near expiration ({days_to_expiry} days) with price close to short call strike'
                }
        
        # Default: no action needed
        return {
            'action': 'NO_ACTION',
            'reason': 'Position within parameters'
        }
    
    def generate_order_parameters(self, action, position, available_options=None):
        """Generate order parameters for trade execution"""
        symbol = position.get('symbol')
        quantity = position.get('quantity', 0)
        short_put_strike = position.get('short_put_strike', 0)
        long_put_strike = position.get('long_put_strike', 0)
        short_call_strike = position.get('short_call_strike', 0)
        long_call_strike = position.get('long_call_strike', 0)
        expiry_date = position.get('expiry_date')
        
        if action == 'CLOSE_CONDOR':
            return {
                'action': 'CLOSE_CONDOR',
                'symbol': symbol,
                'quantity': quantity,
                'short_put_option': f"{symbol}_P_{short_put_strike}_{expiry_date}",
                'long_put_option': f"{symbol}_P_{long_put_strike}_{expiry_date}",
                'short_call_option': f"{symbol}_C_{short_call_strike}_{expiry_date}",
                'long_call_option': f"{symbol}_C_{long_call_strike}_{expiry_date}",
                'order_type': 'MARKET'
            }
        
        elif action == 'ADJUST_PUT_SIDE':
            if not available_options or 'puts' not in available_options:
                return None
            
            # Find new put credit spread with same expiry date but lower strikes
            puts = available_options.get('puts', [])
            
            # Build a smaller options data structure with only puts of matching expiry
            puts_data = {'puts': [p for p in puts if p.get('expiry', '') == expiry_date]}
            
            # Use PutCreditSpreadStrategy to find a new put spread
            put_strategy = PutCreditSpreadStrategy(self.risk_level, self.profit_target_percentage,
                                                self.stop_loss_percentage, self.options_expiry_days)
            new_put_spread = put_strategy.select_options(position.get('current_price', 0), puts_data)
            
            if not new_put_spread:
                return None
            
            # Generate order for adjusting the put side of the iron condor
            return {
                'action': 'ADJUST_PUT_SIDE',
                'symbol': symbol,
                'quantity': quantity,
                'close_short_put': f"{symbol}_P_{short_put_strike}_{expiry_date}",
                'close_long_put': f"{symbol}_P_{long_put_strike}_{expiry_date}",
                'new_short_put': f"{symbol}_P_{new_put_spread['short_strike']}_{new_put_spread['expiry_date']}",
                'new_long_put': f"{symbol}_P_{new_put_spread['long_strike']}_{new_put_spread['expiry_date']}",
                'order_type': 'NET_DEBIT',
                'max_debit': new_put_spread['net_credit'] * 0.5  # Allow paying up to 50% of new credit
            }
        
        elif action == 'ADJUST_CALL_SIDE':
            if not available_options or 'calls' not in available_options:
                return None
            
            # Find new call credit spread with same expiry date but higher strikes
            calls = available_options.get('calls', [])
            
            # Filter to calls with matching expiry date and higher strikes
            calls_filtered = [c for c in calls if c.get('expiry', '') == expiry_date 
                             and c.get('strike', 0) > short_call_strike]
            
            if not calls_filtered:
                return None
                
            # Sort by delta and find a new short call with similar delta to original strategy
            sorted_calls = sorted(calls_filtered, key=lambda x: abs(abs(x.get('delta', 0)) - self.call_delta_target))
            
            if not sorted_calls:
                return None
                
            new_short_call = sorted_calls[0]
            new_short_strike = new_short_call.get('strike', 0)
            
            # Find a new long call with similar width to original spread
            original_width = long_call_strike - short_call_strike
            target_long_strike = new_short_strike + original_width
            
            # Find the closest long call strike
            best_long_call = None
            best_strike_diff = float('inf')
            
            for call in calls_filtered:
                call_strike = call.get('strike', 0)
                if call_strike <= new_short_strike:
                    continue
                    
                strike_diff = abs(call_strike - target_long_strike)
                if strike_diff < best_strike_diff:
                    best_strike_diff = strike_diff
                    best_long_call = call
            
            if not best_long_call:
                return None
                
            new_long_strike = best_long_call.get('strike', 0)
            
            # Generate order for adjusting the call side of the iron condor
            return {
                'action': 'ADJUST_CALL_SIDE',
                'symbol': symbol,
                'quantity': quantity,
                'close_short_call': f"{symbol}_C_{short_call_strike}_{expiry_date}",
                'close_long_call': f"{symbol}_C_{long_call_strike}_{expiry_date}",
                'new_short_call': f"{symbol}_C_{new_short_strike}_{expiry_date}",
                'new_long_call': f"{symbol}_C_{new_long_strike}_{expiry_date}",
                'order_type': 'NET_DEBIT',
                'max_debit': (new_short_call.get('premium', 0) - best_long_call.get('premium', 0)) * 0.5  # Allow paying up to 50% of new credit
            }
        
        return None
