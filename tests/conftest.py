import os
import sys
import pytest

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import User, Settings


@pytest.fixture(scope='function')
def test_app():
    """Fixture to provide a Flask app with a test database"""
    # Configure the app for testing
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Create database and context
    with app.app_context():
        db.create_all()
        
        # Create a test user
        test_user = User(
            username='testuser',
            email='testuser@example.com'
        )
        test_user.set_password('password123')
        db.session.add(test_user)
        
        # Create default settings
        test_settings = Settings(
            user_id=1,
            api_provider='schwab',
            is_paper_trading=True,
            force_simulation_mode=True,
            risk_level='moderate'
        )
        db.session.add(test_settings)
        db.session.commit()
        
        yield app
        
        # Clean up
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(test_app):
    """Fixture to provide a Flask test client"""
    return test_app.test_client()


@pytest.fixture(scope='function')
def authenticated_client(test_app):
    """Fixture to provide an authenticated Flask test client"""
    with test_app.test_client() as client:
        # Log in the test user
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        }, follow_redirects=True)
        yield client