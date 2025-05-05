"""
Migrate the settings table to add OAuth token fields.
"""
import os
from sqlalchemy import create_engine, MetaData, Table, Column, String, DateTime
from datetime import datetime

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///instance/trading_bot.db")

def run_migration():
    print(f"Using database: {DATABASE_URL}")
    
    # Create engine and connect to the database
    engine = create_engine(DATABASE_URL)
    
    # Create metadata object
    metadata = MetaData()
    
    # Reflect existing tables
    metadata.reflect(bind=engine)
    
    # Check if settings table exists
    if 'settings' not in metadata.tables:
        print("Settings table not found!")
        return
    
    # Get settings table
    settings = metadata.tables['settings']
    
    # Define columns to add
    columns_to_add = {
        'oauth_access_token': Column('oauth_access_token', String(1024)),
        'oauth_refresh_token': Column('oauth_refresh_token', String(1024)),
        'oauth_token_expiry': Column('oauth_token_expiry', DateTime)
    }
    
    # Add missing columns
    existing_columns = [c.name for c in settings.columns]
    added_columns = []
    
    with engine.begin() as conn:
        for column_name, column_def in columns_to_add.items():
            if column_name not in existing_columns:
                print(f"Adding column {column_name} to settings table")
                conn.execute(f'ALTER TABLE settings ADD COLUMN {column_name} {column_def.type}')
                added_columns.append(column_name)
    
    if not added_columns:
        print("All columns already exist in settings table")
    else:
        print(f"Added {len(added_columns)} columns to settings table: {', '.join(added_columns)}")

if __name__ == "__main__":
    run_migration()
