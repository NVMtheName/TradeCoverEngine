import os
import logging
import json
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse
from datetime import datetime, timedelta
import os.path
import requests
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# Custom JSON encoder to handle pandas DataFrames and numpy arrays
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient='records')
        elif isinstance(obj, pd.Series):
            return obj.to_dict()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Import our Schwab proxy module - will be imported after app initialization to avoid circular imports

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", os.environ.get("FLASK_SECRET_KEY", "dev_secret_key"))
# Set the custom JSON encoder
app.json_encoder = CustomJSONEncoder
# Set session permanency and lifetime
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)  # Sessions last 31 days
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_session')
app.config['SESSION_COOKIE_SECURE'] = True  # Only send cookie over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['SESSION_COOKIE_NAME'] = 'trading_bot_session'  # Custom cookie name

# Import Flask-Session extension for server-side sessions
try:
    from flask_session import Session
    sess = Session()
    sess.init_app(app)
    logger.info("Flask-Session initialized successfully")
except ImportError:
    logger.warning("Flask-Session not installed. Using Flask's default client-side sessions.")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Add datetime to Jinja context
app.jinja_env.globals.update(datetime=datetime)

# Configure database
db_url = os.environ.get("DATABASE_URL", "sqlite:///trading_bot.db")
# Handle postgres URLs (convert postgres:// to postgresql://)
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
print(f"Using database: {db_url.split('@')[0].split('://')[0]}://*****@{db_url.split('@')[-1] if '@' in db_url else db_url.split('://')[-1]}")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with SQLAlchemy
db.init_app(app)

# Import models after initializing db
from models import User, Settings, Trade, WatchlistItem

# Import and register the Schwab proxy blueprint after app initialization
from schwab_proxy import schwab_proxy

# Register the Schwab proxy blueprint
app.register_blueprint(schwab_proxy)

# Set up sandbox mode configuration for the proxy
# This will be used by the proxy to determine which API endpoints to use
app.config['USE_SANDBOX'] = os.environ.get('USE_SCHWAB_SANDBOX', 'true').lower() == 'true'

# Configure sandbox status
app.config['USE_SANDBOX'] = os.environ.get('USE_SANDBOX', 'true').lower() == 'true'  # Default to sandbox

