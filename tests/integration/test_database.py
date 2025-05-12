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
        self.test_user = models.User()
        self.test_user.username = 'testuser'
        self.test_user.email = 'testuser@example.com'
        self.test_user.password_hash = generate_password_hash('password123')
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
        user = models.User.query.filter_by(username='testuser').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'testuser@example.com')
        
        # Password should be hashed and not stored in plaintext
        self.assertNotEqual(user.password_hash, 'password123')
        
        # We'll use the check_password method from the model
        from werkzeug.security import check_password_hash
        self.assertTrue(check_password_hash(user.password_hash, 'password123'))
        self.assertFalse(check_password_hash(user.password_hash, 'wrongpassword'))
    
    def test_settings_relationship(self):
        """Test user-settings relationship"""
        # Create settings for the test user
        settings = models.Settings()
        settings.user_id = self.test_user.id
        settings.api_provider = 'schwab'
        settings.risk_level = 'moderate'
        settings.is_paper_trading = True
        db.session.add(settings)
        db.session.commit()
        
        # Settings should be associated with the user
        user_settings = models.Settings.query.filter_by(user_id=self.test_user.id).first()
        self.assertIsNotNone(user_settings)
        self.assertEqual(user_settings.api_provider, 'schwab')
        self.assertEqual(user_settings.risk_level, 'moderate')
        self.assertTrue(user_settings.is_paper_trading)
    
    def test_trades_relationship(self):
        """Test user-trades relationship"""
        # Create trades for the test user
        trade1 = models.Trade()
        trade1.user_id = self.test_user.id
        trade1.symbol = 'AAPL'
        trade1.trade_type = 'BUY_STOCK'
        trade1.quantity = 10
        trade1.price = 150.0
        trade1.status = 'OPEN'
        trade1.timestamp = datetime.now()
        
        trade2 = models.Trade()
        trade2.user_id = self.test_user.id
        trade2.symbol = 'MSFT'
        trade2.trade_type = 'COVERED_CALL'
        trade2.quantity = 5
        trade2.price = 250.0
        trade2.option_strike = 260.0
        trade2.option_expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        trade2.status = 'OPEN'
        trade2.timestamp = datetime.now()
        
        db.session.add_all([trade1, trade2])
        db.session.commit()
        
        # Query trades by user ID
        user_trades = models.Trade.query.filter_by(user_id=self.test_user.id).all()
        self.assertEqual(len(user_trades), 2)
        
        # Sort by symbol to make sure the test is deterministic
        user_trades.sort(key=lambda t: t.symbol)
        self.assertEqual(user_trades[0].symbol, 'AAPL')
        self.assertEqual(user_trades[1].symbol, 'MSFT')
        
        # Test trade querying
        open_trades = models.Trade.query.filter_by(status='OPEN').all()
        self.assertEqual(len(open_trades), 2)
        
        apple_trades = models.Trade.query.filter_by(symbol='AAPL').all()
        self.assertEqual(len(apple_trades), 1)
        self.assertEqual(apple_trades[0].quantity, 10)
    
    def test_watchlist_relationship(self):
        """Test user-watchlist relationship"""
        # Create watchlist items for the test user
        watchlist1 = models.WatchlistItem()
        watchlist1.user_id = self.test_user.id
        watchlist1.symbol = 'AAPL'
        watchlist1.notes = 'Potential covered call candidate'
        
        watchlist2 = models.WatchlistItem()
        watchlist2.user_id = self.test_user.id
        watchlist2.symbol = 'TSLA'
        watchlist2.notes = 'High IV for options'
        
        db.session.add_all([watchlist1, watchlist2])
        db.session.commit()
        
        # Query watchlist items by user ID
        user_watchlist = models.WatchlistItem.query.filter_by(user_id=self.test_user.id).all()
        self.assertEqual(len(user_watchlist), 2)
        
        # Sort by symbol to make the test deterministic
        user_watchlist.sort(key=lambda w: w.symbol)
        self.assertEqual(user_watchlist[0].symbol, 'AAPL')
        self.assertEqual(user_watchlist[1].symbol, 'TSLA')
        
        # Test watchlist querying
        apple_item = models.WatchlistItem.query.filter_by(symbol='AAPL').first()
        self.assertIsNotNone(apple_item)
        self.assertEqual(apple_item.notes, 'Potential covered call candidate')


if __name__ == '__main__':
    unittest.main()