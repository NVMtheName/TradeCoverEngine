from app import app, db
from models import User, Settings, Trade, WatchlistItem
import os

# Print database URL (with password masked)
db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
if "://" in db_url:
    masked_url = db_url.split("://")[0] + "://"
    if "@" in db_url:
        auth = db_url.split("://")[1].split("@")[0]
        if ":" in auth:
            username = auth.split(":")[0]
            masked_url += username + ":****@"
        else:
            masked_url += auth + "@"
    masked_url += db_url.split("@")[-1]
    print(f"Using database: {masked_url}")
else:
    print(f"Using database: {db_url}")

# Create all tables
with app.app_context():
    # Create database tables
    db.create_all()
    print("Database tables created successfully")
    
    # Check if we have any users
    user_count = User.query.count()
    print(f"Found {user_count} users in the database")
    
    # Check if we have any settings
    settings_count = Settings.query.count()
    print(f"Found {settings_count} settings records in the database")