# Import forms
from forms import LoginForm, RegistrationForm

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
from trading_bot.wheel_strategy import WheelStrategy
from trading_bot.collar_strategy import CollarStrategy
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
        
        # Initialize trading components with user-specific settings when possible
        try:
            # Try to get user-specific settings if a user is logged in
            if current_user and current_user.is_authenticated:
                settings = Settings.query.filter_by(user_id=current_user.id).first()
                
                # If no settings found for user, create a new settings record
                if not settings:
                    logger.info(f"Creating new settings for user ID: {current_user.id}")
                    settings = Settings(
                        user_id=current_user.id,
                        api_provider="schwab",
                        is_paper_trading=True,
                        force_simulation_mode=True,
                        risk_level="moderate",
                        max_position_size=5000.0,
                        profit_target_percentage=5.0,
                        stop_loss_percentage=3.0,
                        options_expiry_days=30,
                        enabled_strategies='covered_call',
                        forex_leverage=10.0,
                        forex_lot_size=0.1,
                        forex_pairs_watchlist='EUR/USD,GBP/USD,USD/JPY'
                    )
                    db.session.add(settings)
                    db.session.commit()
                
                user_specific = True
                logger.info(f"Using settings for user ID: {current_user.id}")
            else:
                # Fall back to default settings
                settings = Settings.query.first()
                user_specific = False
                logger.info("Using default settings (no user logged in)")
            
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
            
            # Check OAuth tokens if using Schwab
            # Initialize trading components
            use_sim_mode = settings.force_simulation_mode
            logger.info(f"Initializing API connector with force_simulation={use_sim_mode}")
            
            # Get SCHWAB API credentials from environment if available
            api_key = settings.api_key or os.environ.get("SCHWAB_API_KEY")
            api_secret = settings.api_secret or os.environ.get("SCHWAB_API_SECRET")
            
            # Initialize API connector
            api_connector = APIConnector(
                provider=settings.api_provider,
                api_key=api_key,
                api_secret=api_secret,
                paper_trading=settings.is_paper_trading,
                force_simulation=use_sim_mode
            )
            
            # If we're using Schwab and have OAuth tokens, update the connector
            if settings.api_provider == 'schwab' and settings.oauth_access_token:
                # Pass OAuth tokens to the connector
                logger.info(f"Passing OAuth tokens to API connector (access token: {settings.oauth_access_token[:5]}...)")
                api_connector.access_token = settings.oauth_access_token
                api_connector.refresh_token = settings.oauth_refresh_token
                api_connector.token_expiry = settings.oauth_token_expiry
                
                # Update Authorization header
                api_connector.session.headers.update({
                    'Authorization': f'Bearer {settings.oauth_access_token}'
                })
                
                # Check if token needs refresh
                if api_connector.is_token_expired() and settings.oauth_refresh_token:
                    logger.info("OAuth token expired, attempting refresh during initialization")
                    refresh_success = api_connector.refresh_access_token()
                    
                    if refresh_success:
                        # Update the settings with new tokens
                        settings.oauth_access_token = api_connector.access_token
                        settings.oauth_refresh_token = api_connector.refresh_token
                        settings.oauth_token_expiry = api_connector.token_expiry
                        db.session.commit()
                        logger.info("Successfully refreshed and stored new OAuth tokens")
                    else:
                        logger.warning("Failed to refresh OAuth tokens during initialization")
            
            stock_analyzer = StockAnalyzer(api_connector)
            
            # Create strategies based on enabled_strategies setting
            enabled_strategies = settings.enabled_strategies.split(',') if settings.enabled_strategies else ['covered_call']
            
            # Choose strategy based on user's selection - using the first in the list as the primary strategy
            if 'covered_call' in enabled_strategies:
                strategy = CoveredCallStrategy(
                    risk_level=settings.risk_level,
                    profit_target_percentage=settings.profit_target_percentage,
                    stop_loss_percentage=settings.stop_loss_percentage,
                    options_expiry_days=settings.options_expiry_days
                )
            elif 'wheel' in enabled_strategies:
                strategy = WheelStrategy(
                    risk_level=settings.risk_level,
                    profit_target_percentage=settings.profit_target_percentage,
                    stop_loss_percentage=settings.stop_loss_percentage,
                    options_expiry_days=settings.options_expiry_days
                )
            elif 'collar' in enabled_strategies:
                strategy = CollarStrategy(
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
            
            # Initialize AI advisor
            ai_advisor = AIAdvisor()
            
            # Initialize auto trader if AI advisor is available
            if ai_advisor.is_available():
                auto_trader = AutoTrader(
                    api_connector=api_connector,
                    ai_advisor=ai_advisor,
                    trade_executor=trade_executor,
                    stock_analyzer=stock_analyzer
                )
                
                # Set auto trader watchlist from database
                watchlist_items = WatchlistItem.query.all()
                if watchlist_items:
                    auto_trader.set_watchlist([item.symbol for item in watchlist_items])
                
                # Set trading parameters
                auto_trader.set_trading_parameters({
                    'max_position_size': settings.max_position_size,
                    'scan_interval_hours': 6,  # Scan every 6 hours
                    'max_concurrent_trades': 5,  # Maximum of 5 concurrent trades
                    'confidence_threshold': 0.7  # Minimum AI confidence score
                })
            else:
                logger.warning("AI advisor not available. Auto trader will not be initialized.")
                auto_trader = None
            
            logger.info("Trading bot components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing trading bot components: {str(e)}")

# Initialize app before first request
@app.before_request
def before_request():
    # Initialize app if components are not set up, or on login/logout events
    global api_connector, ai_advisor, auto_trader
    
    # Check for initialization or login/logout event
    user_id = current_user.id if current_user.is_authenticated else None
    
    # Get previous request path from session
    prev_path = session.get('prev_path', '')
    curr_path = request.path
    
    # Store current path for next request
    session['prev_path'] = curr_path
    
    # Detect login/logout events
    login_event = prev_path == '/login' and curr_path != '/login'
    logout_event = prev_path == '/logout'
    
    # Reinitialize if needed
    if api_connector is None or login_event or logout_event:
        logger.info(f"Reinitializing API connector for user_id={user_id} (login_event={login_event}, logout_event={logout_event})")
        initialize_app()

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            # Set up session based on remember preference
            if form.remember.data:
                # If remember me is checked, make session permanent with our long expiry
                session.permanent = True
                # Login with remember=True for Flask-Login's cookie
                login_user(user, remember=True)
                logger.info(f"Setting permanent session for user {user.username}")
            else:
                # If remember me is not checked, use standard session lifetime
                session.permanent = False
                # Set a shorter session expiry for non-remembered sessions (1 day)
                app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
                # Login with remember=False
                login_user(user, remember=False)
                # Reset the session lifetime back to the longer period for future remembered sessions
                app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)
                logger.info(f"Setting temporary session for user {user.username}")
            
            # Update last login time
            user.last_login = datetime.now()
            db.session.commit()
            
            # Set a session variable to track the user's ID explicitly
            session['user_id'] = user.id
            
            # Log user login for debugging
            logger.info(f"User {user.username} (ID: {user.id}) logged in successfully with remember_me={form.remember.data}")
            
            # Get the next page from query string (or default to dashboard)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('dashboard')
                
            flash('Login successful!', 'success')
            return redirect(next_page)
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        
        # Create user-specific settings
        settings = Settings(
            user=user,
            api_provider="schwab",
            is_paper_trading=True,
            force_simulation_mode=True,
            risk_level="moderate",
            max_position_size=5000.0,
            profit_target_percentage=5.0,
            stop_loss_percentage=3.0,
            options_expiry_days=30,
            enabled_strategies='covered_call',
            forex_leverage=10.0,
            forex_lot_size=0.1,
            forex_pairs_watchlist='EUR/USD,GBP/USD,USD/JPY'
        )
        
        db.session.add(user)
        db.session.add(settings)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    # Get user info for logging
    if current_user.is_authenticated:
        user_id = current_user.id
        username = current_user.username
        logger.info(f"Logging out user {username} (ID: {user_id})")
    
    # Clear Flask-Login session
    logout_user()
    
    # Clear custom session variables
    session.pop('user_id', None)
    session.pop('prev_path', None)
    
    # Reset session permanence
    session.permanent = False
    
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
def index():
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get account info and recent trades
    account_info = {}
    recent_trades = []
    performance_data = {}
    open_positions = []
    
    try:
        if api_connector:
            # Get recent trades from database for current user
            recent_trades = Trade.query.filter_by(user_id=current_user.id).order_by(Trade.timestamp.desc()).limit(10).all()
            
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
                # Check if account_info is a dictionary before trying to set a new key
                if isinstance(account_info, dict):
                    account_info['api_status'] = 'Error'
                else:
                    # Handle case where account_info might be None or some other format
                    account_info = {'api_status': 'Error'}
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

