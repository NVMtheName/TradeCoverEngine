import pytest
from bs4 import BeautifulSoup

# Fixtures are imported from conftest.py automatically


def test_index_route(client):
    """Test the index route"""
    response = client.get('/')
    assert response.status_code == 200
    # Should contain login and register links when not logged in
    assert b'Login' in response.data
    assert b'Register' in response.data


def test_login_route(client):
    """Test the login route"""
    # Get login page
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data
    
    # Test successful login
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Dashboard' in response.data
    
    # Test invalid login
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid username or password' in response.data


def test_register_route(client):
    """Test the register route"""
    # Get register page
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Register' in response.data
    
    # Test successful registration
    response = client.post('/register', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Account created' in response.data or b'Dashboard' in response.data
    
    # Test duplicate username
    response = client.post('/register', data={
        'username': 'testuser',  # Existing username
        'email': 'different@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Username already exists' in response.data or b'already taken' in response.data


def test_dashboard_route(authenticated_client):
    """Test the dashboard route (requires authentication)"""
    response = authenticated_client.get('/dashboard')
    assert response.status_code == 200
    assert b'Dashboard' in response.data
    
    # Check for key dashboard elements
    soup = BeautifulSoup(response.data, 'html.parser')
    assert soup.find(id='watchlist') is not None
    assert soup.find(id='account-summary') is not None or soup.find(class_='account-summary') is not None


def test_settings_route(authenticated_client):
    """Test the settings route (requires authentication)"""
    response = authenticated_client.get('/settings')
    assert response.status_code == 200
    assert b'Settings' in response.data
    
    # Check for key settings elements
    soup = BeautifulSoup(response.data, 'html.parser')
    assert soup.find(id='api-settings') is not None or soup.find(class_='api-settings') is not None
    assert soup.find(id='risk-settings') is not None or soup.find(class_='risk-settings') is not None
    
    # Test settings update (partial)
    response = authenticated_client.post('/settings', data={
        'risk_level': 'aggressive',
        'is_paper_trading': 'y'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Settings updated' in response.data or b'saved' in response.data


def test_strategy_info_route(authenticated_client):
    """Test the strategy information route"""
    response = authenticated_client.get('/strategy_info')
    assert response.status_code == 200
    assert b'Trading Strategies' in response.data
    
    # Check for strategy information sections
    soup = BeautifulSoup(response.data, 'html.parser')
    strategies = soup.find_all(class_='strategy-card') or soup.find_all(class_='card')
    assert len(strategies) > 0


def test_logout_route(authenticated_client):
    """Test the logout route"""
    # First verify we are logged in
    response = authenticated_client.get('/dashboard')
    assert response.status_code == 200
    
    # Now logout
    response = authenticated_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify we are logged out by checking for login link
    assert b'Login' in response.data
    
    # Dashboard should now redirect to login
    response = authenticated_client.get('/dashboard')
    assert response.status_code == 302  # Redirect status