# Heroku Production Deployment Guide

## Heroku Connect CLI Setup

Your Arbion trading platform is now configured with Heroku Connect CLI integration for proper production callback URLs.

### Step 1: Deploy to Heroku

```bash
# Create new Heroku app
heroku create your-app-name

# Add required addons
heroku addons:create heroku-postgresql:essential-0
heroku addons:create heroku-redis:mini
heroku addons:create papertrail:choklad
heroku addons:create herokuconnect:demo

# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set HEROKU_APP_NAME=your-app-name
heroku config:set OPENAI_API_KEY=your_openai_key
heroku config:set SCHWAB_API_KEY=your_schwab_client_id
heroku config:set SCHWAB_API_SECRET=your_schwab_client_secret

# Deploy
git push heroku main
```

### Step 2: Configure Schwab Developer Portal

Add these URLs to your Schwab developer application:

**OAuth Redirect URI:**
```
https://your-app-name.herokuapp.com/oauth/callback
```

**Allowed Origins:**
```
https://your-app-name.herokuapp.com
```

### Step 3: Verify Production Setup

```bash
# Check app status
heroku ps

# View logs
heroku logs --tail

# Test health endpoint
curl https://your-app-name.herokuapp.com/health

# Run callback URL generation
heroku run python bin/heroku_callback_setup.py
```

### Step 4: Production Monitoring

Your app includes comprehensive monitoring:

- **Health Checks**: `/health` endpoint for Heroku monitoring
- **Application Metrics**: `/metrics` for performance tracking
- **Structured Logging**: JSON format for log aggregation
- **Error Tracking**: Automatic error reporting

### Step 5: SSL and Security

All production features are enabled:
- HTTPS enforcement
- Security headers (CSP, HSTS, XSS protection)
- Secure session management
- CSRF protection

Your platform is now production-ready with proper Heroku Connect CLI integration.