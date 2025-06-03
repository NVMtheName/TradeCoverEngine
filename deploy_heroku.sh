#!/bin/bash
# Heroku Deployment Script for Arbion Trading Platform

set -e

echo "🚀 Starting Heroku deployment for Arbion Trading Platform..."

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI not found. Please install it first:"
    echo "curl https://cli-assets.heroku.com/install.sh | sh"
    exit 1
fi

# Get app name from user
read -p "Enter your Heroku app name: " APP_NAME

if [ -z "$APP_NAME" ]; then
    echo "❌ App name is required"
    exit 1
fi

echo "Creating Heroku app: $APP_NAME"

# Create Heroku app
heroku create $APP_NAME

# Add PostgreSQL addon
echo "Adding PostgreSQL database..."
heroku addons:create heroku-postgresql:mini -a $APP_NAME

# Set environment variables
echo "Setting environment variables..."
heroku config:set FLASK_ENV=production -a $APP_NAME

read -p "Enter your Schwab API Key (Client ID): " SCHWAB_KEY
heroku config:set SCHWAB_API_KEY="$SCHWAB_KEY" -a $APP_NAME

read -p "Enter your Schwab API Secret (Client Secret): " SCHWAB_SECRET
heroku config:set SCHWAB_API_SECRET="$SCHWAB_SECRET" -a $APP_NAME

read -p "Enter a secure session secret: " SESSION_SECRET
heroku config:set SESSION_SECRET="$SESSION_SECRET" -a $APP_NAME

# Optional OpenAI API key
read -p "Enter OpenAI API Key (optional, press Enter to skip): " OPENAI_KEY
if [ ! -z "$OPENAI_KEY" ]; then
    heroku config:set OPENAI_API_KEY="$OPENAI_KEY" -a $APP_NAME
fi

# Initialize git and deploy
echo "Deploying application..."
git init
git add .
git commit -m "Initial deployment of Arbion Trading Platform"
heroku git:remote -a $APP_NAME
git push heroku main

# Initialize database
echo "Initializing database..."
heroku run python -c "from app import db; db.create_all()" -a $APP_NAME

echo "✅ Deployment complete!"
echo "🌐 Your app is available at: https://$APP_NAME.herokuapp.com"
echo "👤 Default admin login: admin / admin123"
echo "⚠️  Remember to change the admin password after first login!"
