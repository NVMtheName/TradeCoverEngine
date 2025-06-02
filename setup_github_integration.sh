#!/bin/bash

# GitHub Integration Setup Script for Arbion Trading Platform
# This script automates the GitHub integration with Heroku deployment

set -e

echo "🔗 Setting up GitHub Integration for Arbion"
echo "=========================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command_exists git; then
    echo "❌ Git is not installed. Please install Git first."
    exit 1
fi

if ! command_exists heroku; then
    echo "❌ Heroku CLI is not installed. Please install it first:"
    echo "   https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Check if logged into Heroku
if ! heroku auth:whoami &> /dev/null; then
    echo "🔐 Please log in to Heroku:"
    heroku login
fi

echo "✅ Prerequisites check complete"

# Get repository information
read -p "Enter your GitHub repository URL (e.g., https://github.com/username/arbion-trading-platform): " REPO_URL
read -p "Enter your Heroku app name: " APP_NAME

# Validate inputs
if [ -z "$REPO_URL" ] || [ -z "$APP_NAME" ]; then
    echo "❌ Repository URL and app name are required"
    exit 1
fi

# Initialize Git repository if needed
if [ ! -d ".git" ]; then
    echo "📦 Initializing Git repository..."
    git init
    git branch -M main
fi

# Add GitHub remote
echo "🔗 Configuring Git remote..."
if git remote get-url origin &> /dev/null; then
    echo "⚠️  Origin remote already exists. Updating..."
    git remote set-url origin "$REPO_URL"
else
    git remote add origin "$REPO_URL"
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "📝 Creating .gitignore..."
    cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
pip-log.txt
pip-delete-this-directory.txt
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/
*.mo
*.pot
*.log
local_settings.py
db.sqlite3
instance/
.webassets-cache
.scrapy
docs/_build/
target/
.ipynb_checkpoints
profile_default/
ipython_config.py
.python-version
Pipfile.lock
__pypackages__/
celerybeat-schedule
celerybeat.pid
*.sage.py
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/
.spyderproject
.spyproject
.ropeproject
/site
.mypy_cache/
.dmypy.json
dmypy.json
.pyre/
.replit
replit.nix
.upm/
.vscode/
.idea/
*.swp
*.swo
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
*.zip
backup_*
temp_*
trading_bot_export_*
heroku_deploy_*
secrets.txt
credentials.json
api_keys.txt
test_results/
flask_session/
EOF
fi

# Add and commit all files
echo "💾 Committing files to Git..."
git add .
git commit -m "Setup Arbion trading platform with GitHub integration" || echo "No changes to commit"

# Push to GitHub
echo "🚀 Pushing to GitHub..."
git push -u origin main

# Configure Heroku app for GitHub integration
echo "⚙️  Configuring Heroku app..."

# Add Heroku remote
heroku git:remote -a "$APP_NAME"

# Set up environment variables
echo "🔧 Setting up environment variables..."
echo "Please provide your API credentials:"

read -p "OpenAI API Key: " OPENAI_KEY
read -p "Schwab API Key (Client ID): " SCHWAB_KEY
read -p "Schwab API Secret: " SCHWAB_SECRET

# Set Heroku config vars
if [ ! -z "$OPENAI_KEY" ]; then
    heroku config:set OPENAI_API_KEY="$OPENAI_KEY" --app "$APP_NAME"
fi

if [ ! -z "$SCHWAB_KEY" ]; then
    heroku config:set SCHWAB_API_KEY="$SCHWAB_KEY" --app "$APP_NAME"
fi

if [ ! -z "$SCHWAB_SECRET" ]; then
    heroku config:set SCHWAB_API_SECRET="$SCHWAB_SECRET" --app "$APP_NAME"
fi

# Set additional config vars
heroku config:set FLASK_ENV=production --app "$APP_NAME"
heroku config:set REPLIT_DEV_DOMAIN="$APP_NAME.herokuapp.com" --app "$APP_NAME"

# Generate session secret if not set
if ! heroku config:get SESSION_SECRET --app "$APP_NAME" &> /dev/null; then
    SESSION_SECRET=$(openssl rand -base64 32)
    heroku config:set SESSION_SECRET="$SESSION_SECRET" --app "$APP_NAME"
fi

echo ""
echo "✅ GitHub integration setup complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Go to https://dashboard.heroku.com/apps/$APP_NAME"
echo "2. Navigate to the 'Deploy' tab"
echo "3. In 'Deployment method', click 'GitHub'"
echo "4. Connect to GitHub and select your repository"
echo "5. Enable 'Automatic deploys' from the main branch"
echo ""
echo "🔗 Repository: $REPO_URL"
echo "🚀 Heroku App: https://$APP_NAME.herokuapp.com"
echo ""
echo "📊 Monitor your deployment:"
echo "   heroku logs --tail --app $APP_NAME"
echo "   heroku ps --app $APP_NAME"