@app.route('/strategy_info')
@login_required
def strategy_info():
    """Display information about trading strategies"""
    return render_template('strategy_info.html')

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    # Ensure user has settings
    settings = Settings.query.filter_by(user_id=current_user.id).first()
    
    # If no settings found for user, create a new settings record
    if not settings:
        logger.info(f"Creating new settings for user ID: {current_user.id} during settings page access")
        settings = Settings(
            user_id=current_user.id,
            api_provider="schwab",
            is_paper_trading=True,
            force_simulation_mode=True,
            risk_level="moderate",
            max_position_size=5000.0,
            profit_target_percentage=5.0,
            stop_loss_percentage=3.0,
            options_expiry_days=30,
            enabled_strategies='covered_call',
            forex_leverage=10.0,
            forex_lot_size=0.1,
            forex_pairs_watchlist='EUR/USD,GBP/USD,USD/JPY'
        )
        db.session.add(settings)
        db.session.commit()
    
    if request.method == 'POST':
        try:
            # Update settings
            settings.api_provider = request.form.get('api_provider')
            settings.api_key = request.form.get('api_key')
            settings.api_secret = request.form.get('api_secret')
            settings.is_paper_trading = 'is_paper_trading' in request.form
            settings.force_simulation_mode = 'force_simulation_mode' in request.form
            settings.risk_level = request.form.get('risk_level')
            settings.max_position_size = float(request.form.get('max_position_size'))
            settings.profit_target_percentage = float(request.form.get('profit_target_percentage'))
            settings.stop_loss_percentage = float(request.form.get('stop_loss_percentage'))
            settings.options_expiry_days = int(request.form.get('options_expiry_days'))
            settings.forex_pairs_watchlist = request.form.get('forex_pairs_watchlist')
            settings.forex_leverage = float(request.form.get('forex_leverage'))
            settings.forex_lot_size = float(request.form.get('forex_lot_size'))
            
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
@login_required
def trades():
    all_trades = Trade.query.filter_by(user_id=current_user.id).order_by(Trade.timestamp.desc()).all()
    return render_template('trades.html', trades=all_trades)

@app.route('/analysis')
@login_required
def analysis():
    # Get stock symbols for analysis
    watchlist = []
    opportunities = []
    
    try:
        if stock_analyzer:
            watchlist = WatchlistItem.query.filter_by(user_id=current_user.id).all()
            symbol_list = [item.symbol for item in watchlist]
            
            if symbol_list:
                # Find covered call opportunities
                opportunities = stock_analyzer.find_covered_call_opportunities(symbol_list)
    except Exception as e:
        logger.error(f"Error retrieving analysis data: {str(e)}")
        flash(f"Error analyzing stocks: {str(e)}", "danger")
    
    return render_template('analysis.html', watchlist=watchlist, opportunities=opportunities)

@app.route('/watchlist/add', methods=['POST'])
@login_required
def add_to_watchlist():
    symbol = request.form.get('symbol', '').strip().upper()
    
    if not symbol:
        flash('Please enter a valid stock symbol', 'danger')
        return redirect(url_for('analysis'))
    
    # Check if already in watchlist
    existing = WatchlistItem.query.filter_by(user_id=current_user.id, symbol=symbol).first()
    if existing:
        flash(f'{symbol} is already in your watchlist', 'warning')
        return redirect(url_for('analysis'))
    
    # Add to watchlist
    try:
        watchlist_item = WatchlistItem(symbol=symbol, user_id=current_user.id)
        db.session.add(watchlist_item)
        db.session.commit()
        flash(f'{symbol} added to watchlist', 'success')
    except Exception as e:
        logger.error(f"Error adding to watchlist: {str(e)}")
        flash(f"Error adding to watchlist: {str(e)}", 'danger')
    
    return redirect(url_for('analysis'))

