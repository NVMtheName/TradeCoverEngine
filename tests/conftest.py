"""
Configuration and fixtures for pytest testing.
"""

import os
import pytest
from app import app as flask_app
from app import db

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Configure app for testing
    flask_app.config.update({
        'TESTING': True,
        'DEBUG': True,
        'SQLALCHEMY_DATABASE_URI': os.environ.get('DATABASE_URL', 'sqlite:///:memory:'),
    })

    # Create the test client
    with flask_app.app_context():
        # Create tables
        db.create_all()
        
        yield flask_app
        
        # Clean up
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Test client for the Flask app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Test CLI runner for the Flask app."""
    return app.test_cli_runner()

@pytest.fixture
def db_session(app):
    """Database session for testing."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        session = db.scoped_session(
            db.sessionmaker(autocommit=False, autoflush=False, bind=connection)
        )
        
        db.session = session
        
        yield db.session
        
        transaction.rollback()
        connection.close()
        db.session.remove()

@pytest.fixture
def db(app):
    """Database object for testing."""
    return db