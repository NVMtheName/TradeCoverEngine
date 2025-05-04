import logging
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

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
                    'risk_reward_ratio': (spread_width - net_credit) / net_credit,
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