@app.route('/watchlist/remove/<symbol>', methods=['POST'])
@login_required
def remove_from_watchlist(symbol):
    try:
        watchlist_item = WatchlistItem.query.filter_by(user_id=current_user.id, symbol=symbol).first()
        if watchlist_item:
            db.session.delete(watchlist_item)
            db.session.commit()
            flash(f'{symbol} removed from watchlist', 'success')
    except Exception as e:
        logger.error(f"Error removing from watchlist: {str(e)}")
        flash(f"Error removing from watchlist: {str(e)}", 'danger')
    
    return redirect(url_for('analysis'))

@app.route('/execute/covered-call', methods=['POST'])
@login_required
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
                    user_id=current_user.id,
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
            paper_trading=is_paper_trading,
            force_simulation=data.get('force_simulation_mode', False)
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
    """Start OAuth2 authorization flow for 3-legged OAuth authentication"""
    try:
        provider = request.args.get('provider', 'schwab')
        
        # Use current user's settings if available
        if current_user.is_authenticated:
            settings = Settings.query.filter_by(user_id=current_user.id).first()
            logger.info(f"Initiating OAuth flow for user ID: {current_user.id}")
            if not settings:
                logger.warning(f"No settings found for user ID: {current_user.id}, creating new settings")
                settings = Settings(
                    user_id=current_user.id,
                    api_provider="schwab",
                    is_paper_trading=True,
                    force_simulation_mode=True
                )
                db.session.add(settings)
                db.session.commit()
        else:
            flash("You must be logged in to use OAuth authentication", 'warning')
            return redirect(url_for('login'))
        
        if provider == 'schwab':
            # Ensure we have client credentials configured
            if not settings.api_key or not settings.api_secret:
                # Check environment variables for credentials
                env_api_key = os.environ.get("SCHWAB_API_KEY")
                env_api_secret = os.environ.get("SCHWAB_API_SECRET")
                
                if env_api_key and env_api_secret:
                    settings.api_key = env_api_key
                    settings.api_secret = env_api_secret
                    db.session.commit()
                    logger.info("Applied Schwab API credentials from environment variables")
                else:
                    flash("Missing API Key and Secret. Please configure your API credentials in settings first.", 'danger')
                    return redirect(url_for('settings'))
            
            # Generate a state parameter to prevent CSRF attacks
            state = os.urandom(16).hex()
            session['oauth_state'] = state
            
            # Store additional OAuth session data
            session['oauth_provider'] = provider
            session['oauth_user_id'] = current_user.id
            session['oauth_initiation_time'] = datetime.now().timestamp()
            
            # We'll use our server-side proxy to avoid CORS issues
            # Our proxy handles the direct communication with Schwab API from our server
            logger.info("Using server-side proxy for Schwab API OAuth authorization")
            
            # Construct redirect URI for callback
            # Schwab API requirements state the callback URL must use HTTPS
            app_url = request.url_root.rstrip('/')
            
            # Force HTTPS as required by Schwab
            if app_url.startswith('http:'):
                app_url = app_url.replace('http:', 'https:', 1)
                
            # Per Schwab requirements, callback URLs must:
            # 1. Use HTTPS protocol
            # 2. Have a valid SSL/TLS certificate
            # 3. Not use localhost or 127.0.0.1
            # 4. Not include special characters except those allowed in RFC 3986
            # 5. Not include ports unless it's a sandbox environment
            
            # Define callback path
            callback_path = '/oauth/callback'
            
            # Use client ID from settings or environment variables
            env_api_key = os.environ.get("SCHWAB_API_KEY")
            client_id = settings.api_key or env_api_key
            
            if not client_id:
                logger.error("Missing client ID for OAuth authorization")
                flash("Authentication failed: Missing API Key. Please configure it in settings.", 'danger')
                return redirect(url_for('settings'))
                
            # Save the client ID in settings for future use if it came from environment variables
            if settings.api_key != client_id:
                settings.api_key = client_id
                db.session.commit()
            
            # Define the callback URL for OAuth integration
            # For Replit, we can get this from environment variables or generate a proper HTTPS URL
            replit_domain = os.environ.get('REPLIT_DEV_DOMAIN')
            
            # Use both /oauth/callback and /oauth2/callback paths for maximum compatibility
            # Create a list of potential callback URIs
            callback_paths = ['/oauth/callback', '/oauth2/callback']
            
            if replit_domain:
                # Use the Replit domain for callbacks
                callback_uris = [f"https://{replit_domain}{path}" for path in callback_paths]
                # Default to first one
                exact_redirect_uri = callback_uris[0]
                logger.info(f"Using Replit domain for OAuth callbacks: {', '.join(callback_uris)}")
            else:
                # Fallback to app URL with forced HTTPS
                callback_uris = [f"{app_url}{path}" for path in callback_paths]
                # Default to first one
                exact_redirect_uri = callback_uris[0]
                logger.info(f"Using generated URLs for OAuth callbacks: {', '.join(callback_uris)}")
            
            # Define authorization parameters with exact values according to Schwab documentation
            # https://developer.schwab.com/user-guides/apis-and-apps/app-callback-url-requirements
            # The authorize request must include client_id, redirect_uri, response_type, and scope
            auth_params = {
                'client_id': client_id,
                'redirect_uri': exact_redirect_uri,
                'response_type': 'code',  # Required for authorization code flow
                'scope': 'trading'  # Required scope for Schwab API per their documentation
            }
            
            # For debugging
            logger.info(f"Using complete Schwab OAuth authorization URL format as specified in API docs")
            
            # Build the authorization URL with proper URL encoding
            from urllib.parse import urlencode
            
            # We no longer need to determine auth_base_url since we're using our proxy
            # This prevents the 'auth_base_url is unbound' error
            
            logger.info(f"Using Schwab API key: {client_id[:4]}...{client_id[-4:]} for OAuth flow")
            logger.info(f"Redirect URI: {exact_redirect_uri}")
            
            # Show the OAuth authorization URL for debugging purposes
            flash(f"Using provided credentials for Schwab OAuth authorization", 'info')
            
            # Build URL for our proxy endpoint
            try:
                # Set up sandbox/production mode in the session for the proxy
                session['oauth_is_sandbox'] = settings.is_paper_trading
                
                # Update the app config to use the correct environment
                app.config['USE_SANDBOX'] = settings.is_paper_trading
                
                # Build a URL to our proxy endpoint instead of directly to Schwab
                # This avoids CORS issues since our server will make the request
                proxy_url = url_for('schwab_proxy.proxy_oauth_authorize', _external=True)
                
                # Add required OAuth parameters
                from urllib.parse import urlencode
                auth_params = {
                    'client_id': client_id,
                    'redirect_uri': exact_redirect_uri,
                    'response_type': 'code',  # Required for authorization code flow
                    'scope': 'trading',       # Required scope for Schwab API
                    'state': state            # CSRF protection token
                }
                
                # Construct the full proxy URL with parameters
                proxy_auth_url = f"{proxy_url}?{urlencode(auth_params)}"
                
                # Log the proxy URL we're using
                logger.info(f"Using proxy to connect to Schwab API: {proxy_url}")
                logger.info(f"Using Schwab API key: {client_id[:4]}...{client_id[-4:]} for OAuth flow")
                logger.info(f"Redirect URI: {exact_redirect_uri}")
                
                # Store additional session data for the proxy to use
                session['oauth_proxy_enabled'] = True
                session['oauth_client_id'] = client_id
                session['oauth_redirect_uri'] = exact_redirect_uri
                
                # Show informative message to user
                flash("Connecting to Schwab API through secure proxy...", 'info')
                
                # Redirect to our proxy endpoint
                logger.info(f"Redirecting user to proxy OAuth authorization endpoint: {proxy_auth_url}")
                return redirect(proxy_auth_url)
                
            except Exception as e:
                logger.error(f"Error testing connection to Schwab authorization endpoint: {str(e)}")
                flash(f"Error connecting to Schwab API: {str(e)}. If this persists, contact Schwab Developer Support.", 'danger')
                return redirect(url_for('settings'))
        else:
            flash(f"OAuth flow not implemented for provider: {provider}", 'warning')
            return redirect(url_for('settings'))
    except Exception as e:
        logger.error(f"Error initiating OAuth flow: {str(e)}")
        flash(f"Error initiating OAuth flow: {str(e)}", 'danger')
        return redirect(url_for('settings'))

