#!/usr/bin/env python3
"""
Auto-configure master account with API credentials from secure environment
This script runs automatically when environment secrets are available
"""

import os
from app import app, db
from models import User, Settings
from datetime import datetime

def auto_configure_master_credentials():
    """Automatically configure master account with environment credentials"""
    with app.app_context():
        # Find the master account
        master_user = User.query.filter_by(username="arbion_master").first()
        
        if not master_user:
            print("Master account not found")
            return False
        
        # Get master account settings
        master_settings = Settings.query.filter_by(user_id=master_user.id).first()
        
        if not master_settings:
            print("Master account settings not found")
            return False
        
        # Check for available environment credentials
        openai_key = os.environ.get('OPENAI_API_KEY')
        schwab_key = os.environ.get('SCHWAB_API_KEY') 
        schwab_secret = os.environ.get('SCHWAB_API_SECRET')
        
        # Update master account with available credentials
        updated = False
        
        if openai_key and openai_key != master_settings.openai_api_key:
            master_settings.openai_api_key = openai_key
            updated = True
            print(f"✓ Updated OpenAI API key for master account")
        
        if schwab_key and schwab_key != master_settings.api_key:
            master_settings.api_key = schwab_key
            updated = True
            print(f"✓ Updated Schwab API key for master account")
        
        if schwab_secret and schwab_secret != master_settings.api_secret:
            master_settings.api_secret = schwab_secret
            updated = True
            print(f"✓ Updated Schwab API secret for master account")
        
        if updated:
            # Ensure optimal settings for master account
            master_settings.enable_ai_advisor = True
            master_settings.ai_model_selection = 'premium'
            master_settings.api_provider = 'schwab'
            master_settings.is_paper_trading = False  # Enable real trading for master
            master_settings.force_simulation_mode = False
            master_settings.updated_at = datetime.now()
            
            # Commit changes
            try:
                db.session.commit()
                print(f"🔐 Master account credentials configured and stored permanently")
                print(f"   - OpenAI API: {'configured' if openai_key else 'pending'}")
                print(f"   - Schwab API: {'configured' if schwab_key else 'pending'}")
                print(f"   - Schwab Secret: {'configured' if schwab_secret else 'pending'}")
                return True
            except Exception as e:
                db.session.rollback()
                print(f"Failed to save master account settings: {e}")
                return False
        else:
            print("Master account credentials already up to date")
            return True

if __name__ == "__main__":
    print("Auto-configuring master account with available credentials...")
    success = auto_configure_master_credentials()
    if success:
        print("Master account configuration complete!")
    else:
        print("Master account configuration failed!")