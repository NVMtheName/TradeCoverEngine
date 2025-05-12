"""
Configuration module for the trading bot application.
Contains environment-specific settings and constants.
"""

import os
from datetime import timedelta

# Flask application settings
DEBUG = True
SECRET_KEY = os.environ.get("SESSION_SECRET", "dev_secret_key")
PORT = 5000
HOST = '0.0.0.0'

# Database settings
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///trading_bot.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Trading API settings
DEFAULT_API_PROVIDER = 'alpaca'
PAPER_TRADING_ENABLED = True

# Session settings
PERMANENT_SESSION_LIFETIME = timedelta(days=7)

# Trading strategy defaults
DEFAULT_RISK_LEVEL = 'moderate'
DEFAULT_MAX_POSITION_SIZE = 5000.0
DEFAULT_PROFIT_TARGET_PERCENTAGE = 5.0
DEFAULT_STOP_LOSS_PERCENTAGE = 3.0
DEFAULT_OPTIONS_EXPIRY_DAYS = 30

# Technical analysis settings
TECHNICAL_INDICATORS = {
    'sma_periods': [20, 50, 200],
    'rsi_period': 14,
    'macd_fast_period': 12,
    'macd_slow_period': 26,
    'macd_signal_period': 9,
    'bollinger_period': 20,
    'bollinger_std_dev': 2
}

# Covered call strategy settings
COVERED_CALL_SETTINGS = {
    'conservative': {
        'delta_target': 0.2,
        'premium_min_percentage': 0.5,
        'strike_min_percentage': 5.0
    },
    'moderate': {
        'delta_target': 0.3,
        'premium_min_percentage': 1.0,
        'strike_min_percentage': 3.0
    },
    'aggressive': {
        'delta_target': 0.4,
        'premium_min_percentage': 1.5,
        'strike_min_percentage': 2.0
    }
}

# API request timeouts (in seconds)
API_TIMEOUT = 10

# Logging settings
LOG_LEVEL = 'DEBUG'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# API endpoints for various providers
API_ENDPOINTS = {
    'alpaca': {
        'base_url': 'https://api.alpaca.markets',
        'data_url': 'https://data.alpaca.markets',
        'paper_url': 'https://paper-api.alpaca.markets'
    },
    'td_ameritrade': {
        'base_url': 'https://api.tdameritrade.com/v1'
    },
    'interactive_brokers': {
        'base_url': 'https://localhost:5000/v1/api'
    }
}

# Supported stock exchanges
SUPPORTED_EXCHANGES = ['NASDAQ', 'NYSE', 'AMEX']

# User agent for API requests
USER_AGENT = 'TradingBot/1.0'

# Cache settings
CACHE_TIMEOUT = 300  # 5 minutes

# Chart settings
CHART_DEFAULTS = {
    'days_to_display': 90,
    'candle_interval': '1D'
}