@app.route('/oauth/callback')
@app.route('/oauth2/callback')  # Alternative OAuth2 callback path
@app.route('/google_login/callback')  # Keep for backward compatibility
def oauth_callback():
    """Callback endpoint for OAuth2 authorization flow in 3-legged OAuth authentication"""
    try:
        # Get the authorization code and state from the query parameters
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        error_description = request.args.get('error_description')
        
        # Log basic information about the callback
        logger.info(f"OAuth callback received: code={bool(code)}, state={bool(state)}, error={error}")
        
        # Check for OAuth error response (RFC 6749 Section 4.1.2.1)
        if error:
            logger.error(f"OAuth authorization error: {error} - {error_description}")
            flash(f"Authorization failed: {error_description or error}", 'danger')
            return redirect(url_for('settings'))
        
        # Validate required parameters
        if not code:
            flash('Authentication failed: No authorization code received', 'danger')
            return redirect(url_for('settings'))
        
        # Verify state parameter to prevent CSRF attacks (RFC 6749 Section 10.12)
        if state != session.get('oauth_state'):
            logger.error(f"OAuth state mismatch: received={state}, stored={session.get('oauth_state')}")
            flash('Authentication failed: Invalid state parameter (potential CSRF attack)', 'danger')
            return redirect(url_for('settings'))
            
        # Get user info from session
        oauth_provider = session.get('oauth_provider')
        oauth_user_id = session.get('oauth_user_id')
        
        # Verify session data
        if not oauth_provider or not oauth_user_id:
            logger.error("Missing OAuth session data, can't determine user or provider")
            flash('Authentication failed: Session data lost, please try again', 'danger')
            return redirect(url_for('settings'))
        
        # Retrieve user settings
        settings = Settings.query.filter_by(user_id=oauth_user_id).first()
        if not settings:
            logger.error(f"No settings found for user ID {oauth_user_id}")
            flash('Authentication failed: User settings not found', 'danger')
            return redirect(url_for('settings'))
        
        # Process based on the provider
        if oauth_provider == 'schwab':
            # Exchange the authorization code for an access token (RFC 6749 Section 4.1.3)
            try:
                # Log the authorization code (truncated for security)
                logger.info(f"Processing authorization code: {code[:5]}...")
                
                # Set OAuth 2.0 token endpoints based on environment
                # We'll try multiple possible URL patterns since the exact endpoints may have changed
                # https://developer.schwab.com/products/trader-api--individual/details/specifications/Retail%20Trader%20API%20Production
                if settings.is_paper_trading:
                    # Define OAuth2 token URLs for sandbox environment
                    # Based on our connectivity tests, only the following endpoint works
                    token_urls = [
                        # Primary working sandbox endpoint confirmed by our tests
                        "https://sandbox.schwabapi.com/v1/oauth/token",  # The ONLY working sandbox endpoint
                        
                        # Fallback options (unlikely to work but included for robustness)
                        "https://sandbox.schwabapi.com/oauth2/token",
                        "https://sandbox.schwabapi.com/oauth/token",
                        "https://api-sandbox.schwabapi.com/oauth/token"
                    ]
                    logger.info("Using Schwab sandbox OAuth2 token endpoints - will try multiple patterns")
                else:
                    # Define OAuth2 token URLs based on our comprehensive endpoint testing
                    # Using the same base URLs as the authorization endpoints for consistency
                    token_urls = [
                        # Primary working endpoint confirmed by our tests
                        "https://api.schwabapi.com/v1/oauth/token",  # Token endpoint matching the working auth endpoint
                        
                        # Fallback options (unlikely to work but included for robustness)
                        "https://api.schwabapi.com/oauth2/token",
                        "https://api.schwabapi.com/oauth/token",
                        "https://api.schwab.com/v1/oauth/token",
                        "https://developer.schwab.com/oauth/token"
                    ]
                    logger.info("Using Schwab production OAuth2 token endpoints - will try multiple patterns")
                    
                # Start with the first URL pattern
                token_url = token_urls[0]
                
                # Use exactly the same redirect URI as in the authorization request
                # This is critical for OAuth to work correctly
                replit_domain = os.environ.get('REPLIT_DEV_DOMAIN')
                
                # Determine which callback path was used in the authorization flow
                callback_path = request.path
                # Default to /oauth/callback if we can't determine the actual path
                if not callback_path or callback_path == '/':
                    callback_path = '/oauth/callback'
                    
                logger.info(f"OAuth callback received on path: {callback_path}")
                
                if replit_domain:
                    # Use the Replit domain for callback
                    redirect_uri = f"https://{replit_domain}{callback_path}"
                    logger.info(f"Using Replit domain for OAuth callback: {redirect_uri}")
                else:
                    # Fallback to using app URL with HTTPS
                    app_url = request.url_root.rstrip('/')
                    if app_url.startswith('http:'):
                        app_url = app_url.replace('http:', 'https:', 1)
                    redirect_uri = f"{app_url}{callback_path}"
                    logger.info(f"Using generated URL for OAuth callback: {redirect_uri}")
                
                # Now perform the token exchange
                import requests
                from urllib.parse import urlencode
                
                # Prepare the token request payload (RFC 6749 Section 4.1.3)
                # Use client ID from settings or environment variables
                env_api_key = os.environ.get("SCHWAB_API_KEY")
                client_id = settings.api_key or env_api_key
                
                if not client_id:
                    logger.error("Missing client ID for token exchange")
                    flash("Authentication failed: Missing API Key. Please configure it in settings.", 'danger')
                    return redirect(url_for('settings'))
                # Use the client secret from settings or environment variables
                env_api_secret = os.environ.get("SCHWAB_API_SECRET")
                client_secret = settings.api_secret or env_api_secret
                
                if not client_secret:
                    logger.error("Missing client secret for token exchange")
                    flash("Authentication failed: Missing API secret. Please configure it in settings.", 'danger')
                    return redirect(url_for('settings'))
                
                # Prepare token payload according to Schwab's documentation
                # https://developer.schwab.com/user-guides/apis-and-apps/oauth-restart-vs-refresh-token
                token_payload = {
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': redirect_uri,  # Must match the original redirect exactly
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'scope': 'trading'  # Match scope from authorization request per Schwab docs
                }
                
                # Prepare headers for token request
                token_headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json',
                    'User-Agent': 'Trading Bot OAuth2 Flow'
                }
                
                # Use our proxy for token exchange to avoid CORS issues
                token_response = None
                
                # Build proxy token URL
                proxy_token_url = url_for('schwab_proxy.proxy_oauth_token', _external=True)
                logger.info(f"Using proxy for token exchange: {proxy_token_url}")
                logger.info(f"Using redirect_uri: {redirect_uri}")
                
                try:
                    # Make the token exchange request through our proxy
                    response = requests.post(
                        proxy_token_url,
                        data=token_payload,
                        headers=token_headers,
                        timeout=15  # Longer timeout for token exchange
                    )
                    
                    # Log the response status
                    logger.info(f"Token exchange response status: {response.status_code}")
                    
                    # Store the response for processing
                    token_response = response
                    
                except Exception as e:
                    logger.error(f"Error during token exchange: {str(e)}")
                    flash(f"Authentication error: {str(e)}", 'danger')
                    return redirect(url_for('settings'))
                
                # No need to try multiple URLs since we're using our proxy
                    
                logger.info(f"Final token exchange response status: {token_response.status_code}")
                
                if token_response.status_code == 200:
                    # Process successful token response (RFC 6749 Section 4.1.4)
                    token_data = token_response.json()
                    
                    # Extract token data
                    access_token = token_data.get('access_token')
                    refresh_token = token_data.get('refresh_token')
                    expires_in = token_data.get('expires_in', 3600)  # Default to 1 hour
                    token_type = token_data.get('token_type', 'Bearer')
                    scope = token_data.get('scope', '')
                    
                    # Validate required tokens
                    if not access_token:
                        logger.error("Missing access_token in token response")
                        flash("Authentication failed: Invalid token response from server", 'danger')
                        return redirect(url_for('settings'))
                    
                    if not refresh_token:
                        logger.warning("Missing refresh_token in token response - this may affect longevity of access")
                    
                    # Store tokens securely in the database
                    from datetime import timedelta
                    settings.oauth_access_token = access_token
                    settings.oauth_refresh_token = refresh_token
                    settings.oauth_token_expiry = datetime.now() + timedelta(seconds=expires_in)
                    
                    # Disable simulation mode now that we have real API access
                    settings.force_simulation_mode = False
                    
                    # Save changes to database
                    db.session.commit()
                    
                    # Log success (with minimal token info for security)
                    logger.info(f"Successfully obtained OAuth tokens (access: {access_token[:5]}..., expires in: {expires_in}s)")
                    logger.info(f"Granted scopes: {scope}")
                    
                    # Update API connector with new tokens
                    try:
                        global api_connector
                        if api_connector and api_connector.provider == 'schwab':
                            api_connector.access_token = access_token
                            api_connector.refresh_token = refresh_token
                            api_connector.token_expiry = settings.oauth_token_expiry
                            
                            # Update authorization header
                            api_connector.session.headers.update({
                                'Authorization': f'{token_type} {access_token}'
                            })
                            
                            logger.info("Updated API connector with new OAuth tokens")
                        else:
                            # Reinitialize the app with the new tokens
                            logger.info("Reinitializing app to apply new OAuth tokens")
                            initialize_app()
                    except Exception as connector_error:
                        logger.error(f"Error updating API connector: {str(connector_error)}")
                    
                    # Clean up session data
                    if 'oauth_state' in session:
                        del session['oauth_state']
                    if 'oauth_provider' in session:
                        del session['oauth_provider']
                    if 'oauth_initiation_time' in session:
                        del session['oauth_initiation_time']
                    
                    # Notify user of success
                    flash('Successfully authenticated with Schwab API! You can now use the trading features.', 'success')
                else:
                    # Process error response (RFC 6749 Section 5.2)
                    try:
                        error_content = token_response.json() if 'application/json' in token_response.headers.get('content-type', '') else {}
                    except ValueError:
                        error_content = {}
                    
                    error_type = error_content.get('error', 'server_error')
                    error_desc = error_content.get('error_description', token_response.text[:100])
                    
                    # Log detailed error information
                    logger.error(f"OAuth token exchange error: {error_type} - {error_desc}")
                    logger.error(f"Response status: {token_response.status_code}, Headers: {dict(token_response.headers)}")
                    
                    # Provide user-friendly error message
                    if error_type == 'invalid_grant':
                        flash("Authentication failed: Invalid or expired authorization code", 'danger')
                    elif error_type == 'invalid_client':
                        flash("Authentication failed: Invalid API key or secret", 'danger')
                    else:
                        flash(f"Failed to authenticate with Schwab: {error_desc or error_type}", 'danger')
            
            except Exception as e:
                logger.error(f"Error in OAuth2 token exchange: {str(e)}")
                flash(f"Authentication error: {str(e)}", 'danger')
        else:
            # Unsupported provider
            logger.error(f"OAuth callback for unsupported provider: {oauth_provider}")
            flash(f"OAuth authentication not implemented for provider: {oauth_provider}", 'warning')
        
        # Redirect to settings page
        return redirect(url_for('settings'))
    except Exception as e:
        logger.error(f"Unhandled error in OAuth callback: {str(e)}")
        flash(f"Authentication error: {str(e)}", 'danger')
        return redirect(url_for('settings'))

