#!/usr/bin/env python3
"""
Create a secure backdoor admin user for platform owner access.
This creates a high-privilege user with unrestricted access to all features.
"""

import os
import secrets
import string
from app import app, db
from models import User, Settings
from datetime import datetime

def generate_secure_password(length=16):
    """Generate a cryptographically secure password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def create_admin_backdoor():
    """Create a secure admin backdoor user"""
    with app.app_context():
        # Use a secure username that's not obvious
        admin_username = "arbion_master"
        admin_email = "admin@arbion.internal"
        
        # Check if admin already exists
        existing_admin = User.query.filter_by(username=admin_username).first()
        
        if existing_admin:
            print(f"⚠️  Admin backdoor user already exists: {admin_username}")
            print(f"User ID: {existing_admin.id}")
            print(f"Access Level: {existing_admin.access_level}")
            print(f"Is Admin: {existing_admin.is_admin}")
            return existing_admin
        
        # Generate secure password
        admin_password = generate_secure_password(20)
        
        # Create admin user with maximum privileges
        admin_user = User(
            username=admin_username,
            email=admin_email,
            is_admin=True,
            access_level='admin',
            is_active=True,
            created_at=datetime.now()
        )
        admin_user.set_password(admin_password)
        
        db.session.add(admin_user)
        db.session.commit()
        
        # Create premium settings for admin user
        admin_settings = Settings(
            user_id=admin_user.id,
            api_provider='schwab',
            api_key=os.environ.get('SCHWAB_API_KEY', ''),
            api_secret=os.environ.get('SCHWAB_API_SECRET', ''),
            is_paper_trading=False,  # Allow real trading
            force_simulation_mode=False,
            risk_level='aggressive',  # Maximum risk level
            max_position_size=100000.0,  # High position limits
            profit_target_percentage=10.0,
            stop_loss_percentage=2.0,
            options_expiry_days=45,
            enabled_strategies='covered_call,cash_secured_put,iron_condor,strangle',
            forex_leverage=50.0,  # High leverage
            forex_lot_size=1.0,   # Full lot size
            forex_pairs_watchlist='EUR/USD,GBP/USD,USD/JPY,USD/CHF,AUD/USD,USD/CAD,NZD/USD',
            openai_api_key=os.environ.get('OPENAI_API_KEY', ''),
            enable_ai_advisor=True,
            ai_model_selection='premium',  # Best AI models
            updated_at=datetime.now()
        )
        
        db.session.add(admin_settings)
        db.session.commit()
        
        print("🔐 SECURE ADMIN BACKDOOR CREATED")
        print("=" * 50)
        print(f"Username: {admin_username}")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
        print(f"User ID: {admin_user.id}")
        print(f"Settings ID: {admin_settings.id}")
        print("=" * 50)
        print("⚠️  IMPORTANT: Save these credentials securely!")
        print("⚠️  This user has FULL UNRESTRICTED ACCESS to the platform")
        print("⚠️  Delete this script after saving credentials")
        
        return admin_user

def verify_admin_access():
    """Verify that the admin user has proper access"""
    with app.app_context():
        admin_user = User.query.filter_by(username="arbion_master").first()
        
        if not admin_user:
            print("❌ Admin user not found")
            return False
            
        print("✅ Admin Access Verification:")
        print(f"   Username: {admin_user.username}")
        print(f"   Is Admin: {admin_user.is_admin}")
        print(f"   Access Level: {admin_user.access_level}")
        print(f"   Has Admin Access: {admin_user.has_admin_access()}")
        print(f"   Has Premium Access: {admin_user.has_premium_access()}")
        
        # Check settings
        settings = Settings.query.filter_by(user_id=admin_user.id).first()
        if settings:
            print(f"   Max Position Size: ${settings.max_position_size:,.2f}")
            print(f"   Risk Level: {settings.risk_level}")
            print(f"   AI Model: {settings.ai_model_selection}")
        
        return True

if __name__ == "__main__":
    print("Creating secure admin backdoor user...")
    admin_user = create_admin_backdoor()
    print("\nVerifying admin access...")
    verify_admin_access()
    print("\nDone!")