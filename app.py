import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Add datetime to Jinja context
app.jinja_env.globals.update(datetime=datetime)

# Configure SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///trading_bot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with SQLAlchemy
db.init_app(app)

# Import models after initializing db
from models import User, Settings, Trade, WatchlistItem

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import trading bot modules
from trading_bot.api_connector import APIConnector
from trading_bot.stock_analyzer import StockAnalyzer
from trading_bot.strategies import CoveredCallStrategy, PutCreditSpreadStrategy, IronCondorStrategy
from trading_bot.trade_executor import TradeExecutor
from trading_bot.ai_advisor import AIAdvisor
from trading_bot.auto_trader import AutoTrader

# Create API connector instance (to be configured in settings)
api_connector = None
stock_analyzer = None
strategy = None
trade_executor = None
ai_advisor = None
auto_trader = None

def initialize_app():
    global api_connector, stock_analyzer, strategy, trade_executor, ai_advisor, auto_trader
    
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Initialize trading components with default settings
        try:
            # Get settings from database or use defaults
            settings = Settings.query.first()
            
            if not settings:
                # Create default settings
                settings = Settings(
                    api_provider="alpaca",
                    api_key=os.environ.get("TRADING_API_KEY", ""),
                    api_secret=os.environ.get("TRADING_API_SECRET", ""),
                    is_paper_trading=True,
                    risk_level="moderate",
                    max_position_size=5000,
                    profit_target_percentage=5,
                    stop_loss_percentage=3,
                    options_expiry_days=30
                )
                db.session.add(settings)
                db.session.commit()
            
            # Initialize trading components
            api_connector = APIConnector(
                provider=settings.api_provider,
                api_key=settings.api_key,
                api_secret=settings.api_secret,
                paper_trading=settings.is_paper_trading
            )
            
            stock_analyzer = StockAnalyzer(api_connector)
            
            # Create strategies based on enabled_strategies setting
            enabled_strategies = settings.enabled_strategies.split(',') if settings.enabled_strategies else ['covered_call']
            
            # Default to covered call strategy
            if 'covered_call' in enabled_strategies:
                strategy = CoveredCallStrategy(
                    risk_level=settings.risk_level,
                    profit_target_percentage=settings.profit_target_percentage,
                    stop_loss_percentage=settings.stop_loss_percentage,
                    options_expiry_days=settings.options_expiry_days
                )
            elif 'put_credit_spread' in enabled_strategies:
                strategy = PutCreditSpreadStrategy(
                    risk_level=settings.risk_level,
                    profit_target_percentage=settings.profit_target_percentage,
                    stop_loss_percentage=settings.stop_loss_percentage,
                    options_expiry_days=settings.options_expiry_days
                )
            elif 'iron_condor' in enabled_strategies:
                strategy = IronCondorStrategy(
                    risk_level=settings.risk_level,
                    profit_target_percentage=settings.profit_target_percentage,
                    stop_loss_percentage=settings.stop_loss_percentage,
                    options_expiry_days=settings.options_expiry_days
                )
            else:
                # Default fallback
                strategy = CoveredCallStrategy(
                    risk_level=settings.risk_level,
                    profit_target_percentage=settings.profit_target_percentage,
                    stop_loss_percentage=settings.stop_loss_percentage,
                    options_expiry_days=settings.options_expiry_days
                )
            
            trade_executor = TradeExecutor(
                api_connector=api_connector,
                max_position_size=settings.max_position_size
            )
            
            logger.info("Trading bot components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing trading bot components: {str(e)}")