# Error handling
# Auto trading routes
@app.route('/auto-trading')
@login_required
def auto_trading():
    """Display auto trading status and controls"""
    status = {}
    ai_status = {}
    scan_results = []
    watchlist = []
    
    try:
        # Get watchlist items
        watchlist = WatchlistItem.query.filter_by(user_id=current_user.id).all()
        
        # Check if auto trader is available
        if auto_trader:
            status = auto_trader.get_status()
            
            # Check if AI advisor is available
            if ai_advisor:
                ai_status = {
                    'is_available': ai_advisor.is_available(),
                    'api_key_set': bool(ai_advisor.api_key)
                }
        else:
            status = {
                'is_enabled': False,
                'error': 'Auto trader not initialized'
            }
            
            ai_status = {
                'is_available': ai_advisor.is_available() if ai_advisor else False,
                'api_key_set': bool(ai_advisor.api_key) if ai_advisor else False
            }
    except Exception as e:
        logger.error(f"Error getting auto trading status: {str(e)}")
        flash(f"Error getting auto trading status: {str(e)}", 'danger')
    
    return render_template(
        'auto_trading.html',
        status=status,
        ai_status=ai_status,
        scan_results=scan_results,
        watchlist=watchlist
    )

@app.route('/auto-trading/start', methods=['POST'])
def start_auto_trading():
    """Start the auto trader"""
    try:
        if auto_trader:
            result = auto_trader.start()
            
            if result:
                flash('Auto trader started successfully', 'success')
            else:
                flash('Auto trader is already running', 'warning')
        else:
            flash('Auto trader not initialized. Please check your OpenAI API key.', 'danger')
    except Exception as e:
        logger.error(f"Error starting auto trader: {str(e)}")
        flash(f"Error starting auto trader: {str(e)}", 'danger')
    
    return redirect(url_for('auto_trading'))

