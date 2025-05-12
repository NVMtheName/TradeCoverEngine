"""
Integration tests for database models.
"""

import pytest
from models import User, Settings, Trade, WatchlistItem


def test_user_model(db):
    """Test User model creation and querying."""
    # Create a new user
    user = User(
        username='dbtest',
        email='db@example.com',
    )
    user.set_password('Password123')
    
    # Add to database
    db.session.add(user)
    db.session.commit()
    
    # Query the user
    queried_user = User.query.filter_by(username='dbtest').first()
    assert queried_user is not None
    assert queried_user.email == 'db@example.com'
    assert queried_user.check_password('Password123')
    assert not queried_user.check_password('WrongPassword')


def test_settings_model(db):
    """Test Settings model creation and relationship to User."""
    # Create a new user
    user = User(
        username='settingstest',
        email='settings@example.com',
    )
    user.set_password('Password123')
    db.session.add(user)
    db.session.commit()
    
    # Create settings for the user
    settings = Settings(
        user_id=user.id,
        api_provider='schwab',
        risk_level='moderate',
        is_paper_trading=True,
    )
    db.session.add(settings)
    db.session.commit()
    
    # Query the settings
    queried_settings = Settings.query.filter_by(user_id=user.id).first()
    assert queried_settings is not None
    assert queried_settings.api_provider == 'schwab'
    assert queried_settings.risk_level == 'moderate'
    assert queried_settings.is_paper_trading is True
    
    # Test relationship
    assert queried_settings.user.username == 'settingstest'


def test_trade_model(db):
    """Test Trade model creation and relationship to User."""
    # Create a new user
    user = User(
        username='tradetest',
        email='trade@example.com',
    )
    user.set_password('Password123')
    db.session.add(user)
    db.session.commit()
    
    # Create a trade for the user
    trade = Trade(
        user_id=user.id,
        symbol='AAPL',
        trade_type='BUY_STOCK',
        quantity=10,
        price=150.0,
        status='OPEN',
    )
    db.session.add(trade)
    db.session.commit()
    
    # Query the trade
    queried_trade = Trade.query.filter_by(user_id=user.id).first()
    assert queried_trade is not None
    assert queried_trade.symbol == 'AAPL'
    assert queried_trade.trade_type == 'BUY_STOCK'
    assert queried_trade.quantity == 10
    assert queried_trade.price == 150.0
    assert queried_trade.status == 'OPEN'
    
    # Test relationship
    assert queried_trade.user.username == 'tradetest'


def test_watchlist_item_model(db):
    """Test WatchlistItem model creation and relationship to User."""
    # Create a new user
    user = User(
        username='watchlisttest',
        email='watchlist@example.com',
    )
    user.set_password('Password123')
    db.session.add(user)
    db.session.commit()
    
    # Create a watchlist item for the user
    watchlist_item = WatchlistItem(
        user_id=user.id,
        symbol='MSFT',
        notes='Potential covered call candidate',
    )
    db.session.add(watchlist_item)
    db.session.commit()
    
    # Query the watchlist item
    queried_item = WatchlistItem.query.filter_by(user_id=user.id).first()
    assert queried_item is not None
    assert queried_item.symbol == 'MSFT'
    assert queried_item.notes == 'Potential covered call candidate'
    
    # Test relationship
    assert queried_item.user.username == 'watchlisttest'


def test_user_relationships(db):
    """Test User relationships to other models."""
    # Create a new user
    user = User(
        username='relationtest',
        email='relation@example.com',
    )
    user.set_password('Password123')
    db.session.add(user)
    db.session.commit()
    
    # Create settings, trades, and watchlist items
    settings = Settings(user_id=user.id, api_provider='schwab')
    trade1 = Trade(user_id=user.id, symbol='AAPL', trade_type='BUY_STOCK', quantity=10, price=150.0)
    trade2 = Trade(user_id=user.id, symbol='MSFT', trade_type='BUY_STOCK', quantity=5, price=250.0)
    watchlist1 = WatchlistItem(user_id=user.id, symbol='GOOG')
    watchlist2 = WatchlistItem(user_id=user.id, symbol='AMZN')
    
    db.session.add_all([settings, trade1, trade2, watchlist1, watchlist2])
    db.session.commit()
    
    # Query the user
    queried_user = User.query.filter_by(username='relationtest').first()
    
    # Test relationships
    assert len(queried_user.settings) == 1
    assert queried_user.settings[0].api_provider == 'schwab'
    
    assert len(queried_user.trades) == 2
    assert queried_user.trades[0].symbol in ['AAPL', 'MSFT']
    assert queried_user.trades[1].symbol in ['AAPL', 'MSFT']
    
    assert len(queried_user.watchlist_items) == 2
    assert queried_user.watchlist_items[0].symbol in ['GOOG', 'AMZN']
    assert queried_user.watchlist_items[1].symbol in ['GOOG', 'AMZN']