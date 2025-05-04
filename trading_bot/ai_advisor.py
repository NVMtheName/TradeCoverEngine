import os
import json
import logging
from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)

class AIAdvisor:
    """
    AI-powered advisor for trading strategies and stock analysis.
    Integrates with OpenAI's GPT models to provide enhanced market insights.
    """
    
    def __init__(self):
        """
        Initialize the AI advisor with OpenAI client.
        """
        try:
            self.api_key = os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                logger.warning("OpenAI API key not found. AI advisor will not be available.")
                self.client = None
            else:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("AI advisor initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing AI advisor: {str(e)}")
            self.client = None
    
    def is_available(self):
        """
        Check if AI advisor is available (has valid API key).
        
        Returns:
            bool: True if advisor is available, False otherwise
        """
        return self.client is not None
    
    def analyze_stock(self, symbol, price_history, financial_data=None):
        """
        Generate AI-powered analysis for a stock based on price history and financial data.
        
        Args:
            symbol (str): Stock symbol
            price_history (dict): Historical price data
            financial_data (dict, optional): Additional financial metrics
            
        Returns:
            dict: AI analysis with insights and recommendations
        """
        if not self.is_available():
            return {
                "ai_insights": "AI advisor not available. Please provide an OpenAI API key.",
                "recommendation": None,
                "confidence": 0,
                "supporting_data": None
            }
        
        try:
            # Prepare context for the AI
            context = {
                "symbol": symbol,
                "price_history": {
                    "dates": price_history.get("dates", [])[-30:],  # Last 30 data points
                    "prices": price_history.get("prices", [])[-30:],
                    "volumes": price_history.get("volumes", [])[-30:]
                }
            }
            
            if financial_data:
                context["financial_data"] = financial_data
                
            # Current price and basic stats
            if context["price_history"]["prices"]:
                current_price = context["price_history"]["prices"][-1]
                price_30d_ago = context["price_history"]["prices"][0] if len(context["price_history"]["prices"]) >= 30 else current_price
                price_change_pct = ((current_price - price_30d_ago) / price_30d_ago * 100) if price_30d_ago else 0
                context["current_price"] = current_price
                context["price_change_30d_pct"] = price_change_pct
                
            # Create prompt for GPT
            prompt = f"""Analyze the stock {symbol} as a potential covered call opportunity based on the following data:

1. Current Price: ${context.get('current_price', 'N/A')}
2. 30-Day Price Change: {context.get('price_change_30d_pct', 'N/A'):.2f}%
3. Price History (Last 30 days): {context['price_history']['prices']}

Provide the following in a structured JSON format:
1. A brief analysis of recent price action and volatility
2. Evaluation of whether this stock is suitable for a covered call strategy
3. Recommendation for strike price and expiration if applicable
4. Confidence score (0-1) in your recommendation
5. Potential risks and rewards

JSON format should include: analysis, suitability_score (0-10), strike_price_recommendation, days_to_expiration, confidence, risks, rewards"""
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2  # Lower temperature for more focused/analytical responses
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            return {
                "ai_insights": result.get("analysis", "No analysis provided"),
                "suitability_score": result.get("suitability_score", 0),
                "recommendation": {
                    "strike_price": result.get("strike_price_recommendation"),
                    "days_to_expiration": result.get("days_to_expiration")
                },
                "confidence": result.get("confidence", 0),
                "risks": result.get("risks", []),
                "rewards": result.get("rewards", [])
            }
            
        except Exception as e:
            logger.error(f"Error generating AI analysis for {symbol}: {str(e)}")
            return {
                "ai_insights": f"Error generating AI analysis: {str(e)}",
                "recommendation": None,
                "confidence": 0,
                "supporting_data": None
            }
    
    def generate_market_summary(self, market_data, watchlist_performance):
        """
        Generate a natural language summary of current market conditions and watchlist performance.
        
        Args:
            market_data (dict): General market indicators and data
            watchlist_performance (dict): Performance metrics for watchlist stocks
            
        Returns:
            str: Natural language market summary
        """
        if not self.is_available():
            return "AI market summary not available. Please provide an OpenAI API key."
        
        try:
            # Prepare context
            context = {
                "market_data": market_data,
                "watchlist": watchlist_performance
            }
            
            # Create prompt
            symbols = ", ".join(watchlist_performance.keys())
            
            prompt = f"""Generate a concise market summary and analysis of the following watchlist stocks: {symbols}

Watchlist performance data:
{json.dumps(watchlist_performance, indent=2)}

Market data:
{json.dumps(market_data, indent=2)}

Provide a professional 3-paragraph summary that includes:
1. Overall market sentiment and notable market movements
2. Specific analysis of the watchlist stocks, highlighting opportunities or concerns
3. Tactical recommendations for trading these stocks in the current market environment

Your analysis should be data-driven but presented in clear, jargon-free language."""
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating market summary: {str(e)}")
            return f"Error generating market summary: {str(e)}"
    
    def optimize_strategy_parameters(self, strategy_type, historical_performance, risk_preference):
        """
        Optimize trading strategy parameters based on historical performance and risk preference.
        
        Args:
            strategy_type (str): Type of trading strategy ('covered_call', 'iron_condor', etc.)
            historical_performance (dict): Historical performance metrics
            risk_preference (str): Risk preference ('conservative', 'moderate', 'aggressive')
            
        Returns:
            dict: Optimized strategy parameters
        """
        if not self.is_available():
            return {
                "parameters": {},
                "explanation": "AI strategy optimization not available. Please provide an OpenAI API key."
            }
        
        try:
            # Prepare prompt based on strategy type
            strategy_prompts = {
                "covered_call": f"""Optimize parameters for a covered call strategy based on the following historical performance data:

{json.dumps(historical_performance, indent=2)}

The trader's risk preference is: {risk_preference}

Provide the following optimized parameters in JSON format:
1. profit_target_percentage: Target profit percentage to close early
2. stop_loss_percentage: Stop loss percentage to limit losses
3. delta_target: Target option delta (0.2-0.4 is typical)
4. days_to_expiration: Recommended days until expiration
5. otm_percentage: Percentage out-of-the-money for strike selection

Include a brief explanation for each parameter.""",
                
                "iron_condor": f"""Optimize parameters for an iron condor options strategy based on the following historical performance data:

{json.dumps(historical_performance, indent=2)}

The trader's risk preference is: {risk_preference}

Provide the following optimized parameters in JSON format:
1. profit_target_percentage: Target profit percentage to close early
2. stop_loss_percentage: Stop loss percentage to limit losses
3. call_wing_delta: Target delta for call wing (0.1-0.3 typical)
4. put_wing_delta: Target delta for put wing (0.1-0.3 typical)
5. days_to_expiration: Recommended days until expiration
6. wing_width_percentage: Percentage width between short and long strikes

Include a brief explanation for each parameter."""
            }
            
            prompt = strategy_prompts.get(strategy_type, f"Optimize trading parameters for {strategy_type} strategy with {risk_preference} risk preference.")
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Extract parameters and explanations
            parameters = {}
            explanations = {}
            
            for key, value in result.items():
                if key.endswith("_explanation"):
                    base_key = key.replace("_explanation", "")
                    explanations[base_key] = value
                else:
                    parameters[key] = value
            
            return {
                "parameters": parameters,
                "explanations": explanations
            }
            
        except Exception as e:
            logger.error(f"Error optimizing {strategy_type} strategy: {str(e)}")
            return {
                "parameters": {},
                "explanation": f"Error optimizing strategy: {str(e)}"
            }
