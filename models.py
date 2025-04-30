from datetime import datetime, timedelta
from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    trades = db.relationship('Trade', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # API settings
    api_provider = db.Column(db.String(50), default='alpaca')  # Options: alpaca, td_ameritrade, etc.
    api_key = db.Column(db.String(100))
    api_secret = db.Column(db.String(100))
    is_paper_trading = db.Column(db.Boolean, default=True)
    
    # Strategy settings
    risk_level = db.Column(db.String(20), default='moderate')  # Options: conservative, moderate, aggressive
    max_position_size = db.Column(db.Float, default=5000.0)  # Maximum $ amount per position
    profit_target_percentage = db.Column(db.Float, default=5.0)
    stop_loss_percentage = db.Column(db.Float, default=3.0)
    options_expiry_days = db.Column(db.Integer, default=30)  # Target days until expiration
    
    # Last updated timestamp
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
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
    symbol = db.Column(db.String(10), nullable=False, unique=True)
    added_at = db.Column(db.DateTime, default=datetime.now)
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<WatchlistItem {self.symbol}>'
