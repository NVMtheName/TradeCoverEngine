# Complete Heroku Deployment Guide for Trading Bot

This guide covers everything you need to deploy your trading bot to Heroku with a static IP for Schwab API access.

## Step 1: Required Files for Heroku

Create these files in your project root:

### Procfile
```
web: gunicorn main:app
```

### runtime.txt
```
python-3.9.13
```

### requirements.txt
Make sure it includes these packages:
```
flask==2.0.1
flask-login==0.5.0
flask-session==0.4.0
flask-sqlalchemy==3.0.3
flask-wtf==1.0.0
flask-migrate==3.1.0
gunicorn==20.1.0
matplotlib==3.5.1
numpy==1.22.3
pandas==1.4.2
psycopg2-binary==2.9.3
python-dateutil==2.8.2
requests==2.27.1
oauthlib==3.2.0
openai==0.27.0
werkzeug==2.0.3
wtforms==3.0.1
email-validator==1.1.3
trafilatura==1.4.0
sqlalchemy==1.4.46
python-dotenv==0.20.0
```

### proxies.py
This file is critical for the static IP connection to Schwab API:
```python
import os
import urllib.parse

def get_proxy_session():
    """Create a requests session configured to use the QuotaGuard Static proxy"""
    import requests
    
    session = requests.Session()
    
    # Check if QUOTAGUARDSTATIC_URL is set
    quotaguardstatic_url = os.environ.get('QUOTAGUARDSTATIC_URL')
    if quotaguardstatic_url:
        url = urllib.parse.urlparse(quotaguardstatic_url)
        
        # Configure proxy settings
        proxy_url = f"{url.scheme}://{url.netloc}"
        proxy_auth = f"{url.username}:{url.password}"
        
        session.proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # Add proxy authentication
        session.auth = (url.username, url.password)
        
    return session
```

## Step 2: Code Modifications for Heroku

### Update trading_bot/api_connector.py
Modify the Schwab connector initialization to use the proxy:

```python
# Find the _init_schwab method in trading_bot/api_connector.py
# and add this code near the beginning:

def _init_schwab(self):
    """Initialize Charles Schwab API settings."""
    # Import the specialized Schwab connector
    from trading_bot.schwab_connector import SchwabConnector, create_connector_from_settings
    
    # Initialize OAuth credentials
    self.client_id = self.api_key  # Schwab uses client_id/client_secret terminology
    self.client_secret = self.api_secret
    
    # Use proxy session if on Heroku
    if 'QUOTAGUARDSTATIC_URL' in os.environ:
        from proxies import get_proxy_session
        self.session = get_proxy_session()
        print("Using QuotaGuard Static proxy for Schwab API connections")
    
    # Continue with the rest of your code...
```

### Update Database Configuration in app.py
Add this to handle Heroku's PostgreSQL:

```python
# Database configuration with Heroku PostgreSQL support
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///instance/tradingbot.db")
# Fix for Heroku PostgreSQL URL format
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://", 1)
```

## Step 3: Set Up Heroku

### Install Heroku CLI
```bash
# On macOS
brew install heroku/brew/heroku

# On Windows
# Download installer from: https://devcenter.heroku.com/articles/heroku-cli

# On Ubuntu/Debian
curl https://cli-assets.heroku.com/install-ubuntu.sh | sh
```

### Login and Create App
```bash
# Login to Heroku
heroku login

# Create a new Heroku app 
heroku create schwab-trading-bot
```

### Add Required Add-ons
```bash
# Add PostgreSQL database
heroku addons:create heroku-postgresql:hobby-dev

# Add static IP for Schwab API whitelisting
heroku addons:create quotaguardstatic:starter
```

### Configure Environment Variables
```bash
# Set required environment variables
heroku config:set SCHWAB_API_KEY=kLgjtAjFRFsdGjm3ZUuGTWPEHmVtwQoX
heroku config:set SCHWAB_API_SECRET=tTNTKFos4LKybsiG
heroku config:set SECRET_KEY=$(openssl rand -hex 32)
heroku config:set OPENAI_API_KEY=your_openai_api_key_if_you_have_one

# Force HTTPS
heroku config:set FLASK_ENV=production
```

## Step 4: Deployment

### Initialize Git Repository (if needed)
```bash
git init
git add .
git commit -m "Prepare for Heroku deployment"
```

### Deploy to Heroku
```bash
# Deploy to Heroku
git push heroku main
```

### Initialize Database
```bash
# Create database tables
heroku run python -c "from app import app, db; with app.app_context(): db.create_all()"
```

### Scale the Dyno
```bash
# Start web dyno
heroku ps:scale web=1
```

## Step 5: Whitelist Your Static IP with Schwab

### Get Your Static IP
```bash
# Find your static IP from QuotaGuard
heroku config | grep QUOTAGUARDSTATIC_URL
```

The static IP will be in the URL. For example, if the URL is:
```
quotaguardstatic://username:password@qgp-123-456-789-101.us-east-1.quotaguard.com:9292
```
The IP to whitelist is `123.456.789.101`

### Contact Schwab for Whitelisting
Send an email to Schwab API Support with:

1. Your application name: `prod-nvm427gmailcom-d63839b5-7e1f-4b97-a656-8d24842f597d`
2. Your Schwab API key: `kLgjtAjFRFsdGjm3ZUuGTWPEHmVtwQoX`
3. The static IP address from QuotaGuard
4. A request to whitelist this IP for your application

### Update OAuth Callback URLs
In the Schwab Developer Portal, update your OAuth callback URLs to include:
```
https://schwab-trading-bot.herokuapp.com/oauth/callback
```

## Step 6: Monitoring and Management

### View Logs
```bash
# Monitor application logs
heroku logs --tail
```

### Automatic Restarts
Add the Heroku Scheduler for automatic daily restarts:
```bash
heroku addons:create scheduler:standard
```

Then configure a daily job with the command:
```bash
heroku ps:restart
```

### Connect to PostgreSQL Database
```bash
# Connect to the database
heroku pg:psql

# View database tables
\dt
```

## Additional Heroku Tips

### Upgrading Your Plan
For production use, consider:
- Upgrading from Hobby to Standard 1X dyno ($25/month) for better performance
- Upgrading from Hobby PostgreSQL to Standard 0 ($50/month) for more rows and better performance
- Upgrading QuotaGuard Static to a higher plan if you need more bandwidth

### Custom Domain
Set up a custom domain:
```bash
heroku domains:add www.yourdomain.com
```

Follow the DNS instructions Heroku provides to point your domain to the app.

### Auto-Deploy from GitHub
1. In the Heroku Dashboard, go to your app
2. Click the "Deploy" tab
3. Connect to your GitHub repository
4. Enable "Automatic deploys" from main branch

## Troubleshooting

### Connection Issues to Schwab API
If you're still having connection issues after whitelisting:
1. Check the logs: `heroku logs --tail`
2. Verify the proxy is working: Add logging to the proxies.py file
3. Check your environment variables: `heroku config`
4. Check QuotaGuard status: `heroku addons:open quotaguardstatic`

### Database Issues
Reset the database if needed:
```bash
heroku pg:reset DATABASE
heroku run python -c "from app import app, db; with app.app_context(): db.create_all()"
```