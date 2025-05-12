"""
Integration tests for Flask routes.
"""

import pytest


def test_index_route(client):
    """Test that the home page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Trading Bot' in response.data


def test_login_route(client):
    """Test that the login page loads correctly."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data
    assert b'Username' in response.data
    assert b'Password' in response.data


def test_register_route(client):
    """Test that the registration page loads correctly."""
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Register' in response.data
    assert b'Username' in response.data
    assert b'Email' in response.data
    assert b'Password' in response.data


def test_logout_redirect(client):
    """Test that logout redirects to home."""
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Trading Bot' in response.data


def test_protected_routes_redirect(client):
    """Test that protected routes redirect to login when not authenticated."""
    protected_routes = [
        '/dashboard',
        '/settings',
        '/trades',
        '/analysis',
        '/strategy_info',
        '/api_diagnostics',
        '/auto_trading',
    ]
    
    for route in protected_routes:
        response = client.get(route, follow_redirects=True)
        assert response.status_code == 200
        assert b'Login' in response.data


def test_registration(client, db):
    """Test user registration."""
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123',
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Account created successfully' in response.data or b'Login' in response.data
    
    # Check database for the new user
    from models import User
    user = User.query.filter_by(username='testuser').first()
    assert user is not None
    assert user.email == 'test@example.com'


def test_login(client, db):
    """Test user login with a test user."""
    # First create a test user
    from models import User
    from werkzeug.security import generate_password_hash
    
    user = User(
        username='logintest',
        email='login@example.com',
    )
    user.password_hash = generate_password_hash('Password123')
    db.session.add(user)
    db.session.commit()
    
    # Try to login
    response = client.post('/login', data={
        'username': 'logintest',
        'password': 'Password123',
        'remember': False
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Dashboard' in response.data or b'Trading Bot' in response.data