# Initialize app before first request
@app.before_request
def before_request():
    # Initialize app if components are not set up
    global api_connector
    if api_connector is None:
        initialize_app()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    # Get account info and recent trades
    account_info = {}
    recent_trades = []
    performance_data = {}
    open_positions = []
    
    try:
        if api_connector:
            # Get recent trades from database
            recent_trades = Trade.query.order_by(Trade.timestamp.desc()).limit(10).all()
            
            # Check if API is connected
            if api_connector.is_connected():
                account_info = api_connector.get_account_info()
                open_positions = api_connector.get_open_positions()
                
                # Get performance data for charts
                performance_data = {
                    'equity_history': api_connector.get_equity_history(),
                    'monthly_returns': api_connector.get_monthly_returns()
                }
            else:
                # Set API status to Error for the alert to display
                account_info = api_connector.get_account_info()
                account_info['api_status'] = 'Error'
                logger.warning("API is not connected. Using fallback data.")
    except Exception as e:
        logger.error(f"Error retrieving dashboard data: {str(e)}")
        flash(f"Error loading dashboard data: {str(e)}", "danger")
        # Ensure API status is set to Error
        account_info['api_status'] = 'Error'
    
    return render_template(
        'dashboard.html', 
        account_info=account_info,
        recent_trades=recent_trades,
        open_positions=open_positions,
        performance_data=performance_data
    )

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    settings = Settings.query.first()
    
    if request.method == 'POST':
        try:
            # Update settings
            settings.api_provider = request.form.get('api_provider')
            settings.api_key = request.form.get('api_key')
            settings.api_secret = request.form.get('api_secret')
            settings.is_paper_trading = 'is_paper_trading' in request.form
            settings.risk_level = request.form.get('risk_level')
            settings.max_position_size = float(request.form.get('max_position_size'))
            settings.profit_target_percentage = float(request.form.get('profit_target_percentage'))
            settings.stop_loss_percentage = float(request.form.get('stop_loss_percentage'))
            settings.options_expiry_days = int(request.form.get('options_expiry_days'))
            
            # Handle multiple strategy selections
            enabled_strategies = request.form.getlist('enabled_strategies')
            if not enabled_strategies:
                # Default to covered call if nothing selected
                enabled_strategies = ['covered_call']
            settings.enabled_strategies = ','.join(enabled_strategies)
            
            db.session.commit()
            
            # Reinitialize components with new settings
            initialize_app()
            
            flash('Settings updated successfully', 'success')
            return redirect(url_for('settings'))
        
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            flash(f"Error updating settings: {str(e)}", "danger")
    
    return render_template('settings.html', settings=settings)

@app.route('/trades')
def trades():
    all_trades = Trade.query.order_by(Trade.timestamp.desc()).all()
    return render_template('trades.html', trades=all_trades)

@app.route('/analysis')
def analysis():
    # Get stock symbols for analysis
    watchlist = []
    opportunities = []
    
    try:
        if stock_analyzer:
            watchlist = WatchlistItem.query.all()
            symbol_list = [item.symbol for item in watchlist]
            
            if symbol_list:
                # Find covered call opportunities
                opportunities = stock_analyzer.find_covered_call_opportunities(symbol_list)
    except Exception as e:
        logger.error(f"Error retrieving analysis data: {str(e)}")
        flash(f"Error analyzing stocks: {str(e)}", "danger")
    
    return render_template('analysis.html', watchlist=watchlist, opportunities=opportunities)

@app.route('/watchlist/add', methods=['POST'])
def add_to_watchlist():
    symbol = request.form.get('symbol', '').strip().upper()
    
    if not symbol:
        flash('Please enter a valid stock symbol', 'danger')
        return redirect(url_for('analysis'))
    
    # Check if already in watchlist
    existing = WatchlistItem.query.filter_by(symbol=symbol).first()
    if existing:
        flash(f'{symbol} is already in your watchlist', 'warning')
        return redirect(url_for('analysis'))
    
    # Add to watchlist
    try:
        watchlist_item = WatchlistItem(symbol=symbol)
        db.session.add(watchlist_item)
        db.session.commit()
        flash(f'{symbol} added to watchlist', 'success')
    except Exception as e:
        logger.error(f"Error adding to watchlist: {str(e)}")
        flash(f"Error adding to watchlist: {str(e)}", 'danger')
    
    return redirect(url_for('analysis'))

