import os
import sys
import pytest
from werkzeug.security import generate_password_hash

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
import models


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
        test_user = models.User()
        test_user.username = 'testuser'
        test_user.email = 'testuser@example.com'
        test_user.password_hash = generate_password_hash('password123')
        db.session.add(test_user)
        db.session.flush()  # Flush to get the ID without committing
        
        # Create default settings
        test_settings = models.Settings()
        test_settings.user_id = test_user.id
        test_settings.api_provider = 'schwab'
        test_settings.is_paper_trading = True
        test_settings.force_simulation_mode = True
        test_settings.risk_level = 'moderate'
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