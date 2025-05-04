import logging
import json
import time
from datetime import datetime, timedelta
import threading
import queue
import random
import os

# Configure logging
logger = logging.getLogger(__name__)

class AutoTrader:
    """
    AI-powered automated trading system that can scan for stock picks,
    analyze market data, and execute trades without user intervention.
    """
    
    def __init__(self, api_connector, ai_advisor, trade_executor, stock_analyzer):
        """
        Initialize the auto trader.
        
        Args:
            api_connector: API connector for market data and trade execution
            ai_advisor: AI advisor for market analysis and predictions
            trade_executor: Trade executor for placing trades
            stock_analyzer: Stock analyzer for technical analysis
        """
        self.api_connector = api_connector
        self.ai_advisor = ai_advisor
        self.trade_executor = trade_executor
        self.stock_analyzer = stock_analyzer
        
        # Trading parameters
        self.is_enabled = False
        self.last_scan_time = None
        self.scan_interval_hours = 6  # How often to scan for new opportunities
        self.max_concurrent_trades = 5  # Maximum number of concurrent trades
        self.max_position_size = 5000  # Maximum $ amount per position
        self.confidence_threshold = 0.7  # Minimum AI confidence score to execute a trade
        
        # Watchlist of stocks to scan
        self.watchlist = []
        
        # Queue for trade signals
        self.trade_queue = queue.Queue()
        
        # Thread for background scanning and trading
        self.trading_thread = None
        self.should_stop = threading.Event()
        
        logger.info("Initialized AI auto trader")
    
    def start(self):
        """
        Start the auto trader background thread.
        """
        if self.is_enabled:
            logger.warning("Auto trader already running")
            return False
        
        self.is_enabled = True
        self.should_stop.clear()
        self.trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
        self.trading_thread.start()
        
        logger.info("Auto trader started")
        return True
    
    def stop(self):
        """
        Stop the auto trader background thread.
        """
        if not self.is_enabled:
            logger.warning("Auto trader not running")
            return False
        
        self.is_enabled = False
        self.should_stop.set()
        if self.trading_thread:
            self.trading_thread.join(timeout=5.0)
        
        logger.info("Auto trader stopped")
        return True
    
    def set_watchlist(self, symbols):
        """
        Set the watchlist of stocks to scan.
        
        Args:
            symbols (list): List of stock symbols
        """
        self.watchlist = symbols
        logger.info(f"Auto trader watchlist updated with {len(symbols)} symbols")
    
    def set_trading_parameters(self, params):
        """
        Set trading parameters for the auto trader.
        
        Args:
            params (dict): Trading parameters
        """
        if 'scan_interval_hours' in params:
            self.scan_interval_hours = params['scan_interval_hours']
        
        if 'max_concurrent_trades' in params:
            self.max_concurrent_trades = params['max_concurrent_trades']
        
        if 'max_position_size' in params:
            self.max_position_size = params['max_position_size']
        
        if 'confidence_threshold' in params:
            self.confidence_threshold = params['confidence_threshold']
        
        logger.info("Auto trader parameters updated")
    
    def get_status(self):
        """
        Get the current status of the auto trader.
        
        Returns:
            dict: Auto trader status
        """
        return {
            'is_enabled': self.is_enabled,
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'next_scan_time': (self.last_scan_time + timedelta(hours=self.scan_interval_hours)).isoformat() if self.last_scan_time else None,
            'watchlist_size': len(self.watchlist),
            'pending_signals': self.trade_queue.qsize(),
            'parameters': {
                'scan_interval_hours': self.scan_interval_hours,
                'max_concurrent_trades': self.max_concurrent_trades,
                'max_position_size': self.max_position_size,
                'confidence_threshold': self.confidence_threshold
            }
        }
    
    def scan_for_opportunities(self, force=False):
        """
        Scan the watchlist for trading opportunities using AI analysis.
        
        Args:
            force (bool): Force a scan even if the scan interval hasn't elapsed
            
        Returns:
            list: Trading opportunities with AI analysis
        """
        # Check if scan interval has elapsed or if forced
        if not force and self.last_scan_time:
            time_since_last_scan = datetime.now() - self.last_scan_time
            if time_since_last_scan.total_seconds() < self.scan_interval_hours * 3600:
                hours_to_next_scan = (self.scan_interval_hours - (time_since_last_scan.total_seconds() / 3600))
                logger.info(f"Scan interval not elapsed. Next scan in {hours_to_next_scan:.1f} hours")
                return []
        
        # Update scan time
        self.last_scan_time = datetime.now()
        
        # If watchlist is empty, download top market cap stocks
        if not self.watchlist:
            logger.warning("Watchlist is empty, using default top stocks")
            self.watchlist = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'JPM', 'V', 'JNJ']
        
        # Get market data for AI context
        market_data = self._get_market_context()
        
        opportunities = []
        
        for symbol in self.watchlist:
            try:
                # Get price history
                price_history = self.api_connector.get_stock_data(symbol, days=90)
                
                if not price_history or not price_history.get('prices'):
                    logger.warning(f"Could not get price history for {symbol}")
                    continue
                
                # Get additional financial data (could be expanded)
                financial_data = {
                    'market_cap': 'unknown',  # In a real implementation, this would be actual data
                    'sector': 'unknown'
                }
                
                # Get AI analysis
                analysis = self.ai_advisor.analyze_stock(symbol, price_history, financial_data)
                
                # Check if analysis indicates a trading opportunity
                if analysis and analysis.get('confidence') >= self.confidence_threshold:
                    # Create opportunity record
                    opportunity = {
                        'symbol': symbol,
                        'timestamp': datetime.now().isoformat(),
                        'current_price': price_history['prices'][-1] if price_history['prices'] else None,
                        'ai_insights': analysis.get('ai_insights'),
                        'suitability_score': analysis.get('suitability_score'),
                        'confidence': analysis.get('confidence'),
                        'recommendation': analysis.get('recommendation'),
                        'risks': analysis.get('risks'),
                        'rewards': analysis.get('rewards')
                    }
                    
                    opportunities.append(opportunity)
                    
                    # Add to trade queue if auto trading is enabled
                    if self.is_enabled:
                        self.trade_queue.put(opportunity)
                        logger.info(f"Added {symbol} to trade queue with confidence {analysis.get('confidence'):.2f}")
            
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {str(e)}")
        
        logger.info(f"Scan completed. Found {len(opportunities)} trading opportunities")
        return opportunities
    
    def _get_market_context(self):
        """
        Get overall market context for AI analysis.
        
        Returns:
            dict: Market context data
        """
        # This would be expanded with real market data in production
        # For simulation, return basic context
        return {
            'timestamp': datetime.now().isoformat(),
            'market_indices': {
                'SPY': self.api_connector.get_current_price('SPY'),
                'QQQ': self.api_connector.get_current_price('QQQ'),
                'IWM': self.api_connector.get_current_price('IWM')
            },
            'vix': self.api_connector.get_current_price('VIX') or 15.0,  # Fallback value if not available
            'treasury_yield_10y': 2.5  # Placeholder value
        }
    
    def _trading_loop(self):
        """
        Background thread that processes the trade queue and executes trades.
        """
        while not self.should_stop.is_set():
            try:
                # Check for scheduled scan
                if self.last_scan_time:
                    time_since_last_scan = datetime.now() - self.last_scan_time
                    if time_since_last_scan.total_seconds() >= self.scan_interval_hours * 3600:
                        self.scan_for_opportunities()
                else:
                    # Initial scan if never run before
                    self.scan_for_opportunities()
                
                # Process trade queue
                self._process_trade_queue()
                
                # Check for adjustments to existing positions
                self._check_position_adjustments()
                
                # Sleep to avoid busy waiting
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in auto trader background thread: {str(e)}")
                time.sleep(60)  # Longer sleep after error
    
    def _process_trade_queue(self):
        """
        Process pending trade signals in the queue.
        """
        # Get current positions
        positions = self.api_connector.get_open_positions()
        current_position_count = len(positions) if positions else 0
        
        # Check if we're under the max concurrent trades limit
        if current_position_count >= self.max_concurrent_trades:
            return
        
        # Calculate how many new trades we can take
        available_slots = self.max_concurrent_trades - current_position_count
        
        # Process up to available_slots trades
        for _ in range(min(available_slots, self.trade_queue.qsize())):
            try:
                # Get opportunity from queue with non-blocking
                if self.trade_queue.empty():
                    break
                    
                opportunity = self.trade_queue.get(block=False)
                
                # Execute trade based on AI recommendation
                self._execute_ai_trade(opportunity)
                
                # Mark task as done
                self.trade_queue.task_done()
                
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing trade: {str(e)}")
    
    def _execute_ai_trade(self, opportunity):
        """
        Execute a trade based on AI recommendation.
        
        Args:
            opportunity (dict): Trading opportunity with AI analysis
        """
        symbol = opportunity.get('symbol')
        recommendation = opportunity.get('recommendation', {})
        
        # Determine the right strategy based on AI analysis
        trade_result = None
        
        # Check for covered call opportunity (default strategy)
        if recommendation:
            strike_price = recommendation.get('strike_price')
            days_to_expiration = recommendation.get('days_to_expiration')
            
            # Calculate position size based on current price and max position size
            current_price = opportunity.get('current_price')
            if not current_price:
                current_price = self.api_connector.get_current_price(symbol)
            
            if not current_price:
                logger.error(f"Could not determine current price for {symbol}")
                return
            
            quantity = int(self.max_position_size / current_price)
            quantity = (quantity // 100) * 100  # Round to multiple of 100 for options contracts
            
            if quantity < 100:
                logger.warning(f"Position size too small for {symbol} at price {current_price}")
                return
            
            # Execute covered call
            trade_result = self.trade_executor.execute_covered_call(
                symbol=symbol,
                quantity=quantity,
                strike_price=strike_price,
                expiry_date=None  # Let the trade executor find the expiry date
            )
        
        # Log the result
        if trade_result and trade_result.get('success'):
            logger.info(f"Auto trader successfully executed trade for {symbol}: {trade_result.get('message')}")
        else:
            error_msg = trade_result.get('message') if trade_result else "Unknown error"
            logger.error(f"Auto trader failed to execute trade for {symbol}: {error_msg}")
    
    def _check_position_adjustments(self):
        """
        Check existing positions for potential adjustments based on AI recommendations.
        """
        # Get current positions
        positions = self.api_connector.get_open_positions()
        if not positions:
            return
        
        for position in positions:
            try:
                symbol = position.get('symbol')
                entry_price = position.get('entry_price')
                current_price = self.api_connector.get_current_price(symbol)
                
                if not current_price:
                    continue
                
                # Get strategy for this position type
                strategy = None
                if position.get('position_type') == 'covered_call':
                    from trading_bot.strategy import CoveredCallStrategy
                    strategy = CoveredCallStrategy()
                elif position.get('position_type') == 'put_credit_spread':
                    from trading_bot.strategies import PutCreditSpreadStrategy
                    strategy = PutCreditSpreadStrategy()
                
                if not strategy:
                    continue
                
                # Check if adjustment is needed
                adjustment = strategy.adjust_position(position, current_price)
                
                if adjustment and adjustment.get('action') != 'NO_ACTION':
                    # Generate AI recommendation for adjustment
                    self._generate_adjustment_recommendation(position, adjustment, current_price)
            
            except Exception as e:
                logger.error(f"Error checking position adjustment: {str(e)}")
    
    def _generate_adjustment_recommendation(self, position, adjustment, current_price):
        """
        Generate an AI recommendation for position adjustment.
        
        Args:
            position (dict): Position details
            adjustment (dict): Suggested adjustment
            current_price (float): Current stock price
        """
        try:
            symbol = position.get('symbol')
            action = adjustment.get('action')
            reason = adjustment.get('reason')
            
            # Get price history and options chain
            price_history = self.api_connector.get_stock_data(symbol, days=30)
            options_chain = self.api_connector.get_options_chain(symbol)
            
            # Create context for AI analysis
            context = {
                'symbol': symbol,
                'position': position,
                'current_price': current_price,
                'price_history': price_history,
                'options_chain': options_chain,
                'suggested_adjustment': adjustment
            }
            
            # Use AI advisor to evaluate the adjustment
            # This would be implemented with a new method in AIAdvisor
            # For now, we'll just log the suggested adjustment
            logger.info(f"AI auto trader suggests {action} for {symbol}: {reason}")
            
            # In future enhancement, we would call:
            # recommendation = self.ai_advisor.evaluate_position_adjustment(context)
            # and then execute the adjustment if AI agrees
        
        except Exception as e:
            logger.error(f"Error generating adjustment recommendation: {str(e)}")