@app.route('/watchlist/remove/<symbol>', methods=['POST'])
def remove_from_watchlist(symbol):
    try:
        watchlist_item = WatchlistItem.query.filter_by(symbol=symbol).first()
        if watchlist_item:
            db.session.delete(watchlist_item)
            db.session.commit()
            flash(f'{symbol} removed from watchlist', 'success')
    except Exception as e:
        logger.error(f"Error removing from watchlist: {str(e)}")
        flash(f"Error removing from watchlist: {str(e)}", 'danger')
    
    return redirect(url_for('analysis'))

@app.route('/execute/covered-call', methods=['POST'])
def execute_covered_call():
    symbol = request.form.get('symbol')
    expiry_date = request.form.get('expiry_date')
    strike_price = float(request.form.get('strike_price'))
    quantity = int(request.form.get('quantity'))
    
    try:
        if trade_executor:
            # Execute the covered call strategy
            result = trade_executor.execute_covered_call(
                symbol=symbol,
                quantity=quantity,
                strike_price=strike_price,
                expiry_date=expiry_date
            )
            
            if result['success']:
                # Record the trade
                trade = Trade(
                    symbol=symbol,
                    trade_type='COVERED_CALL',
                    quantity=quantity,
                    price=result['entry_price'],
                    option_strike=strike_price,
                    option_expiry=expiry_date,
                    timestamp=datetime.now()
                )
                db.session.add(trade)
                db.session.commit()
                
                flash(f'Successfully executed covered call for {symbol}', 'success')
            else:
                flash(f'Failed to execute trade: {result["message"]}', 'danger')
        else:
            flash('Trade executor not initialized', 'danger')
    except Exception as e:
        logger.error(f"Error executing covered call: {str(e)}")
        flash(f"Error executing covered call: {str(e)}", 'danger')
    
    return redirect(url_for('analysis'))