@app.route('/auto-trading/stop', methods=['POST'])
def stop_auto_trading():
    """Stop the auto trader"""
    try:
        if auto_trader:
            result = auto_trader.stop()
            
            if result:
                flash('Auto trader stopped successfully', 'success')
            else:
                flash('Auto trader is not running', 'warning')
        else:
            flash('Auto trader not initialized', 'danger')
    except Exception as e:
        logger.error(f"Error stopping auto trader: {str(e)}")
        flash(f"Error stopping auto trader: {str(e)}", 'danger')
    
    return redirect(url_for('auto_trading'))

@app.route('/auto-trading/scan', methods=['POST'])
def scan_for_opportunities():
    """Manually trigger a scan for trading opportunities"""
    opportunities = []
    
    try:
        if auto_trader:
            opportunities = auto_trader.scan_for_opportunities(force=True)
            
            if opportunities:
                flash(f'Found {len(opportunities)} trading opportunities', 'success')
            else:
                flash('No trading opportunities found', 'info')
        else:
            flash('Auto trader not initialized', 'danger')
    except Exception as e:
        logger.error(f"Error scanning for opportunities: {str(e)}")
        flash(f"Error scanning for opportunities: {str(e)}", 'danger')
    
    # Store scan results in session for display
    session['scan_results'] = opportunities
    
    return redirect(url_for('auto_trading'))

