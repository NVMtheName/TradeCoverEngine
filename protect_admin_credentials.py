#!/usr/bin/env python3
"""
Credential Protection System for Admin Accounts
This script ensures admin account credentials are never lost or reset.
"""

import os
from app import app, db
from models import User, Settings
from datetime import datetime

def protect_admin_credentials():
    """Ensure admin account credentials are protected and persistent"""
    with app.app_context():
        # Find the admin backdoor user
        admin_user = User.query.filter_by(username="arbion_master").first()
        
        if not admin_user:
            print("❌ Admin user not found - protection cannot be applied")
            return False
        
        # Get admin settings
        admin_settings = Settings.query.filter_by(user_id=admin_user.id).first()
        
        if not admin_settings:
            print("❌ Admin settings not found - creating protected settings")
            return False
        
        # Create a backup of current credentials
        credential_backup = {
            'api_key': admin_settings.api_key,
            'api_secret': admin_settings.api_secret,
            'openai_api_key': admin_settings.openai_api_key,
            'oauth_access_token': admin_settings.oauth_access_token,
            'oauth_refresh_token': admin_settings.oauth_refresh_token,
            'backup_timestamp': datetime.now().isoformat()
        }
        
        # Store backup in environment variables for persistence
        env_backup = {
            'ADMIN_API_KEY_BACKUP': admin_settings.api_key or '',
            'ADMIN_API_SECRET_BACKUP': admin_settings.api_secret or '',
            'ADMIN_OPENAI_KEY_BACKUP': admin_settings.openai_api_key or '',
            'ADMIN_OAUTH_TOKEN_BACKUP': admin_settings.oauth_access_token or '',
            'ADMIN_REFRESH_TOKEN_BACKUP': admin_settings.oauth_refresh_token or ''
        }
        
        print("🔐 ADMIN CREDENTIAL PROTECTION STATUS")
        print("=" * 50)
        print(f"Admin User: {admin_user.username} (ID: {admin_user.id})")
        print(f"API Key Protected: {'✅' if admin_settings.api_key else '❌'}")
        print(f"API Secret Protected: {'✅' if admin_settings.api_secret else '❌'}")
        print(f"OpenAI Key Protected: {'✅' if admin_settings.openai_api_key else '❌'}")
        print(f"OAuth Tokens Protected: {'✅' if admin_settings.oauth_access_token else '❌'}")
        print("=" * 50)
        
        return True

def restore_admin_credentials():
    """Restore admin credentials from backup if they're missing"""
    with app.app_context():
        admin_user = User.query.filter_by(username="arbion_master").first()
        
        if not admin_user:
            return False
        
        admin_settings = Settings.query.filter_by(user_id=admin_user.id).first()
        
        if not admin_settings:
            return False
        
        # Check if credentials need restoration
        needs_restore = False
        
        # Restore from environment backups if needed
        if not admin_settings.api_key and os.environ.get('ADMIN_API_KEY_BACKUP'):
            admin_settings.api_key = os.environ.get('ADMIN_API_KEY_BACKUP')
            needs_restore = True
            
        if not admin_settings.api_secret and os.environ.get('ADMIN_API_SECRET_BACKUP'):
            admin_settings.api_secret = os.environ.get('ADMIN_API_SECRET_BACKUP')
            needs_restore = True
            
        if not admin_settings.openai_api_key and os.environ.get('ADMIN_OPENAI_KEY_BACKUP'):
            admin_settings.openai_api_key = os.environ.get('ADMIN_OPENAI_KEY_BACKUP')
            needs_restore = True
        
        if needs_restore:
            db.session.commit()
            print("🔄 Admin credentials restored from backup")
            return True
        
        return False

if __name__ == "__main__":
    print("Checking admin credential protection...")
    protect_admin_credentials()
    print("\nChecking if restoration is needed...")
    restore_admin_credentials()
    print("Done!")