@app.route('/api/stock-data/<symbol>')
def stock_data(symbol):
    try:
        if api_connector and api_connector.is_connected():
            data = api_connector.get_stock_data(symbol, days=30)
            return jsonify(data)
        else:
            return jsonify({'error': 'API connector not initialized'}), 500
    except Exception as e:
        logger.error(f"Error retrieving stock data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-connection', methods=['POST'])
def test_api_connection():
    """Test the API connection with provided credentials"""
    try:
        # Get connection parameters from POST request
        data = request.json
        provider = data.get('provider', 'alpaca')
        api_key = data.get('api_key', '')
        api_secret = data.get('api_secret', '')
        is_paper_trading = data.get('is_paper_trading', True)
        
        # Create a temporary connector to test the connection
        temp_connector = APIConnector(
            provider=provider,
            api_key=api_key,
            api_secret=api_secret,
            paper_trading=is_paper_trading
        )
        
        # Test the connection
        is_connected = temp_connector.is_connected()
        
        if is_connected:
            return jsonify({
                'success': True,
                'message': 'API connection successful! Your credentials are valid.'
            })
        else:
            # Get additional details from the connector
            return jsonify({
                'success': False,
                'message': 'Could not connect to the API. Please check your credentials and try again.'
            })
    except Exception as e:
        logger.error(f"Error testing API connection: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
        
@app.route('/oauth/initiate')
def oauth_initiate():
    """Start OAuth2 authorization flow"""
    try:
        provider = request.args.get('provider', 'schwab')
        settings = Settings.query.first()
        
        if provider == 'schwab':
            # In a real implementation, you would redirect to Schwab's authorization URL
            # with necessary parameters (client_id, redirect_uri, scope, etc.)
            
            # Generate a state parameter to prevent CSRF attacks
            state = os.urandom(16).hex()
            session['oauth_state'] = state
            
            # Get the base URL based on paper trading setting
            auth_base_url = "https://api-sandbox.schwab.com/v1/oauth2/authorize" if settings.is_paper_trading else "https://api.schwab.com/v1/oauth2/authorize"
            
            # Construct redirect URI for callback
            redirect_uri = url_for('oauth_callback', _external=True)
            
            # For demonstration purposes, show what the URL would be
            auth_url = f"{auth_base_url}?response_type=code&client_id={settings.api_key}&redirect_uri={redirect_uri}&scope=accounts&state={state}"
            
            flash(f"For a real Schwab API integration, you would be redirected to authorize the application. The callback URL to register in your Schwab Developer account would be: {redirect_uri}", 'info')
            
            # In a real implementation with valid credentials, you would redirect here:
            # return redirect(auth_url)
            
            return redirect(url_for('settings'))
        else:
            flash(f"OAuth flow not implemented for provider: {provider}", 'warning')
            return redirect(url_for('settings'))
    except Exception as e:
        logger.error(f"Error initiating OAuth flow: {str(e)}")
        flash(f"Error initiating OAuth flow: {str(e)}", 'danger')
        return redirect(url_for('settings'))

@app.route('/oauth/callback')
def oauth_callback():
    """Callback endpoint for OAuth2 authentication flow"""
    try:
        # Get the authorization code from the query parameters
        code = request.args.get('code')
        state = request.args.get('state')
        
        # Get the stored settings
        settings = Settings.query.first()
        
        if not code:
            flash('Authentication failed: No authorization code received.', 'danger')
            return redirect(url_for('settings'))
            
        # Verify state parameter to prevent CSRF attacks
        if state != session.get('oauth_state'):
            flash('Authentication failed: Invalid state parameter.', 'danger')
            return redirect(url_for('settings'))
            
        if settings.api_provider == 'schwab':
            # Exchange the authorization code for an access token
            # In a real implementation, you would make a POST request to Schwab's token endpoint
            try:
                # This is a simplified version; in production, you'd make a real API call
                logger.info(f"Received OAuth2 authorization code: {code[:5]}...")
                
                # Get the token endpoint based on paper trading setting
                token_url = "https://api-sandbox.schwab.com/v1/oauth2/token" if settings.is_paper_trading else "https://api.schwab.com/v1/oauth2/token"
                
                # Construct redirect URI for callback (must match the one used in authorization request)
                redirect_uri = url_for('oauth_callback', _external=True)
                
                # In a real implementation, you would make this request:
                # token_response = requests.post(
                #     token_url,
                #     data={
                #         'grant_type': 'authorization_code',
                #         'code': code,
                #         'client_id': settings.api_key,
                #         'client_secret': settings.api_secret,
                #         'redirect_uri': redirect_uri
                #     },
                #     headers={'Content-Type': 'application/x-www-form-urlencoded'}
                # )
                # 
                # if token_response.status_code == 200:
                #     token_data = token_response.json()
                #     access_token = token_data.get('access_token')
                #     refresh_token = token_data.get('refresh_token')
                #     expires_in = token_data.get('expires_in')
                # 
                #     # Store tokens in the database
                #     settings.api_key = access_token  # Store access token as API key
                #     settings.api_secret = refresh_token  # Store refresh token as API secret
                #     db.session.commit()
                
                # Store the authorization code in the session (temporary)
                session['schwab_auth_code'] = code
                
                flash('Authorization code received. In a production app, this would be exchanged for an access token.', 'info')
            except Exception as e:
                logger.error(f"Error in OAuth2 flow: {str(e)}")
                flash(f"Error in authentication flow: {str(e)}", 'danger')
        
        return redirect(url_for('settings'))
    except Exception as e:
        logger.error(f"Error in OAuth callback: {str(e)}")
        flash(f"Error in authentication flow: {str(e)}", 'danger')
        return redirect(url_for('settings'))

# Error handling
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="404 - Page Not Found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error="500 - Internal Server Error"), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
