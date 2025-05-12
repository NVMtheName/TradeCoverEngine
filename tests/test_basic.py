"""
Basic tests for the trading bot application.
"""
import os
import sys
import unittest

# Add parent directory to path to import main application
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

class TestBasicApp(unittest.TestCase):
    """Basic tests for the Flask application."""

    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_home_page(self):
        """Test that home page loads."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
    def test_app_exists(self):
        """Test the app exists."""
        self.assertIsNotNone(app)

if __name__ == '__main__':
    unittest.main()