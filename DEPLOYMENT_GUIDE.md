# Detailed Deployment Guide

## Pre-Deployment Checklist
- [ ] Domain name configured
- [ ] SSL certificate ready
- [ ] Database server prepared
- [ ] API keys obtained
- [ ] Environment variables configured

## Step-by-Step Heroku Deployment

### 1. Prepare Your Local Environment
```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login to Heroku
heroku login

# Clone or download the application
cd arbion-production-package
```

### 2. Create Heroku Application
```bash
# Create new app (replace 'your-app-name' with desired name)
heroku create your-app-name

# Add PostgreSQL database
heroku addons:create heroku-postgresql:mini

# Verify database URL is set
heroku config:get DATABASE_URL
```

### 3. Configure Environment Variables
```bash
# Set session secret
heroku config:set SESSION_SECRET="your-very-secure-random-string"

# Set Schwab API credentials
heroku config:set SCHWAB_API_KEY="your-schwab-client-id"
heroku config:set SCHWAB_API_SECRET="your-schwab-client-secret"

# Optional: Set OpenAI API key for AI features
heroku config:set OPENAI_API_KEY="your-openai-api-key"

# Set production environment
heroku config:set FLASK_ENV="production"
```

### 4. Deploy Application
```bash
# Initialize git repository
git init
git add .
git commit -m "Initial deployment"

# Add Heroku remote
heroku git:remote -a your-app-name

# Deploy to Heroku
git push heroku main
```

### 5. Initialize Database
```bash
# Create database tables
heroku run python -c "from app import db; db.create_all()"

# Create admin user (optional - will be created automatically)
heroku run python -c "
from app import db
from models import User
admin = User(username='admin', email='admin@example.com')
admin.set_password('admin123')
db.session.add(admin)
db.session.commit()
print('Admin user created')
"
```

### 6. Configure Custom Domain (Optional)
```bash
# Add custom domain
heroku domains:add your-domain.com

# Configure DNS CNAME record pointing to your-app-name.herokuapp.com
```

## Manual Server Deployment

### System Requirements
- Ubuntu 20.04+ or CentOS 8+
- Python 3.11+
- PostgreSQL 12+
- Nginx (recommended)
- SSL certificate

### Installation Steps
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and PostgreSQL
sudo apt install python3.11 python3.11-pip postgresql postgresql-contrib nginx -y

# Create database
sudo -u postgres createdb arbion_production

# Create application directory
sudo mkdir /var/www/arbion
sudo chown $USER:$USER /var/www/arbion
cd /var/www/arbion

# Extract application files
unzip arbion_production_package.zip
cd arbion_production_package

# Install Python dependencies
pip3.11 install -r requirements.txt

# Configure environment variables
cp .env.template .env
# Edit .env with your configuration

# Start application
gunicorn --bind 0.0.0.0:5000 --workers 3 main:app
```

## Troubleshooting

### Common Issues
1. **Database Connection Error**
   - Verify DATABASE_URL format
   - Check database server accessibility
   - Ensure PostgreSQL is running

2. **Template Not Found Error**
   - Verify all template files are uploaded
   - Check file permissions

3. **API Authentication Errors**
   - Verify API keys are correctly set
   - Check Schwab OAuth callback URL

4. **Performance Issues**
   - Increase Gunicorn workers
   - Enable database connection pooling
   - Configure Redis for session storage

### Getting Help
- Check application logs: `heroku logs --tail`
- Monitor server resources
- Review error messages in browser console
