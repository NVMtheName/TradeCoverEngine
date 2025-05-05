"""
Create a test user and settings in the database.
"""
from app import app, db
from models import User, Settings
from datetime import datetime

def create_test_user():
    with app.app_context():
        # Check if we already have a test user
        test_user = User.query.filter_by(username='admin').first()
        
        if test_user:
            print(f"Test user already exists: {test_user.username} (ID: {test_user.id})")
        else:
            # Create test user
            test_user = User(
                username='admin',
                email='admin@example.com'
            )
            test_user.set_password('password123')
            db.session.add(test_user)
            db.session.commit()
            print(f"Created test user: admin (ID: {test_user.id})")
        
        # Check if test user has settings
        test_settings = Settings.query.filter_by(user_id=test_user.id).first()
        
        if test_settings:
            print(f"Test user already has settings (ID: {test_settings.id})")
            
            # Update settings with OAuth fields
            test_settings.api_provider = 'schwab'
            test_settings.api_key = os.environ.get('SCHWAB_API_KEY', '')
            test_settings.api_secret = os.environ.get('SCHWAB_API_SECRET', '')
            test_settings.is_paper_trading = True
            test_settings.force_simulation_mode = False
            
            db.session.commit()
            print("Updated test user settings")
        else:
            # Create settings for test user
            test_settings = Settings(
                user_id=test_user.id,
                api_provider='schwab',
                api_key=os.environ.get('SCHWAB_API_KEY', ''),
                api_secret=os.environ.get('SCHWAB_API_SECRET', ''),
                is_paper_trading=True,
                force_simulation_mode=False,
                risk_level='moderate',
                max_position_size=5000.0,
                profit_target_percentage=5.0,
                stop_loss_percentage=3.0,
                options_expiry_days=30,
                enabled_strategies='covered_call',
                forex_leverage=10.0,
                forex_lot_size=0.1,
                forex_pairs_watchlist='EUR/USD,GBP/USD,USD/JPY',
                updated_at=datetime.now()
            )
            db.session.add(test_settings)
            db.session.commit()
            print(f"Created settings for test user (ID: {test_settings.id})")

if __name__ == "__main__":
    import os
    create_test_user()
