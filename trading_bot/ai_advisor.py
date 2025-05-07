import os
import json
import logging
import time
import statistics
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)

class AIModelConfig:
    """Configuration class for different AI models and their capabilities"""
    
    # Model definitions with capabilities and use cases
    MODELS = {
        "gpt-4o": {
            "description": "Premium model with highest reasoning capabilities",
            "use_cases": ["complex_analysis", "strategy_optimization", "market_forecasting"],
            "features": ["multimodal", "high_reasoning"],
            "max_tokens": 4096,
            "default_temp": 0.2,
            "is_premium": True
        },
        "gpt-3.5-turbo": {
            "description": "Balanced model for routine analysis tasks",
            "use_cases": ["routine_analysis", "data_summarization", "pattern_recognition"],
            "features": ["fast_response", "cost_effective"],
            "max_tokens": 4096,
            "default_temp": 0.3,
            "is_premium": False
        }
    }
    
    # Task-specific model recommendations
    TASK_MODEL_MAPPING = {
        "stock_analysis": "gpt-4o",
        "market_summary": "gpt-3.5-turbo",
        "strategy_optimization": "gpt-4o",
        "stock_screening": "gpt-3.5-turbo",
        "position_evaluation": "gpt-4o",
        "risk_assessment": "gpt-4o",
        "news_analysis": "gpt-3.5-turbo"
    }
    
    @classmethod
    def get_model_for_task(cls, task: str, allow_premium: bool = True) -> str:
        """Get the recommended model for a specific task"""
        recommended_model = cls.TASK_MODEL_MAPPING.get(task, "gpt-4o")
        
        # Fall back to non-premium model if premium not allowed
        if not allow_premium and cls.MODELS.get(recommended_model, {}).get("is_premium", False):
            return "gpt-3.5-turbo"
            
        return recommended_model
    
    @classmethod
    def get_temp_for_task(cls, task: str) -> float:
        """Get the recommended temperature setting for a task"""
        task_temp_map = {
            "stock_analysis": 0.2,         # More precise
            "market_summary": 0.4,         # More creative
            "strategy_optimization": 0.1,  # Very precise
            "stock_screening": 0.3,        # Balanced
            "position_evaluation": 0.2,    # More precise
            "risk_assessment": 0.1,        # Very precise
            "news_analysis": 0.4           # More creative
        }
        return task_temp_map.get(task, 0.3)


