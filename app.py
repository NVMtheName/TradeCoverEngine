import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse
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
            
            api_connector = APIConnector(
                provider=settings.api_provider,
                api_key=api_key,
                api_secret=api_secret,
                paper_trading=settings.is_paper_trading,
                force_simulation=use_sim_mode
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
            login_user(user, remember=form.remember.data)
            
            # Update last login time
            user.last_login = datetime.now()
            db.session.commit()
            
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
    logout_user()
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
@login_required
def settings():
    settings = Settings.query.filter_by(user_id=current_user.id).first()
    
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
    """Start OAuth2 authorization flow"""
    try:
        provider = request.args.get('provider', 'schwab')
        
        # Use current user's settings if available
        if current_user.is_authenticated:
            settings = Settings.query.filter_by(user_id=current_user.id).first()
            logger.info(f"Initiating OAuth flow for user ID: {current_user.id}")
        else:
            settings = Settings.query.first()
            logger.info("Initiating OAuth flow with default settings (no user logged in)")
        
        if provider == 'schwab':
            # Generate a state parameter to prevent CSRF attacks
            state = os.urandom(16).hex()
            session['oauth_state'] = state
            
            # Get the base URL based on paper trading setting
            auth_base_url = "https://api-sandbox.schwab.com/v1/oauth2/authorize" if settings.is_paper_trading else "https://api.schwab.com/v1/oauth2/authorize"
            
            # Construct redirect URI for callback
            redirect_uri = url_for('oauth_callback', _external=True)
            
            # Create the real authorization URL
            auth_url = f"{auth_base_url}?response_type=code&client_id={settings.api_key}&redirect_uri={redirect_uri}&scope=accounts,trading&state={state}"
            
            logger.info(f"Using Schwab API key: {settings.api_key[:4]}...{settings.api_key[-4:] if len(settings.api_key) > 8 else '****'} for OAuth flow")
            logger.info(f"Redirect URI: {redirect_uri}")
            
            # Show the callback URL for configuration purposes
            flash(f"The callback URL to register in your Schwab Developer account is: {redirect_uri}", 'info')
            
            # For now, we'll still display the link rather than redirect
            # until the user has properly registered the callback URL
            flash(f"<a href='{auth_url}' class='alert-link'>Click here to authorize with Schwab</a>", 'info')
            
            return redirect(url_for('settings'))
            
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
        
        # Get the settings for the current user if logged in
        if current_user.is_authenticated:
            settings = Settings.query.filter_by(user_id=current_user.id).first()
            logger.info(f"Processing OAuth callback for user ID: {current_user.id}")
        else:
            settings = Settings.query.first()
            logger.info("Processing OAuth callback with default settings (no user logged in)")
        
        if not code:
            flash('Authentication failed: No authorization code received.', 'danger')
            return redirect(url_for('settings'))
            
        # Verify state parameter to prevent CSRF attacks
        if state != session.get('oauth_state'):
            flash('Authentication failed: Invalid state parameter.', 'danger')
            return redirect(url_for('settings'))
            
        if settings.api_provider == 'schwab':
            # Exchange the authorization code for an access token
            try:
                # Log the receipt of the authorization code (truncated for security)
                logger.info(f"Received OAuth2 authorization code: {code[:5]}...")
                
                # Get the token endpoint based on paper trading setting
                token_url = "https://api-sandbox.schwab.com/v1/oauth2/token" if settings.is_paper_trading else "https://api.schwab.com/v1/oauth2/token"
                
                # Construct redirect URI for callback (must match the one used in authorization request)
                redirect_uri = url_for('oauth_callback', _external=True)
                
                # Now perform the actual token exchange
                import requests
                token_response = requests.post(
                    token_url,
                    data={
                        'grant_type': 'authorization_code',
                        'code': code,
                        'client_id': settings.api_key,
                        'client_secret': settings.api_secret,
                        'redirect_uri': redirect_uri
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
                
                logger.info(f"Token exchange response status: {token_response.status_code}")
                
                if token_response.status_code == 200:
                    token_data = token_response.json()
                    access_token = token_data.get('access_token')
                    refresh_token = token_data.get('refresh_token')
                    expires_in = token_data.get('expires_in', 3600)  # Default to 1 hour
                    
                    # Store tokens securely
                    from datetime import timedelta
                    settings.oauth_access_token = access_token
                    settings.oauth_refresh_token = refresh_token
                    settings.oauth_token_expiry = datetime.now() + timedelta(seconds=expires_in)
                    
                    # Turn off simulation mode now that we have real tokens
                    settings.force_simulation_mode = False
                    
                    db.session.commit()
                    
                    # Store the authorization code in the session temporarily
                    session['schwab_auth_code'] = code
                    
                    # Reinitialize the app with the new tokens
                    initialize_app()
                    
                    flash('Successfully authenticated with Schwab API!', 'success')
                else:
                    # Failed to exchange code for tokens
                    error_info = token_response.text[:100]  # Truncate long error messages
                    logger.error(f"Failed to exchange authorization code for tokens: {error_info}")
                    flash(f"Failed to authenticate with Schwab: {error_info}", 'danger')
            
            except Exception as e:
                logger.error(f"Error in OAuth2 flow: {str(e)}")
                flash(f"Error in authentication flow: {str(e)}", 'danger')
        
        return redirect(url_for('settings'))
    except Exception as e:
        logger.error(f"Error in OAuth callback: {str(e)}")
        flash(f"Error in authentication flow: {str(e)}", 'danger')
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
