import os
import sqlite3
from datetime import datetime
from app import app, db

# Check if database file exists and delete it
with app.app_context():
    db_path = os.path.join('instance', 'trading_bot.db')
    if os.path.exists(db_path):
        print(f"Removing existing database: {db_path}")
        os.remove(db_path)
    
    # Create all tables based on the updated models
    db.create_all()
    print("New database created with updated schema")
    
    # Create default settings if needed
    from models import Settings
    if not Settings.query.first():
        default_settings = Settings(
            api_provider='alpaca',
            risk_level='moderate',
            max_position_size=5000.0,
            profit_target_percentage=5.0,
            stop_loss_percentage=3.0,
            options_expiry_days=30,
            enabled_strategies='covered_call'
        )
        db.session.add(default_settings)
        db.session.commit()
        print("Default settings created")

print("Database reset completed successfully")
