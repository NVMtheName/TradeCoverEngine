"""
Basic tests to verify application functionality.
This file ensures that the basic app structure is working.
"""

def test_app_exists(app):
    """Test that the Flask app exists."""
    assert app is not None

def test_home_page(client):
    """Test that the home page loads."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Trading Bot' in response.data

def test_login_page(client):
    """Test that the login page loads."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data

def test_register_page(client):
    """Test that the register page loads."""
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Register' in response.data