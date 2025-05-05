from app import app, db
import os

# Print database URL
db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
print(f"Current database: {db_url.split('@')[0].split('://')[0]}://*****@{db_url.split('@')[-1] if '@' in db_url else db_url.split('://')[-1]}")

# Get the DATABASE_URL from environment
env_db_url = os.environ.get("DATABASE_URL", "")
if env_db_url:
    # Convert postgres:// to postgresql://
    if env_db_url.startswith('postgres://'):
        env_db_url = env_db_url.replace('postgres://', 'postgresql://', 1)
        
    print(f"Environment DATABASE_URL: {env_db_url.split('@')[0].split('://')[0]}://*****@{env_db_url.split('@')[-1] if '@' in env_db_url else env_db_url.split('://')[-1]}")
else:
    print("No DATABASE_URL found in environment variables")

