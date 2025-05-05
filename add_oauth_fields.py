from app import app, db
from models import Settings
from sqlalchemy import Column, DateTime

# Add OAuth token fields to Settings if they don't exist
with app.app_context():
    # Check if columns exist
    inspector = db.inspect(db.engine)
    existing_columns = [col['name'] for col in inspector.get_columns('settings')]
    
    if 'oauth_access_token' not in existing_columns:
        print("Adding oauth_access_token column to Settings table")
        db.engine.execute('ALTER TABLE settings ADD COLUMN oauth_access_token VARCHAR(255)')
    
    if 'oauth_refresh_token' not in existing_columns:
        print("Adding oauth_refresh_token column to Settings table")
        db.engine.execute('ALTER TABLE settings ADD COLUMN oauth_refresh_token VARCHAR(255)')
    
    if 'oauth_token_expiry' not in existing_columns:
        print("Adding oauth_token_expiry column to Settings table")
        db.engine.execute('ALTER TABLE settings ADD COLUMN oauth_token_expiry DATETIME')
    
    print("OAuth token fields added to Settings table")
