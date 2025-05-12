import pandas as pd
import numpy as np
import logging
import os
from datetime import datetime, timedelta
from trading_bot.ai_advisor import AIAdvisor

# Configure logging
logger = logging.getLogger(__name__)

class StockAnalyzer:
    """
    Analyzes stock data to identify potential covered call opportunities.
    Incorporates AI-powered analysis when available.
    """
    
    def __init__(self, api_connector):
        """
        Initialize the stock analyzer.
        
        Args:
            api_connector: An instance of APIConnector for data retrieval
        """
        self.api_connector = api_connector
        
        # Initialize AI advisor if OpenAI API key is available
        self.ai_advisor = AIAdvisor()
        if self.ai_advisor.is_available():
            logger.info("AI-powered stock analysis enabled.")
        else:
            logger.info("AI-powered stock analysis not available. Using standard analysis only.")
    
    def analyze_stock(self, symbol):
        """
        Analyze a single stock for covered call potential.
        
        Args:
            symbol (str): The stock symbol to analyze
            
        Returns:
            dict: Analysis results including technical indicators and recommendations
        """
        try:
            # Get historical stock data (last 90 days)
            stock_data = self.api_connector.get_stock_data(symbol, days=90)
            
            if not stock_data['dates'] or not stock_data['prices']:
                logger.warning(f"No data available for {symbol}")
                return None
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame({
                'date': pd.to_datetime(stock_data['dates']),
                'price': stock_data['prices'],
                'volume': stock_data['volumes']
            })
            
            # Calculate basic technical indicators
            df = self._calculate_technical_indicators(df)
            
            # Get current price
            current_price = self.api_connector.get_current_price(symbol)
            
            if not current_price:
                current_price = df['price'].iloc[-1]
            
            # Evaluate stock volatility
            volatility = df['price'].pct_change().std() * np.sqrt(252) * 100  # Annualized volatility in percentage
            
            # Check for potential covered call opportunity
            buy_signal = self._evaluate_buy_signal(df)
            
            # Get options chain data
            options_chain = self.api_connector.get_options_chain(symbol)
            
            # Find optimal call options for covered call strategy
            call_recommendations = self._find_optimal_calls(current_price, options_chain.get('calls', []), volatility)
            
            # Generate overall recommendation
            recommendation = self._generate_recommendation(buy_signal, call_recommendations, volatility)
            
            # Prepare analysis result
            analysis_result = {
                'symbol': symbol,
                'current_price': current_price,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'technical_indicators': {
                    'sma_20': df['sma_20'].iloc[-1],
                    'sma_50': df['sma_50'].iloc[-1],
                    'rsi': df['rsi'].iloc[-1],
                    'macd': df['macd'].iloc[-1],
                    'macd_signal': df['macd_signal'].iloc[-1],
                    'volatility': volatility
                },
                'buy_signal': buy_signal,
                'call_recommendations': call_recommendations,
                'recommendation': recommendation
            }
            
            # Add AI-powered analysis if available
            if self.ai_advisor.is_available():
                try:
                    ai_analysis = self.ai_advisor.analyze_stock(symbol, stock_data)
                    analysis_result['ai_analysis'] = ai_analysis
                    
                    # Enhance recommendation with AI insights
                    if ai_analysis['suitability_score'] > 7:
                        analysis_result['recommendation']['ai_enhanced'] = True
                        analysis_result['recommendation']['confidence'] = max(
                            analysis_result['recommendation'].get('confidence', 0.5),
                            ai_analysis['confidence']
                        )
                        
                        # Add AI recommendation for strike price if different
                        if ai_analysis['recommendation']['strike_price']:
                            analysis_result['recommendation']['ai_strike_price'] = ai_analysis['recommendation']['strike_price']
                            analysis_result['recommendation']['ai_days_to_expiration'] = ai_analysis['recommendation']['days_to_expiration']
                    
                    logger.info(f"Added AI-powered analysis for {symbol}")
                except Exception as e:
                    logger.error(f"Error adding AI analysis for {symbol}: {str(e)}")
                    # Continue without AI analysis
            
            return analysis_result
        
        except Exception as e:
            logger.error(f"Error analyzing stock {symbol}: {str(e)}")
            return None
    
    def _calculate_technical_indicators(self, df):
        """
        Calculate technical indicators for a stock DataFrame.
        
        Args:
            df (DataFrame): DataFrame with date, price, and volume
            
        Returns:
            DataFrame: Original DataFrame with added technical indicators
        """
        # Simple Moving Averages
        df['sma_20'] = df['price'].rolling(window=20).mean()
        df['sma_50'] = df['price'].rolling(window=50).mean()
        
        # Relative Strength Index (RSI)
        delta = df['price'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Moving Average Convergence Divergence (MACD)
        ema_12 = df['price'].ewm(span=12, adjust=False).mean()
        ema_26 = df['price'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['price'].rolling(window=20).mean()
        df['bb_std'] = df['price'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        
        # Drop NaN values resulting from rolling calculations
        df = df.dropna()
        
        return df
    
    def _evaluate_buy_signal(self, df):
        """
        Evaluate if the stock is a good buy based on technical indicators.
        
        Args:
            df (DataFrame): DataFrame with technical indicators
            
        Returns:
            bool: True if the stock shows a buy signal, False otherwise
        """
        # Get the latest indicator values
        latest = df.iloc[-1]
        
        # Check for bullish signals
        price_above_sma_20 = latest['price'] > latest['sma_20']
        sma_20_above_sma_50 = latest['sma_20'] > latest['sma_50']
        rsi_favorable = 40 < latest['rsi'] < 70  # Not overbought or oversold
        macd_bullish = latest['macd'] > latest['macd_signal']
        
        # Calculate a simple score based on these signals
        score = sum([price_above_sma_20, sma_20_above_sma_50, rsi_favorable, macd_bullish])
        
        # Return True if majority of signals are positive
        return score >= 3
    
    def _find_optimal_calls(self, current_price, calls, volatility):
        """
        Find optimal call options for a covered call strategy.
        
        Args:
            current_price (float): Current stock price
            calls (list): List of available call options
            volatility (float): Stock volatility percentage
            
        Returns:
            list: Recommended call options sorted by score
        """
        if not calls:
            # Return a placeholder recommendation based on theoretical options
            # This is useful when the API doesn't provide real options data
            return self._generate_theoretical_calls(current_price, volatility)
        
        recommendations = []
        
        for call in calls:
            # Calculate option metrics
            strike_price = call['strike']
            premium = (call['bid'] + call['ask']) / 2
            days_to_expiry = (datetime.fromisoformat(call['expiry'].replace('Z', '+00:00')) - datetime.now()).days
            
            # Calculate potential return
            potential_return = (premium / current_price) * 100  # Premium yield %
            potential_total_return = ((strike_price - current_price + premium) / current_price) * 100  # Total return if assigned
            
            # Calculate annualized return (if assigned)
            annualized_factor = 365 / max(days_to_expiry, 1)
            annualized_return = potential_total_return * annualized_factor
            
            # Calculate score based on metrics (higher is better)
            # Favor options with higher annualized returns and reasonable days to expiry
            score = annualized_return * 0.6 + (1/max(days_to_expiry, 1)) * 30 * 0.4
            
            # Adjust score based on IV and delta
            if 'iv' in call and 'delta' in call:
                # Higher IV and delta around 0.3-0.4 are favorable for covered calls
                iv_score = min(call['iv'] / 50, 1.5)  # Normalize IV, cap at 1.5
                delta_score = 1 - abs(call['delta'] - 0.35) * 2  # Optimal delta around 0.35
                
                score = score * 0.7 + iv_score * 0.15 + delta_score * 0.15
            
            recommendations.append({
                'strike': strike_price,
                'premium': premium,
                'days_to_expiry': days_to_expiry,
                'potential_return': potential_return,
                'potential_total_return': potential_total_return,
                'annualized_return': annualized_return,
                'score': score,
                'bid': call.get('bid', 0),
                'ask': call.get('ask', 0),
                'delta': call.get('delta', 'N/A'),
                'iv': call.get('iv', 'N/A')
            })
        
        # Sort by score (highest first)
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top 3 recommendations
        return recommendations[:3]
    
    def _generate_theoretical_calls(self, current_price, volatility):
        """
        Generate theoretical call options when real data is not available.
        
        Args:
            current_price (float): Current stock price
            volatility (float): Stock volatility percentage
            
        Returns:
            list: Theoretical call options
        """
        recommendations = []
        
        # Generate a few strike prices around the current price
        strike_factors = [1.05, 1.10, 1.15]  # 5%, 10%, and 15% OTM
        expiry_days = [30, 45, 60]  # Different expiry periods
        
        for strike_factor in strike_factors:
            for days in expiry_days:
                strike_price = round(current_price * strike_factor, 2)
                
                # Use a simple model to estimate premium
                # Higher volatility and more days = higher premium
                premium_factor = (volatility / 100) * (days / 30) * 0.2
                premium = round(current_price * premium_factor, 2)
                
                # Calculate returns
                potential_return = (premium / current_price) * 100
                potential_total_return = ((strike_price - current_price + premium) / current_price) * 100
                annualized_return = potential_total_return * (365 / days)
                
                # Calculate score
                score = annualized_return * 0.6 + (1/days) * 30 * 0.4
                
                # Add theoretical delta and IV
                delta = max(0.1, 0.5 - (strike_price - current_price) / current_price)
                iv = volatility * (1 + (strike_price - current_price) / current_price * 0.5)
                
                recommendations.append({
                    'strike': strike_price,
                    'premium': premium,
                    'days_to_expiry': days,
                    'potential_return': potential_return,
                    'potential_total_return': potential_total_return,
                    'annualized_return': annualized_return,
                    'score': score,
                    'bid': premium - 0.05,
                    'ask': premium + 0.05,
                    'delta': round(delta, 2),
                    'iv': round(iv, 2),
                    'theoretical': True  # Flag to indicate this is a theoretical option
                })
        
        # Sort by score (highest first)
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top 3 recommendations
        return recommendations[:3]
    
    def _generate_recommendation(self, buy_signal, call_recommendations, volatility):
        """
        Generate an overall recommendation based on analysis.
        
        Args:
            buy_signal (bool): Whether the stock shows a buy signal
            call_recommendations (list): Recommended call options
            volatility (float): Stock volatility percentage
            
        Returns:
            dict: Overall recommendation with action and reason
        """
        if not buy_signal:
            return {
                'action': 'HOLD',
                'reason': 'Technical indicators do not support a buy at this time.'
            }
        
        if not call_recommendations:
            return {
                'action': 'BUY_STOCK_ONLY',
                'reason': 'Technical indicators support buying the stock, but no suitable call options found.'
            }
        
        # Check if volatility is too low for covered calls to be profitable
        if volatility < 15:
            return {
                'action': 'BUY_STOCK_ONLY',
                'reason': 'Stock volatility is too low for profitable covered calls.'
            }
        
        # Check the best call option's metrics
        best_call = call_recommendations[0]
        
        if best_call['annualized_return'] < 12:
            return {
                'action': 'BUY_STOCK_ONLY',
                'reason': 'Call option premiums are too low for a profitable covered call strategy.'
            }
        
        return {
            'action': 'COVERED_CALL',
            'reason': f"Technical indicators are positive and covered call can generate {best_call['annualized_return']:.2f}% annualized return.",
            'recommended_strike': best_call['strike'],
            'days_to_expiry': best_call['days_to_expiry']
        }
    
    def find_covered_call_opportunities(self, symbols):
        """
        Find covered call opportunities from a list of stock symbols.
        
        Args:
            symbols (list): List of stock symbols to analyze
            
        Returns:
            list: Opportunities sorted by potential return
        """
        opportunities = []
        
        for symbol in symbols:
            analysis = self.analyze_stock(symbol)
            
            if analysis and analysis['recommendation']['action'] == 'COVERED_CALL':
                best_call = analysis['call_recommendations'][0]
                
                opportunity = {
                    'symbol': symbol,
                    'current_price': analysis['current_price'],
                    'recommendation': analysis['recommendation'],
                    'best_call': best_call,
                    'technical_indicators': analysis['technical_indicators'],
                    'score': best_call['score']
                }
                
                opportunities.append(opportunity)
        
        # Sort opportunities by score (highest first)
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        return opportunities
