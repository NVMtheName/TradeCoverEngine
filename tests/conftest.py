"""
Pytest configuration file for tests.
"""

import os
import sys
import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Add the parent directory to sys.path so that imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as flask_app
from app import db as flask_db


@pytest.fixture
def app():
    """
    Create a Flask app for testing.
    """
    # Override config for testing
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': os.environ.get('DATABASE_URL', 'sqlite:///:memory:'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    
    # Set up app context
    with flask_app.app_context():
        yield flask_app


@pytest.fixture
def client(app):
    """
    Create a test client for the app.
    """
    return app.test_client()


@pytest.fixture
def db(app):
    """
    Provide the database instance.
    """
    # Set up clean tables for tests
    with app.app_context():
        flask_db.create_all()
        yield flask_db
        flask_db.session.remove()
        flask_db.drop_all()