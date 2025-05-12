import os
import sys
import unittest
from datetime import datetime, timedelta

# Add parent directory to path to import modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the database app context and models
# Use literal imports for all models to avoid any LSP issues
from app import app, db
from werkzeug.security import generate_password_hash
import models


class TestDatabaseIntegration(unittest.TestCase):
    """Test database models and relationships"""
    
    def setUp(self):
        """Set up test environment"""
        # Use an in-memory SQLite database for testing
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create a test user
        self.test_user = User(
            username='testuser',
            email='testuser@example.com'
        )
        self.test_user.set_password('password123')
        db.session.add(self.test_user)
        db.session.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_user_creation(self):
        """Test user creation and password hashing"""
        # User should exist in database
        user = User.query.filter_by(username='testuser').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'testuser@example.com')
        
        # Password should be hashed and verifiable
        self.assertNotEqual(user.password_hash, 'password123')
        self.assertTrue(user.check_password('password123'))
        self.assertFalse(user.check_password('wrongpassword'))
    
    def test_settings_relationship(self):
        """Test user-settings relationship"""
        # Create settings for the test user
        settings = Settings(
            user_id=self.test_user.id,
            api_provider='schwab',
            risk_level='moderate',
            is_paper_trading=True
        )
        db.session.add(settings)
        db.session.commit()
        
        # Settings should be associated with the user
        user_settings = self.test_user.settings.first()
        self.assertIsNotNone(user_settings)
        self.assertEqual(user_settings.api_provider, 'schwab')
        self.assertEqual(user_settings.risk_level, 'moderate')
        self.assertTrue(user_settings.is_paper_trading)
    
    def test_trades_relationship(self):
        """Test user-trades relationship"""
        # Create trades for the test user
        trade1 = Trade(
            user_id=self.test_user.id,
            symbol='AAPL',
            trade_type='BUY_STOCK',
            quantity=10,
            price=150.0,
            status='OPEN',
            timestamp=datetime.now()
        )
        trade2 = Trade(
            user_id=self.test_user.id,
            symbol='MSFT',
            trade_type='COVERED_CALL',
            quantity=5,
            price=250.0,
            option_strike=260.0,
            option_expiry=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            status='OPEN',
            timestamp=datetime.now()
        )
        db.session.add_all([trade1, trade2])
        db.session.commit()
        
        # Trades should be associated with the user
        user_trades = self.test_user.trades
        self.assertEqual(len(user_trades), 2)
        self.assertEqual(user_trades[0].symbol, 'AAPL')
        self.assertEqual(user_trades[1].symbol, 'MSFT')
        
        # Test trade querying
        open_trades = Trade.query.filter_by(status='OPEN').all()
        self.assertEqual(len(open_trades), 2)
        
        apple_trades = Trade.query.filter_by(symbol='AAPL').all()
        self.assertEqual(len(apple_trades), 1)
        self.assertEqual(apple_trades[0].quantity, 10)
    
    def test_watchlist_relationship(self):
        """Test user-watchlist relationship"""
        # Create watchlist items for the test user
        watchlist1 = WatchlistItem(
            user_id=self.test_user.id,
            symbol='AAPL',
            notes='Potential covered call candidate'
        )
        watchlist2 = WatchlistItem(
            user_id=self.test_user.id,
            symbol='TSLA',
            notes='High IV for options'
        )
        db.session.add_all([watchlist1, watchlist2])
        db.session.commit()
        
        # Watchlist items should be associated with the user
        user_watchlist = self.test_user.watchlist_items
        self.assertEqual(len(user_watchlist), 2)
        self.assertEqual(user_watchlist[0].symbol, 'AAPL')
        self.assertEqual(user_watchlist[1].symbol, 'TSLA')
        
        # Test watchlist querying
        apple_item = WatchlistItem.query.filter_by(symbol='AAPL').first()
        self.assertIsNotNone(apple_item)
        self.assertEqual(apple_item.notes, 'Potential covered call candidate')


if __name__ == '__main__':
    unittest.main()