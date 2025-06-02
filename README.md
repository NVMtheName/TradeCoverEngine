# Arbion Trading Platform

AI-powered trading platform with advanced market analysis and automated trading strategies.

## Features

- **AI-Powered Analysis**: OpenAI integration for market insights and trading recommendations
- **Multi-Provider Support**: Seamless integration with Charles Schwab API
- **Automated Trading**: Intelligent covered call strategies with risk management
- **User Management**: Secure authentication with multi-level access controls
- **Real-time Monitoring**: Live market data and portfolio tracking
- **Mobile Responsive**: Modern Bootstrap-based interface

## Technology Stack

- **Backend**: Python 3.11, Flask, SQLAlchemy
- **Database**: PostgreSQL with connection pooling
- **Frontend**: Bootstrap 5, responsive design
- **APIs**: OpenAI GPT-4, Charles Schwab API
- **Deployment**: Heroku with GitHub integration
- **CI/CD**: GitHub Actions with automated testing

## Quick Start

### Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables (see Configuration section)
4. Run: `python app.py`

### Heroku Deployment

#### Option 1: GitHub Integration (Recommended)
1. Follow the guide in `github_integration_setup.md`
2. Run: `./setup_github_integration.sh`
3. Connect repository in Heroku dashboard

#### Option 2: Direct Deployment
1. Install Heroku CLI
2. Run: `./deploy_to_heroku.sh`
3. Follow the automated setup process

## Configuration

### Required Environment Variables

```bash
# API Keys
OPENAI_API_KEY=your_openai_api_key
SCHWAB_API_KEY=your_schwab_client_id
SCHWAB_API_SECRET=your_schwab_client_secret

# Flask Configuration
FLASK_ENV=production
SESSION_SECRET=auto_generated_secure_key

# Database
DATABASE_URL=postgresql://... (auto-configured on Heroku)
```

### Optional Configuration

```bash
# OAuth Integration
GOOGLE_OAUTH_CLIENT_ID=your_google_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_google_client_secret

# Performance Tuning
WEB_CONCURRENCY=2
DB_POOL_SIZE=10
```

## API Integration Setup

### OpenAI API
1. Create account at https://platform.openai.com/
2. Generate API key in API section
3. Set as `OPENAI_API_KEY` environment variable

### Charles Schwab API
1. Register at https://developer.schwab.com/
2. Create application and get Client ID/Secret
3. Set as `SCHWAB_API_KEY` and `SCHWAB_API_SECRET`

## Admin Access

A secure admin account is automatically created:
- Username: `arbion_master`
- Access all platform features and user management

## Architecture

- **12-Factor App Methodology**: Environment-based configuration
- **Health Monitoring**: `/health` and `/metrics` endpoints
- **Security**: HTTPS enforcement, secure session management
- **Scalability**: Connection pooling, worker optimization
- **Monitoring**: Comprehensive logging and error tracking

## Development Workflow

1. Create feature branch: `git checkout -b feature/new-feature`
2. Make changes and test locally
3. Push to GitHub: `git push origin feature/new-feature`
4. Create pull request
5. Automated testing runs via GitHub Actions
6. Deploy to production on merge to main

## Monitoring and Logs

```bash
# View application logs
heroku logs --tail

# Check application status
heroku ps

# Monitor database
heroku pg:info
```

## Security

- Environment-based secrets management
- HTTPS-only in production
- Secure OAuth implementation
- Database connection encryption
- Regular dependency updates via GitHub Actions

## Support

For deployment issues or API integration questions, refer to:
- `github_integration_setup.md` - GitHub deployment guide
- `heroku_deployment_checklist.md` - Production deployment checklist
- `DEPLOY_TO_HEROKU.md` - Step-by-step deployment instructions

## License

Proprietary trading platform for authorized users only.