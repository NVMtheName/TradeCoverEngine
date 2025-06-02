#!/bin/bash

# Quick Heroku Connection Script for Existing GitHub Repository
# This script helps connect your existing GitHub repo to Heroku

echo "🔗 Connecting Existing GitHub Repository to Heroku"
echo "================================================="

# Get repository and app information
read -p "Enter your GitHub repository URL: " GITHUB_REPO
read -p "Enter your Heroku app name (or press Enter to create new): " HEROKU_APP

# Check if Heroku CLI is available
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI not found. Please install it first."
    echo "   Visit: https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Login check
if ! heroku auth:whoami &> /dev/null; then
    echo "🔐 Please log in to Heroku:"
    heroku login
fi

# Create Heroku app if needed
if [ -z "$HEROKU_APP" ]; then
    echo "📱 Creating new Heroku app..."
    heroku create
    HEROKU_APP=$(heroku apps:info --json | python3 -c "import sys, json; print(json.load(sys.stdin)['name'])")
    echo "✅ Created app: $HEROKU_APP"
else
    echo "📱 Using existing app: $HEROKU_APP"
fi

# Add PostgreSQL if not exists
echo "🗄️  Setting up database..."
heroku addons:create heroku-postgresql:essential-0 --app $HEROKU_APP 2>/dev/null || echo "Database addon already exists"

# Set basic configuration
echo "⚙️  Setting basic configuration..."
heroku config:set FLASK_ENV=production --app $HEROKU_APP
heroku config:set REPLIT_DEV_DOMAIN="$HEROKU_APP.herokuapp.com" --app $HEROKU_APP

# Generate session secret if not set
if ! heroku config:get SESSION_SECRET --app $HEROKU_APP &> /dev/null; then
    SESSION_SECRET=$(openssl rand -base64 32)
    heroku config:set SESSION_SECRET="$SESSION_SECRET" --app $HEROKU_APP
fi

# API credentials setup
echo ""
echo "🔑 API Credentials Setup"
echo "Please provide your API credentials:"

read -p "OpenAI API Key: " OPENAI_KEY
if [ ! -z "$OPENAI_KEY" ]; then
    heroku config:set OPENAI_API_KEY="$OPENAI_KEY" --app $HEROKU_APP
fi

read -p "Schwab API Key (Client ID): " SCHWAB_KEY
if [ ! -z "$SCHWAB_KEY" ]; then
    heroku config:set SCHWAB_API_KEY="$SCHWAB_KEY" --app $HEROKU_APP
fi

read -p "Schwab API Secret: " SCHWAB_SECRET
if [ ! -z "$SCHWAB_SECRET" ]; then
    heroku config:set SCHWAB_API_SECRET="$SCHWAB_SECRET" --app $HEROKU_APP
fi

# Add Heroku remote if not exists
echo "🔗 Adding Heroku remote..."
heroku git:remote -a $HEROKU_APP 2>/dev/null || echo "Heroku remote already exists"

echo ""
echo "✅ Setup Complete!"
echo ""
echo "📋 Next Steps for GitHub Integration:"
echo "1. Go to: https://dashboard.heroku.com/apps/$HEROKU_APP"
echo "2. Navigate to Deploy tab"
echo "3. Connect to GitHub and select your repository"
echo "4. Enable automatic deployments"
echo ""
echo "🔍 GitHub Secrets needed (Settings > Secrets > Actions):"
echo "   HEROKU_API_KEY=$(heroku auth:token)"
echo "   HEROKU_APP_NAME=$HEROKU_APP"
echo "   HEROKU_EMAIL=$(heroku auth:whoami)"
echo "   HEROKU_APP_URL=https://$HEROKU_APP.herokuapp.com"
echo ""
echo "🚀 Your app: https://$HEROKU_APP.herokuapp.com"
echo "📊 Logs: heroku logs --tail --app $HEROKU_APP"