class AIAdvisor:
    """
    Enhanced AI-powered advisor for trading strategies and stock analysis.
    Integrates with multiple OpenAI models to provide sophisticated market insights
    and trading recommendations with model ensemble techniques.
    """
    
    def __init__(self):
        """
        Initialize the AI advisor with OpenAI client and multiple model support.
        """
        try:
            self.api_key = os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                logger.warning("OpenAI API key not found. AI advisor will not be available.")
                self.client = None
            else:
                self.client = OpenAI(api_key=self.api_key)
                
                # Test available models and capabilities
                self.available_models = self._test_model_availability()
                
                # Set up request tracking for rate limiting
                self.request_timestamps = []
                self.max_requests_per_minute = 25  # Default rate limit
                
                # Cache for model responses to reduce API calls
                self.response_cache = {}
                self.cache_ttl = 1800  # 30 minutes cache lifetime
                
                logger.info(f"AI advisor initialized with {len(self.available_models)} available models.")
        except Exception as e:
            logger.error(f"Error initializing AI advisor: {str(e)}")
            self.client = None
            self.available_models = []
    
    def _test_model_availability(self) -> List[str]:
        """Test which models are available with the current API key"""
        available_models = []
        
        # List of priority models to test
        test_models = ["gpt-4o", "gpt-3.5-turbo"]
        
        for model in test_models:
            try:
                # Simple test prompt to verify model access
                self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5
                )
                available_models.append(model)
                logger.info(f"Model {model} is available")
            except Exception as e:
                if "not available" in str(e).lower() or "no access" in str(e).lower():
                    logger.warning(f"Model {model} is not available with current API key: {str(e)}")
                else:
                    logger.error(f"Error testing model {model}: {str(e)}")
        
        return available_models
    
    def is_available(self) -> bool:
        """
        Check if AI advisor is available (has valid API key and at least one working model).
        
        Returns:
            bool: True if advisor is available, False otherwise
        """
        return self.client is not None and len(self.available_models) > 0
    
    def _execute_model_request(self, model: str, messages: List[Dict[str, str]], 
                          json_response: bool = False, temperature: float = 0.2,
                          cache_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a request to a specific OpenAI model with rate limiting and caching.
        
        Args:
            model: Model name
            messages: List of message dictionaries for the chat API
            json_response: Whether to format response as JSON
            temperature: Creativity setting (0-1)
            cache_key: Optional key for caching responses
            
        Returns:
            Dict containing response and metadata
        """
        # Check if we should use the cache
        if cache_key and cache_key in self.response_cache:
            cache_entry = self.response_cache[cache_key]
            cache_time = cache_entry.get("timestamp", 0)
            if time.time() - cache_time < self.cache_ttl:
                logger.info(f"Using cached response for {cache_key}")
                return cache_entry["response"]
        
        # Implement basic rate limiting
        current_time = time.time()
        self.request_timestamps = [ts for ts in self.request_timestamps if current_time - ts < 60]
        
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            wait_time = 60 - (current_time - self.request_timestamps[0])
            logger.warning(f"Rate limit approaching, waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
        
        # Add current request to tracking
        self.request_timestamps.append(time.time())
        
        # Make sure model is available, fallback if not
        if model not in self.available_models:
            fallback_model = "gpt-3.5-turbo" if "gpt-3.5-turbo" in self.available_models else self.available_models[0] if self.available_models else None
            if not fallback_model:
                raise ValueError("No available models to execute request")
            logger.warning(f"Model {model} not available, falling back to {fallback_model}")
            model = fallback_model
        
        # Execute the request
        try:
            start_time = time.time()
            
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            
            # Add response format if JSON is requested
            if json_response:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**kwargs)
            
            execution_time = time.time() - start_time
            
            # Extract the content
            content = response.choices[0].message.content
            
            # Parse JSON if requested
            result = json.loads(content) if json_response else content
            
            # Create full response object with metadata
            full_response = {
                "result": result,
                "model": model,
                "execution_time": execution_time,
                "tokens": response.usage.total_tokens if hasattr(response, 'usage') else None
            }
            
            # Cache the response if a cache key was provided
            if cache_key:
                self.response_cache[cache_key] = {
                    "response": full_response,
                    "timestamp": time.time()
                }
            
            return full_response
            
        except Exception as e:
            logger.error(f"Error executing model request: {str(e)}")
            raise
    
    def analyze_stock(self, symbol, price_history, financial_data=None, use_ensemble=True):
        """
        Generate AI-powered analysis for a stock based on price history and financial data.
        
        Args:
            symbol (str): Stock symbol
            price_history (dict): Historical price data
            financial_data (dict, optional): Additional financial metrics
            use_ensemble (bool): Whether to use multiple models for enhanced analysis
            
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
            
            # Cache key for this analysis request
            cache_key = f"stock_analysis_{symbol}_{current_price}_{price_change_pct}"
            
            # Create base prompt for GPT
            base_prompt = f"""Analyze the stock {symbol} as a potential covered call opportunity based on the following data:

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

            # If financial data is available, enhance the prompt
            if financial_data:
                financial_prompt = f"""
Additional financial data:
- PE Ratio: {financial_data.get('pe_ratio', 'N/A')}
- Dividend Yield: {financial_data.get('dividend_yield', 'N/A')}%
- Market Cap: ${financial_data.get('market_cap', 'N/A')}B
- 52-Week Range: ${financial_data.get('year_low', 'N/A')} - ${financial_data.get('year_high', 'N/A')}
- Beta: {financial_data.get('beta', 'N/A')}
- Average Volume: {financial_data.get('avg_volume', 'N/A')}M

Please incorporate this financial data into your analysis and recommendations.
"""
                base_prompt += financial_prompt
            
            # Single model approach
            if not use_ensemble or len(self.available_models) == 1:
                model = AIModelConfig.get_model_for_task("stock_analysis", True)
                
                response = self._execute_model_request(
                    model=model,
                    messages=[{"role": "user", "content": base_prompt}],
                    json_response=True,
                    temperature=AIModelConfig.get_temp_for_task("stock_analysis"),
                    cache_key=cache_key
                )
                
                result = response["result"]
                
                return {
                    "ai_insights": result.get("analysis", "No analysis provided"),
                    "suitability_score": result.get("suitability_score", 0),
                    "recommendation": {
                        "strike_price": result.get("strike_price_recommendation"),
                        "days_to_expiration": result.get("days_to_expiration")
                    },
                    "confidence": result.get("confidence", 0),
                    "risks": result.get("risks", []),
                    "rewards": result.get("rewards", []),
                    "model_info": {
                        "model": response.get("model"),
                        "execution_time": response.get("execution_time"),
                        "tokens": response.get("tokens")
                    }
                }
            
            # Ensemble approach - use multiple models for different aspects of analysis
            else:
                # Technical analysis with GPT-4o
                technical_prompt = base_prompt + "\nFocus heavily on technical analysis, price patterns, and volatility metrics."
                technical_response = self._execute_model_request(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": technical_prompt}],
                    json_response=True,
                    temperature=0.2,
                    cache_key=f"{cache_key}_technical"
                )
                
                # Fundamental analysis with GPT-3.5 (faster, more cost effective)
                fundamental_prompt = f"""Analyze the fundamental aspects of stock {symbol} based on this financial data:
                
{json.dumps(financial_data, indent=2) if financial_data else "No financial data provided"}

Focus only on fundamental analysis - valuation metrics, company financials, and dividend potential.
Return a JSON object with: fundamental_analysis (text), fundamental_score (0-10), dividend_outlook (text)
"""
                
                fundamental_response = self._execute_model_request(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": fundamental_prompt}],
                    json_response=True,
                    temperature=0.3,
                    cache_key=f"{cache_key}_fundamental"
                )
                
                # Combine the results
                technical_result = technical_response["result"]
                fundamental_result = fundamental_response["result"]
                
                # Calculate combined suitability score
                tech_score = float(technical_result.get("suitability_score", 5))
                fund_score = float(fundamental_result.get("fundamental_score", 5)) if "fundamental_score" in fundamental_result else 5
                combined_score = (tech_score * 0.7) + (fund_score * 0.3)  # Weight technical more heavily
                
                # Combine analyses
                technical_analysis = technical_result.get("analysis", "")
                fundamental_analysis = fundamental_result.get("fundamental_analysis", "")
                
                combined_analysis = f"""Technical Analysis: {technical_analysis}

Fundamental Analysis: {fundamental_analysis}"""
                
                # Create combined result
                return {
                    "ai_insights": combined_analysis,
                    "suitability_score": round(combined_score, 1),
                    "recommendation": {
                        "strike_price": technical_result.get("strike_price_recommendation"),
                        "days_to_expiration": technical_result.get("days_to_expiration")
                    },
                    "confidence": technical_result.get("confidence", 0),
                    "risks": technical_result.get("risks", []),
                    "rewards": technical_result.get("rewards", []),
                    "fundamental_outlook": fundamental_result.get("dividend_outlook", ""),
                    "model_info": {
                        "ensemble": True,
                        "technical_model": technical_response.get("model"),
                        "fundamental_model": fundamental_response.get("model"),
                        "total_execution_time": technical_response.get("execution_time", 0) + fundamental_response.get("execution_time", 0)
                    }
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
            cache_key = f"market_summary_{symbols}_{int(time.time() / 1800)}"  # Cache key based on symbols and time block (30 min)
            
            # Base prompt - used for both models
            base_prompt = f"""Generate a market summary and analysis of these watchlist stocks: {symbols}

Watchlist performance data:
{json.dumps(watchlist_performance, indent=2)}

Market data:
{json.dumps(market_data, indent=2)}"""

            # Check if we should use a single model or ensemble
            if len(self.available_models) > 1:
                # Ensemble approach - different models for different aspects
                
                # Broad market analysis (GPT-3.5 is efficient for this)
                market_prompt = base_prompt + """

Focus only on broad market conditions. Provide a single paragraph that covers:
1. Overall market sentiment
2. Key index movements
3. Significant macro trends affecting the market
4. Notable sector rotations or movements"""
                
                market_response = self._execute_model_request(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": market_prompt}],
                    json_response=False,
                    temperature=0.4,
                    cache_key=f"{cache_key}_market"
                )
                
                # Stock-specific analysis (GPT-4o for deeper reasoning)
                stock_prompt = base_prompt + f"""

Focus only on analyzing the specific watchlist stocks: {symbols}. Provide:
1. Individual assessment of each stock's performance
2. Highlight patterns or anomalies among these stocks
3. Identify which stocks present the best trading opportunities
4. Evaluate relative strength/weakness among these stocks compared to the broader market"""
                
                stock_response = self._execute_model_request(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": stock_prompt}],
                    json_response=False,
                    temperature=0.3,
                    cache_key=f"{cache_key}_stock"
                )
                
                # Strategy recommendations (GPT-4o for more sophisticated tactics)
                strategy_prompt = base_prompt + f"""

Focus only on tactical trading recommendations. Provide:
1. Specific trading strategies suitable for these stocks in the current market
2. Options strategies that might be appropriate for each stock
3. Suggested entry/exit parameters based on technical levels
4. Risk management considerations"""
                
                strategy_response = self._execute_model_request(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": strategy_prompt}],
                    json_response=False,
                    temperature=0.2,
                    cache_key=f"{cache_key}_strategy"
                )
                
                # Combine all sections into a comprehensive report
                combined_summary = f"""# Market Analysis Report
                
## Market Overview
{market_response["result"]}

## Watchlist Analysis
{stock_response["result"]}

## Trading Recommendations
{strategy_response["result"]}

*Analysis generated using ensemble AI approach*
"""
                
                return combined_summary
            
            else:
                # Single model approach - simpler unified prompt
                unified_prompt = base_prompt + """

Provide a professional 3-paragraph summary that includes:
1. Overall market sentiment and notable market movements
2. Specific analysis of the watchlist stocks, highlighting opportunities or concerns
3. Tactical recommendations for trading these stocks in the current market environment

Your analysis should be data-driven but presented in clear, jargon-free language."""
                
                model = AIModelConfig.get_model_for_task("market_summary", True)
                
                response = self._execute_model_request(
                    model=model,
                    messages=[{"role": "user", "content": unified_prompt}],
                    json_response=False,
                    temperature=AIModelConfig.get_temp_for_task("market_summary"),
                    cache_key=cache_key
                )
                
                return response["result"]
            
        except Exception as e:
            logger.error(f"Error generating market summary: {str(e)}")
            return f"Error generating market summary: {str(e)}"
    
    def optimize_strategy_parameters(self, strategy_type, historical_performance, risk_preference):
        """
        Optimize trading strategy parameters based on historical performance and risk preference.
        Uses multiple models to analyze different aspects of strategy optimization.
        
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
            # Create cache key for this strategy optimization
            perf_hash = hash(json.dumps(historical_performance))
            cache_key = f"strategy_opt_{strategy_type}_{risk_preference}_{perf_hash}"
            
            # Base prompts dictionary for different strategy types
            base_strategy_prompts = {
                "covered_call": f"""Historical performance data for covered call strategy:
{json.dumps(historical_performance, indent=2)}

The trader's risk preference is: {risk_preference}""",
                
                "iron_condor": f"""Historical performance data for iron condor strategy:
{json.dumps(historical_performance, indent=2)}

The trader's risk preference is: {risk_preference}""",
                
                "wheel": f"""Historical performance data for wheel strategy:
{json.dumps(historical_performance, indent=2)}

The trader's risk preference is: {risk_preference}""",
                
                "collar": f"""Historical performance data for collar strategy:
{json.dumps(historical_performance, indent=2)}

The trader's risk preference is: {risk_preference}"""
            }
            
            base_prompt = base_strategy_prompts.get(
                strategy_type, 
                f"""Historical performance data for {strategy_type} strategy:
{json.dumps(historical_performance, indent=2)}

The trader's risk preference is: {risk_preference}"""
            )
            
            # Use model ensemble approach if multiple models are available
            if len(self.available_models) > 1:
                # Risk analysis with GPT-4o for sophisticated risk assessment
                risk_prompt = base_prompt + """
                
Focus only on risk parameters optimization. Based on historical performance and risk preference, provide:
1. Recommended stop_loss_percentage (percentage to trigger stop loss)
2. Position sizing guidelines
3. Margin of safety factors

Return result as JSON with parameters and explanations."""
                
                risk_response = self._execute_model_request(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": risk_prompt}],
                    json_response=True,
                    temperature=0.1,  # Very precise for risk management
                    cache_key=f"{cache_key}_risk"
                )
                
                # Profit target analysis with GPT-3.5 (efficient for straightforward calculations)
                profit_prompt = base_prompt + """
                
Focus only on profit target optimization. Based on historical performance and risk preference, provide:
1. Recommended profit_target_percentage (percentage to take profits)
2. Optimal profit taking schedule
3. Scaling out strategy

Return result as JSON with parameters and explanations."""
                
                profit_response = self._execute_model_request(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": profit_prompt}],
                    json_response=True,
                    temperature=0.2,
                    cache_key=f"{cache_key}_profit"
                )
                
                # Strategy-specific parameters with GPT-4o (requires deep reasoning)
                strategy_specific_prompt = base_prompt + f"""
                
Focus only on strategy-specific parameter optimization for {strategy_type}. Based on the data, provide:
"""
                
                # Add strategy-specific parameters based on strategy type
                if strategy_type == "covered_call":
                    strategy_specific_prompt += """
1. delta_target: Target option delta (0.2-0.4 is typical)
2. days_to_expiration: Recommended days until expiration
3. otm_percentage: Percentage out-of-the-money for strike selection
"""
                elif strategy_type == "iron_condor":
                    strategy_specific_prompt += """
1. call_wing_delta: Target delta for call wing (0.1-0.3 typical)
2. put_wing_delta: Target delta for put wing (0.1-0.3 typical)
3. days_to_expiration: Recommended days until expiration
4. wing_width_percentage: Percentage width between short and long strikes
"""
                elif strategy_type == "wheel":
                    strategy_specific_prompt += """
1. put_delta_target: Target delta for selling puts (0.2-0.4 typical)
2. call_delta_target: Target delta for selling calls after assignment (0.2-0.4 typical)
3. days_to_expiration: Recommended days until expiration for both puts and calls
"""
                elif strategy_type == "collar":
                    strategy_specific_prompt += """
1. call_strike_percentage: Percentage above current price for call leg
2. put_strike_percentage: Percentage below current price for put leg
3. days_to_expiration: Recommended days until expiration
4. collar_width: Total width of the collar (distance between put and call)
"""
                
                strategy_specific_prompt += """
Return result as JSON with parameters and explanations."""
                
                strategy_response = self._execute_model_request(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": strategy_specific_prompt}],
                    json_response=True,
                    temperature=0.2,
                    cache_key=f"{cache_key}_specific"
                )
                
                # Combine all parameters from different aspects
                risk_result = risk_response["result"]
                profit_result = profit_response["result"]
                strategy_result = strategy_response["result"]
                
                # Extract parameters and explanations
                parameters = {}
                explanations = {}
                
                # Process each result and extract parameters/explanations
                for result in [risk_result, profit_result, strategy_result]:
                    for key, value in result.items():
                        if key.endswith("_explanation"):
                            base_key = key.replace("_explanation", "")
                            explanations[base_key] = value
                        else:
                            parameters[key] = value
                
                return {
                    "parameters": parameters,
                    "explanations": explanations,
                    "model_info": {
                        "ensemble": True,
                        "risk_model": risk_response.get("model"),
                        "profit_model": profit_response.get("model"),
                        "strategy_model": strategy_response.get("model")
                    }
                }
                
            else:
                # Single model approach - comprehensive prompt
                comprehensive_prompt = base_prompt + f"""

Optimize ALL parameters for this {strategy_type} strategy. Provide the following in JSON format:"""
                
                # Add parameter requests based on strategy type
                if strategy_type == "covered_call":
                    comprehensive_prompt += """
1. profit_target_percentage: Target profit percentage to close early
2. stop_loss_percentage: Stop loss percentage to limit losses
3. delta_target: Target option delta (0.2-0.4 is typical)
4. days_to_expiration: Recommended days until expiration
5. otm_percentage: Percentage out-of-the-money for strike selection
"""
                elif strategy_type == "iron_condor":
                    comprehensive_prompt += """
1. profit_target_percentage: Target profit percentage to close early
2. stop_loss_percentage: Stop loss percentage to limit losses
3. call_wing_delta: Target delta for call wing (0.1-0.3 typical)
4. put_wing_delta: Target delta for put wing (0.1-0.3 typical)
5. days_to_expiration: Recommended days until expiration
6. wing_width_percentage: Percentage width between short and long strikes
"""
                elif strategy_type == "wheel":
                    comprehensive_prompt += """
1. profit_target_percentage: Target profit percentage to close early
2. stop_loss_percentage: Stop loss percentage to limit losses
3. put_delta_target: Target delta for selling puts (0.2-0.4 typical)
4. call_delta_target: Target delta for selling calls after assignment (0.2-0.4 typical)
5. days_to_expiration: Recommended days until expiration for both puts and calls
"""
                elif strategy_type == "collar":
                    comprehensive_prompt += """
1. profit_target_percentage: Target profit percentage to close early
2. stop_loss_percentage: Stop loss percentage to limit losses
3. call_strike_percentage: Percentage above current price for call leg
4. put_strike_percentage: Percentage below current price for put leg
5. days_to_expiration: Recommended days until expiration
6. collar_width: Total width of the collar (distance between put and call)
"""
                else:
                    comprehensive_prompt += """
1. profit_target_percentage: Target profit percentage to close early
2. stop_loss_percentage: Stop loss percentage to limit losses
3. days_to_expiration: Recommended days until expiration
4. Any additional parameters relevant to this strategy type
"""
                
                comprehensive_prompt += """
Include a brief explanation for each parameter."""
                
                # Use the model recommended for strategy optimization
                model = AIModelConfig.get_model_for_task("strategy_optimization", True)
                response = self._execute_model_request(
                    model=model,
                    messages=[{"role": "user", "content": comprehensive_prompt}],
                    json_response=True,
                    temperature=AIModelConfig.get_temp_for_task("strategy_optimization"),
                    cache_key=cache_key
                )
                
                result = response["result"]
                
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
                    "explanations": explanations,
                    "model_info": {
                        "model": response.get("model"),
                        "execution_time": response.get("execution_time")
                    }
                }
            
        except Exception as e:
            logger.error(f"Error optimizing {strategy_type} strategy: {str(e)}")
            return {
                "parameters": {},
                "explanation": f"Error optimizing strategy: {str(e)}"
            }
            
    def scan_market_for_stocks(self, market_data, sectors=None, min_price=10, max_price=500):
        """
        Scan the market to identify promising stocks for trading strategies.
        Uses multiple models to analyze different market aspects and combine recommendations.
        
        Args:
            market_data (dict): Overall market data and indicators
            sectors (list, optional): List of sectors to focus on
            min_price (float): Minimum stock price to consider
            max_price (float): Maximum stock price to consider
            
        Returns:
            list: Recommended stock symbols with reasoning
        """
        if not self.is_available():
            return []
        
        try:
            # Create a unique cache key for this scan
            sectors_hash = hash(str(sorted(sectors))) if sectors else 0
            cache_key = f"stock_scan_{min_price}_{max_price}_{sectors_hash}_{int(time.time() / 3600)}"  # Cache for 1 hour
            
            # Common text for all prompts
            sectors_text = f"focusing on these sectors: {', '.join(sectors)}" if sectors else "across all market sectors"
            
            # Base prompt template
            base_prompt = f"""Market context:
{json.dumps(market_data, indent=2)}

Find stocks that meet these criteria:
1. Price between ${min_price} and ${max_price}
2. Good liquidity (high trading volume)
3. Moderate to high implied volatility (for better options premiums)"""

            # Check if we should use model ensemble
            if len(self.available_models) > 1:
                # Technical analysis scan with GPT-3.5-turbo (faster, good for pattern recognition)
                technical_prompt = f"""As a technical analysis expert, identify 5-7 promising stocks {sectors_text} 
based solely on technical indicators and chart patterns.

{base_prompt}

Focus specifically on:
- Recent price action and volume patterns
- Technical indicator signals (RSI, MACD, moving averages)
- Chart patterns suggesting potential entry points
- Historical volatility patterns good for options strategies

Return a JSON array of objects with the following properties for each stock:
- symbol: The stock ticker symbol
- technical_reason: Technical analysis rationale (2-3 sentences)
- best_technical_strategy: Recommended options strategy based on technical factors
- technical_confidence: Your confidence based on technical factors (0-1 scale)
"""
                
                technical_response = self._execute_model_request(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": technical_prompt}],
                    json_response=True,
                    temperature=0.3,
                    cache_key=f"{cache_key}_technical"
                )
                
                # Fundamental analysis scan with GPT-4o (deeper reasoning on fundamentals)
                fundamental_prompt = f"""As a fundamental analysis expert, identify 5-7 promising stocks {sectors_text} 
based solely on fundamental factors and business metrics.

{base_prompt}

Focus specifically on:
- Strong business fundamentals with growth potential
- Reasonable valuations relative to peers and historical averages
- Catalyst events that might drive stock appreciation
- Dividend stability and growth potential

Return a JSON array of objects with the following properties for each stock:
- symbol: The stock ticker symbol
- fundamental_reason: Fundamental analysis rationale (2-3 sentences)
- best_fundamental_strategy: Recommended options strategy based on fundamentals
- fundamental_confidence: Your confidence based on fundamental factors (0-1 scale)
"""
                
                fundamental_response = self._execute_model_request(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": fundamental_prompt}],
                    json_response=True,
                    temperature=0.3,
                    cache_key=f"{cache_key}_fundamental"
                )
                
                # Market sentiment scan with GPT-3.5-turbo
                sentiment_prompt = f"""As a market sentiment analyst, identify 5-7 promising stocks {sectors_text} 
based solely on market sentiment and news analysis.

{base_prompt}

Focus specifically on:
- Current market sentiment towards these stocks
- Recent news coverage and potential impact
- Analyst recommendations and target price changes
- Options market sentiment (call/put ratios, implied volatility)

Return a JSON array of objects with the following properties for each stock:
- symbol: The stock ticker symbol
- sentiment_reason: Sentiment analysis rationale (2-3 sentences)
- best_sentiment_strategy: Recommended options strategy based on sentiment
- sentiment_confidence: Your confidence based on sentiment factors (0-1 scale)
"""
                
                sentiment_response = self._execute_model_request(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": sentiment_prompt}],
                    json_response=True,
                    temperature=0.4,
                    cache_key=f"{cache_key}_sentiment"
                )
                
                # Extract results from each analysis
                technical_stocks = technical_response["result"].get("stocks", [])
                if not technical_stocks and isinstance(technical_response["result"], list):
                    technical_stocks = technical_response["result"]
                    
                fundamental_stocks = fundamental_response["result"].get("stocks", [])
                if not fundamental_stocks and isinstance(fundamental_response["result"], list):
                    fundamental_stocks = fundamental_response["result"]
                    
                sentiment_stocks = sentiment_response["result"].get("stocks", [])
                if not sentiment_stocks and isinstance(sentiment_response["result"], list):
                    sentiment_stocks = sentiment_response["result"]
                
                # Create a map of all stocks from all sources
                stock_map = {}
                
                # Process technical stocks
                for stock in technical_stocks:
                    symbol = stock.get("symbol")
                    if not symbol:
                        continue
                        
                    if symbol not in stock_map:
                        stock_map[symbol] = {
                            "symbol": symbol,
                            "analyses": [],
                            "strategies": [],
                            "confidence_scores": []
                        }
                    
                    stock_map[symbol]["analyses"].append(stock.get("technical_reason", ""))
                    stock_map[symbol]["strategies"].append(stock.get("best_technical_strategy", ""))
                    stock_map[symbol]["confidence_scores"].append(float(stock.get("technical_confidence", 0.5)))
                    
                # Process fundamental stocks
                for stock in fundamental_stocks:
                    symbol = stock.get("symbol")
                    if not symbol:
                        continue
                        
                    if symbol not in stock_map:
                        stock_map[symbol] = {
                            "symbol": symbol,
                            "analyses": [],
                            "strategies": [],
                            "confidence_scores": []
                        }
                    
                    stock_map[symbol]["analyses"].append(stock.get("fundamental_reason", ""))
                    stock_map[symbol]["strategies"].append(stock.get("best_fundamental_strategy", ""))
                    stock_map[symbol]["confidence_scores"].append(float(stock.get("fundamental_confidence", 0.5)))
                    
                # Process sentiment stocks
                for stock in sentiment_stocks:
                    symbol = stock.get("symbol")
                    if not symbol:
                        continue
                        
                    if symbol not in stock_map:
                        stock_map[symbol] = {
                            "symbol": symbol,
                            "analyses": [],
                            "strategies": [],
                            "confidence_scores": []
                        }
                    
                    stock_map[symbol]["analyses"].append(stock.get("sentiment_reason", ""))
                    stock_map[symbol]["strategies"].append(stock.get("best_sentiment_strategy", ""))
                    stock_map[symbol]["confidence_scores"].append(float(stock.get("sentiment_confidence", 0.5)))
                
                # Convert the map to a list of final recommendations
                final_recommendations = []
                for symbol, data in stock_map.items():
                    # Only include stocks that were identified by multiple models
                    if len(data["analyses"]) >= 2:
                        # Determine most frequently suggested strategy
                        strategy_counts = {}
                        for strategy in data["strategies"]:
                            if strategy:
                                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
                        
                        best_strategy = max(strategy_counts.items(), key=lambda x: x[1])[0] if strategy_counts else "covered_call"
                        
                        # Calculate average confidence
                        avg_confidence = statistics.mean(data["confidence_scores"]) if data["confidence_scores"] else 0.5
                        
                        # Combine reasons into a comprehensive analysis
                        combined_reason = " ".join(data["analyses"])
                        
                        final_recommendations.append({
                            "symbol": symbol,
                            "reason": combined_reason,
                            "strategy": best_strategy,
                            "confidence": round(avg_confidence, 2),
                            "sources": len(data["analyses"]),  # Number of models that recommended this stock
                        })
                
                # Sort recommendations by confidence and number of sources
                final_recommendations.sort(key=lambda x: (x.get("sources", 0), x.get("confidence", 0)), reverse=True)
                
                # Limit to top 10
                final_recommendations = final_recommendations[:10]
                
                logger.info(f"AI ensemble identified {len(final_recommendations)} promising stocks")
                return final_recommendations
                
            else:
                # Single model approach - more straightforward prompting
                prompt = f"""As an AI stock picker, identify 5-10 promising stocks {sectors_text} that are good candidates for options trading strategies, particularly covered calls or cash-secured puts.

{base_prompt}

Additional criteria:
4. Stable fundamentals but with potential for growth or recovery
5. Technical indicators showing potential entry points

Return a JSON array of objects with the following properties for each stock:
- symbol: The stock ticker symbol
- reason: Brief explanation of why this stock is a good candidate (2-3 sentences)
- strategy: Recommended options strategy ('covered_call', 'cash_secured_put', 'iron_condor', etc.)
- confidence: Your confidence in the recommendation (0-1 scale)
"""
                
                model = AIModelConfig.get_model_for_task("stock_screening", True)
                response = self._execute_model_request(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    json_response=True,
                    temperature=AIModelConfig.get_temp_for_task("stock_screening"),
                    cache_key=cache_key
                )
                
                # Parse response
                result = response["result"]
                
                # Extract stock recommendations
                recommendations = result.get('stocks', [])
                if not recommendations and isinstance(result, list):
                    recommendations = result  # Handle case where response is a direct array
                    
                logger.info(f"AI advisor identified {len(recommendations)} promising stocks")
                return recommendations
            
        except Exception as e:
            logger.error(f"Error scanning market for stocks: {str(e)}")
            return []
    
    def evaluate_position_adjustment(self, position_data):
        """
        Evaluate whether a position should be adjusted based on current market conditions.
        Uses multiple models to analyze risk, technical and fundamental factors for comprehensive evaluation.
        
        Args:
            position_data (dict): Data about the position and market conditions
            
        Returns:
            dict: Adjustment recommendation
        """
        if not self.is_available():
            return {
                "action": "NO_ACTION",
                "reason": "AI advisor not available. Please provide an OpenAI API key."
            }
        
        try:
            # Extract key information from position data
            symbol = position_data.get('symbol')
            position_type = position_data.get('position', {}).get('position_type', 'unknown')
            current_price = position_data.get('current_price')
            entry_price = position_data.get('position', {}).get('entry_price')
            suggested_adjustment = position_data.get('suggested_adjustment', {})
            
            # Create cache key for this position evaluation
            position_hash = hash(f"{symbol}_{position_type}_{current_price}_{entry_price}")
            cache_key = f"position_eval_{position_hash}_{int(time.time() / 1800)}"  # Cache for 30 minutes
            
            # Base position data for all prompts
            base_prompt = f"""Position details:
- Symbol: {symbol}
- Type: {position_type}
- Entry price: ${entry_price}
- Current price: ${current_price}
- Days held: {position_data.get('position', {}).get('days_held', 'unknown')}

Suggested adjustment: {suggested_adjustment.get('action')}
Reason: {suggested_adjustment.get('reason')}"""

            # Check if we should use model ensemble
            if len(self.available_models) > 1:
                # Technical analysis evaluation with GPT-3.5-turbo
                technical_prompt = f"""As a technical analyst, evaluate this trading position from a purely technical perspective.

{base_prompt}

Focus your analysis on:
- Technical chart patterns
- Key support and resistance levels
- Technical indicators (RSI, MACD, moving averages)
- Volume patterns and momentum

Return a JSON object with these properties:
- technical_action: Recommended action ('HOLD', 'EXIT', 'ADJUST_STOP', 'ADJUST_TARGET', 'ROLL_POSITION', 'ADD_TO_POSITION')
- technical_reason: Technical analysis justifying your recommendation
- technical_confidence: Your confidence in this recommendation (0-1 scale)
"""
                
                technical_response = self._execute_model_request(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": technical_prompt}],
                    json_response=True,
                    temperature=0.2,
                    cache_key=f"{cache_key}_technical"
                )
                
                # Risk assessment with GPT-4o (requires sophisticated reasoning)
                risk_prompt = f"""As a risk management specialist, evaluate this trading position focusing solely on risk factors.

{base_prompt}

Focus your analysis on:
- Current risk/reward ratio
- Maximum potential loss vs. remaining profit potential
- Changes in volatility since entry
- Portfolio-level risk considerations
- Market regime and correlation risks

Return a JSON object with these properties:
- risk_action: Recommended action from risk perspective ('MAINTAIN_RISK', 'REDUCE_RISK', 'CLOSE_POSITION', 'HEDGE_POSITION')
- risk_reason: Risk assessment justifying your recommendation
- risk_confidence: Your confidence in this assessment (0-1 scale)
"""
                
                risk_response = self._execute_model_request(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": risk_prompt}],
                    json_response=True,
                    temperature=0.1,  # Low temperature for risk assessment
                    cache_key=f"{cache_key}_risk"
                )
                
                # Market sentiment evaluation
                sentiment_prompt = f"""As a market sentiment analyst, evaluate this trading position based on current market sentiment.

{base_prompt}

Focus your analysis on:
- Broader market sentiment and its effect on this position
- Recent news or events affecting this stock
- Analyst sentiment changes
- Options market sentiment (put/call ratio, implied volatility changes)

Return a JSON object with these properties:
- sentiment_action: Recommended action based on sentiment ('BULLISH_HOLD', 'BEARISH_EXIT', 'NEUTRAL_REDUCE', 'CONTRARIAN_ADD')
- sentiment_reason: Sentiment analysis justifying your recommendation
- sentiment_confidence: Your confidence in this assessment (0-1 scale)
"""
                
                sentiment_response = self._execute_model_request(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": sentiment_prompt}],
                    json_response=True,
                    temperature=0.3,
                    cache_key=f"{cache_key}_sentiment"
                )
                
                # Extract results
                technical_result = technical_response["result"]
                risk_result = risk_response["result"]
                sentiment_result = sentiment_response["result"]
                
                # Final recommendation synthesis with GPT-4o
                synthesis_prompt = f"""You are a master trading advisor synthesizing multiple expert opinions on a position adjustment.

The position is:
- Symbol: {symbol}
- Type: {position_type}
- Entry price: ${entry_price}
- Current price: ${current_price}

Originally suggested adjustment: {suggested_adjustment.get('action', 'None')}

Technical analysis conclusion: {technical_result.get('technical_action')}
Technical reasoning: {technical_result.get('technical_reason')}
Technical confidence: {technical_result.get('technical_confidence')}

Risk assessment conclusion: {risk_result.get('risk_action')}
Risk reasoning: {risk_result.get('risk_reason')}
Risk confidence: {risk_result.get('risk_confidence')}

Sentiment analysis conclusion: {sentiment_result.get('sentiment_action')}
Sentiment reasoning: {sentiment_result.get('sentiment_reason')}
Sentiment confidence: {sentiment_result.get('sentiment_confidence')}

Synthesize these expert opinions into a final recommendation. Return a JSON object with:
- action: Final recommended action ('ACCEPT_SUGGESTED', 'ALTERNATIVE', 'NO_ACTION')
- alternative_action: If action is 'ALTERNATIVE', specify what action to take instead
- reason: Comprehensive explanation of your final recommendation
- confidence: Overall confidence in this recommendation (0-1 scale)
"""
                
                synthesis_response = self._execute_model_request(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": synthesis_prompt}],
                    json_response=True,
                    temperature=0.2,
                    cache_key=f"{cache_key}_synthesis"
                )
                
                final_result = synthesis_response["result"]
                final_result["model_info"] = {
                    "ensemble": True,
                    "models_used": [
                        technical_response.get("model"),
                        risk_response.get("model"),
                        sentiment_response.get("model"),
                        synthesis_response.get("model")
                    ]
                }
                
                logger.info(f"AI ensemble evaluated position adjustment for {symbol}: {final_result.get('action')}")
                return final_result
                
            else:
                # Single model comprehensive evaluation
                prompt = f"""Evaluate a trading position and determine if the suggested adjustment is appropriate based on current market conditions.

{base_prompt}

Based on the price history and other factors, evaluate if this adjustment is appropriate. Consider:
1. Current market conditions
2. Technical indicators
3. Risk/reward of the adjustment
4. Alternative adjustments that might be better

Return your analysis in JSON format with the following properties:
- action: The recommended action ('ACCEPT_SUGGESTED', 'ALTERNATIVE', 'NO_ACTION')
- alternative_action: If action is 'ALTERNATIVE', specify what action to take instead
- reason: Detailed explanation of your recommendation
- confidence: Your confidence in this recommendation (0-1 scale)
"""
                
                model = AIModelConfig.get_model_for_task("position_evaluation", True)
                response = self._execute_model_request(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    json_response=True,
                    temperature=AIModelConfig.get_temp_for_task("position_evaluation"),
                    cache_key=cache_key
                )
                
                result = response["result"]
                result["model_info"] = {
                    "model": response.get("model"),
                    "execution_time": response.get("execution_time")
                }
                
                logger.info(f"AI advisor evaluated position adjustment for {symbol}: {result.get('action')}")
                return result
            
        except Exception as e:
            logger.error(f"Error evaluating position adjustment: {str(e)}")
            return {
                "action": "NO_ACTION",
                "reason": f"Error evaluating adjustment: {str(e)}"
            }
