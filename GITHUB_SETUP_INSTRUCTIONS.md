# GitHub Repository Setup for Arbion Trading Platform

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `arbion-trading-platform`
3. Description: `AI-powered trading platform with automated strategies`
4. Set to **Private** (recommended for trading applications)
5. Initialize with README: **No** (we have our own)
6. Click "Create repository"

## Step 2: Connect Local Repository to GitHub

Open terminal in your project directory and run:

```bash
# Set the main branch
git branch -M main

# Add GitHub remote (replace with your actual repository URL)
git remote add origin https://github.com/YOUR_USERNAME/arbion-trading-platform.git

# Verify remote
git remote -v
```

## Step 3: Push Code to GitHub

```bash
# Add all files
git add .

# Commit with descriptive message
git commit -m "Initial commit: Arbion trading platform with Heroku deployment"

# Push to GitHub
git push -u origin main
```

## Step 4: Set Up GitHub Secrets

Navigate to your repository on GitHub:
1. Go to **Settings** tab
2. Click **Secrets and variables** → **Actions**
3. Add the following repository secrets:

### Required Secrets
- `HEROKU_API_KEY`: Your Heroku API key
- `HEROKU_APP_NAME`: Your Heroku app name
- `HEROKU_EMAIL`: Your Heroku account email
- `HEROKU_APP_URL`: Your app URL (https://your-app-name.herokuapp.com)

### API Credentials
- `OPENAI_API_KEY`: Your OpenAI API key
- `SCHWAB_API_KEY`: Your Schwab client ID
- `SCHWAB_API_SECRET`: Your Schwab client secret

## Step 5: Create Heroku Application

Using Heroku CLI or dashboard:

```bash
# Login to Heroku
heroku login

# Create app
heroku create your-arbion-app-name

# Add PostgreSQL
heroku addons:create heroku-postgresql:essential-0

# Set basic config
heroku config:set FLASK_ENV=production
heroku config:set SESSION_SECRET=$(openssl rand -base64 32)
```

## Step 6: Connect GitHub to Heroku

### Via Heroku Dashboard:
1. Go to https://dashboard.heroku.com/apps/your-app-name
2. Navigate to **Deploy** tab
3. In "Deployment method", click **GitHub**
4. Click "Connect to GitHub" and authorize
5. Search for `arbion-trading-platform`
6. Click **Connect**

### Enable Automatic Deployments:
1. In "Automatic deploys" section
2. Select branch: `main`
3. Check "Wait for CI to pass before deploy"
4. Click **Enable Automatic Deploys**

## Step 7: Configure Environment Variables in Heroku

Set these in Heroku dashboard under Settings → Config Vars:

```
FLASK_ENV=production
SESSION_SECRET=(auto-generated)
OPENAI_API_KEY=your_openai_key
SCHWAB_API_KEY=your_schwab_client_id
SCHWAB_API_SECRET=your_schwab_client_secret
REPLIT_DEV_DOMAIN=your-app-name.herokuapp.com
```

## Step 8: Test Deployment

1. Make a small change to README.md
2. Commit and push:
   ```bash
   git add .
   git commit -m "Test automatic deployment"
   git push origin main
   ```
3. Watch deployment in Heroku dashboard Activity tab

## Development Workflow

### Creating Features:
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes
# ... edit files ...

# Commit changes
git add .
git commit -m "Add new feature description"

# Push feature branch
git push origin feature/new-feature
```

### Pull Request Process:
1. Create pull request on GitHub
2. GitHub Actions will run tests automatically
3. Review and merge to main
4. Automatic deployment to Heroku will trigger

## Monitoring and Logs

```bash
# View deployment logs
heroku logs --tail --app your-app-name

# Check app status
heroku ps --app your-app-name

# View recent deployments
heroku releases --app your-app-name
```

## Branch Protection (Recommended)

1. Go to repository **Settings** → **Branches**
2. Click **Add rule**
3. Branch name pattern: `main`
4. Enable:
   - Require pull request reviews
   - Require status checks to pass
   - Require branches to be up to date

Your Arbion platform is now configured for automatic GitHub to Heroku deployments!