@app.route('/auto-trading/settings', methods=['POST'])
def update_auto_trading_settings():
    """Update auto trading settings"""
    try:
        if auto_trader:
            # Get settings from form
            max_position_size = float(request.form.get('max_position_size', 5000))
            scan_interval_hours = int(request.form.get('scan_interval_hours', 6))
            max_concurrent_trades = int(request.form.get('max_concurrent_trades', 5))
            confidence_threshold = float(request.form.get('confidence_threshold', 0.7))
            
            # Update auto trader settings
            auto_trader.set_trading_parameters({
                'max_position_size': max_position_size,
                'scan_interval_hours': scan_interval_hours,
                'max_concurrent_trades': max_concurrent_trades,
                'confidence_threshold': confidence_threshold
            })
            
            flash('Auto trading settings updated successfully', 'success')
        else:
            flash('Auto trader not initialized', 'danger')
    except Exception as e:
        logger.error(f"Error updating auto trading settings: {str(e)}")
        flash(f"Error updating auto trading settings: {str(e)}", 'danger')
    
    return redirect(url_for('auto_trading'))

@app.route('/api/ai-analysis/<symbol>')
def ai_analysis(symbol):
    """Get AI analysis for a symbol"""
    try:
        if ai_advisor and ai_advisor.is_available():
            # Get stock data
            price_history = api_connector.get_stock_data(symbol, days=90)
            
            # Get AI analysis
            analysis = ai_advisor.analyze_stock(symbol, price_history)
            
            return jsonify(analysis)
        else:
            return jsonify({
                'error': 'AI advisor not available',
                'ai_insights': 'AI advisor not available. Please provide an OpenAI API key.'
            }), 500
    except Exception as e:
        logger.error(f"Error getting AI analysis for {symbol}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="404 - Page Not Found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error="500 - Internal Server Error"), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
