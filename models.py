from datetime import datetime, timedelta
from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    trades = db.relationship('Trade', backref='user', lazy=True)
    
    def set_password(self, password):
        """Set password hash for user"""
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against stored hash"""
        from werkzeug.security import check_password_hash
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False
        
    def __repr__(self):
        return f'<User {self.username}>'

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # API settings
    api_provider = db.Column(db.String(50), default='alpaca')  # Options: alpaca, td_ameritrade, etc.
    api_key = db.Column(db.String(255))  # Client ID for OAuth2
    api_secret = db.Column(db.String(255))  # Client Secret for OAuth2
    is_paper_trading = db.Column(db.Boolean, default=True)
    force_simulation_mode = db.Column(db.Boolean, default=False)  # Force simulation mode (no API needed)
    
    # OAuth2 tokens
    oauth_access_token = db.Column(db.String(1024))  # Access token from OAuth2 flow
    oauth_refresh_token = db.Column(db.String(1024))  # Refresh token from OAuth2 flow
    oauth_token_expiry = db.Column(db.DateTime)  # When the access token expires
    
    # Strategy settings
    risk_level = db.Column(db.String(20), default='moderate')  # Options: conservative, moderate, aggressive
    max_position_size = db.Column(db.Float, default=5000.0)  # Maximum $ amount per position
    profit_target_percentage = db.Column(db.Float, default=5.0)
    stop_loss_percentage = db.Column(db.Float, default=3.0)
    options_expiry_days = db.Column(db.Integer, default=30)  # Target days until expiration
    enabled_strategies = db.Column(db.String(255), default='covered_call')  # Comma-separated list of enabled strategies
    
    # Forex specific settings
    forex_leverage = db.Column(db.Float, default=10.0)  # Leverage for forex trading (10:1)
    forex_lot_size = db.Column(db.Float, default=0.1)  # Default lot size for forex trades (mini lot)
    forex_pairs_watchlist = db.Column(db.String(255), default='EUR/USD,GBP/USD,USD/JPY')  # Watchlist of forex pairs
    
    # AI advisor settings
    openai_api_key = db.Column(db.String(255))  # OpenAI API key for AI features
    enable_ai_advisor = db.Column(db.Boolean, default=True)  # Whether AI advisor is enabled
    ai_model_selection = db.Column(db.String(50), default='auto')  # How to select models (auto, ensemble, cost_effective, premium)
    
    # Last updated timestamp
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationship with User
    user = db.relationship('User', backref='settings', lazy=True)
    
    def __repr__(self):
        return f'<Settings {self.api_provider}>'

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    symbol = db.Column(db.String(10), nullable=False)
    trade_type = db.Column(db.String(50), nullable=False)  # COVERED_CALL, BUY_STOCK, SELL_CALL, etc.
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    # Option specific fields
    option_strike = db.Column(db.Float, nullable=True)
    option_expiry = db.Column(db.String(20), nullable=True)
    
    # Status and timestamps
    status = db.Column(db.String(20), default='OPEN')  # OPEN, CLOSED, EXPIRED, ASSIGNED
    timestamp = db.Column(db.DateTime, default=datetime.now)
    closed_at = db.Column(db.DateTime, nullable=True)
    profit_loss = db.Column(db.Float, nullable=True)
    
    def __repr__(self):
        return f'<Trade {self.symbol} {self.trade_type} {self.timestamp}>'

class WatchlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    symbol = db.Column(db.String(10), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.now)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationship with User
    user = db.relationship('User', backref='watchlist_items', lazy=True)
    
    # Define a unique constraint for symbol per user
    __table_args__ = (db.UniqueConstraint('user_id', 'symbol', name='unique_user_symbol'),)
    
    def __repr__(self):
        return f'<WatchlistItem {self.symbol}>'
