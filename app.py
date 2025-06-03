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
import requests
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# Custom JSON encoder to handle pandas DataFrames and numpy arrays
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, pd.DataFrame):
            return o.to_dict(orient='records')
        elif isinstance(o, pd.Series):
            return o.to_dict()
        elif isinstance(o, np.ndarray):
            return o.tolist()
        elif isinstance(o, np.integer):
            return int(o)
        elif isinstance(o, np.floating):
            return float(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

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

# Set session permanency and lifetime
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_session')
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'trading_bot_session'

# Import Flask-Session extension for server-side sessions
try:
    from flask_session import Session
    sess = Session()
    sess.init_app(app)
    logger.info("Flask-Session initialized successfully")
except ImportError:
    logger.warning("Flask-Session not installed. Using Flask's default client-side sessions.")

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Add datetime and now() function to Jinja context
app.jinja_env.globals.update(datetime=datetime)
app.jinja_env.globals.update(now=lambda: datetime.now())

# Configure database
db_url = os.environ.get("DATABASE_URL", "sqlite:///trading_bot.db")
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

# Initialize CSRF protection
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Global variables to track components
api_connector = None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            user.last_login = datetime.now()
            db.session.commit()
            session['user_id'] = user.id
            
            logger.info(f"User {user.username} (ID: {user.id}) logged in successfully")
            
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
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logger.info(f"User {current_user.username} logging out")
    session.pop('user_id', None)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    account_info = {'api_status': 'Simulation Mode', 'balance': 10000.0}
    recent_trades = []
    open_positions = []
    performance_data = {
        'total_return': 0.0,
        'daily_pnl': 0.0,
        'monthly_returns': {'months': [], 'returns': []}
    }
    
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
    
    if not settings:
        settings = Settings(user_id=current_user.id)
        db.session.add(settings)
        db.session.commit()
    
    if request.method == 'POST':
        try:
            db.session.commit()
            flash('Settings updated successfully!', 'success')
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            flash(f'Error updating settings: {str(e)}', 'danger')
    
    return render_template('settings.html', settings=settings)

@app.route('/trades')
@login_required
def trades():
    user_trades = Trade.query.filter_by(user_id=current_user.id).order_by(Trade.timestamp.desc()).all()
    return render_template('trades.html', trades=user_trades)

@app.route('/analysis')
@login_required
def analysis():
    return render_template('analysis.html')

@app.route('/auto_trading')
@login_required
def auto_trading():
    return render_template('auto_trading.html')

@app.route('/stock_data/<symbol>')
@login_required
def stock_data(symbol):
    """Get stock data for a symbol via AJAX"""
    return jsonify({
        'symbol': symbol.upper(),
        'price': 150.00,
        'change': 2.50,
        'change_percent': 1.69,
        'status': 'simulation'
    })

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return "Internal Server Error", 500

# Initialize the application
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
