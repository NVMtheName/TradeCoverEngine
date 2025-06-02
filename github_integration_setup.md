# Heroku GitHub Integration for Arbion Trading Platform

This guide implements automatic deployment from GitHub to Heroku for your Arbion platform.

## Prerequisites

1. GitHub repository with your Arbion code
2. Heroku account and application created
3. GitHub account connected to Heroku

## Step 1: Prepare GitHub Repository

### Create GitHub Repository
1. Go to https://github.com/new
2. Name your repository: `arbion-trading-platform`
3. Make it private for security (recommended for trading apps)
4. Initialize with README

### Push Your Code to GitHub
```bash
# Initialize git repository (if not already done)
git init
git branch -M main

# Add GitHub remote (replace with your repository URL)
git remote add origin https://github.com/yourusername/arbion-trading-platform.git

# Add all files
git add .

# Commit changes
git commit -m "Initial commit: Arbion trading platform with Heroku deployment"

# Push to GitHub
git push -u origin main
```

## Step 2: Connect GitHub to Heroku

### Via Heroku Dashboard
1. Go to https://dashboard.heroku.com/apps
2. Select your Arbion app
3. Go to the "Deploy" tab
4. In "Deployment method" section, click "GitHub"
5. Click "Connect to GitHub"
6. Authorize Heroku to access your GitHub account
7. Search for your repository name: `arbion-trading-platform`
8. Click "Connect"

### Via Heroku CLI (Alternative)
```bash
# Connect GitHub integration
heroku labs:enable github-integration
heroku git:remote -a your-app-name
```

## Step 3: Configure Automatic Deployments

### Enable Automatic Deployments
1. In the Heroku dashboard, under "Automatic deploys"
2. Select the branch to deploy from (usually `main`)
3. Check "Wait for CI to pass before deploy" (recommended)
4. Click "Enable Automatic Deploys"

### Manual Deploy Option
For immediate deployment:
1. In "Manual deploy" section
2. Select branch: `main`
3. Click "Deploy Branch"

## Step 4: Configure GitHub Actions (Optional)

Create `.github/workflows/heroku-deploy.yml`:

```yaml
name: Deploy to Heroku

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        
    - name: Run tests
      run: |
        python -m pytest tests/ -v
        
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to Heroku
      uses: akhileshns/heroku-deploy@v3.12.12
      with:
        heroku_api_key: ${{secrets.HEROKU_API_KEY}}
        heroku_app_name: "your-arbion-app-name"
        heroku_email: "your-email@example.com"
```

## Step 5: Environment Variables Security

### Heroku Config Vars
Set these in Heroku dashboard under "Settings" > "Config Vars":

```bash
# Required API Keys
OPENAI_API_KEY=your_openai_api_key
SCHWAB_API_KEY=your_schwab_client_id
SCHWAB_API_SECRET=your_schwab_client_secret

# Flask Configuration
FLASK_ENV=production
SESSION_SECRET=auto_generated_by_heroku

# Domain Configuration
REPLIT_DEV_DOMAIN=your-app-name.herokuapp.com
```

### GitHub Secrets (for Actions)
If using GitHub Actions, add these secrets in GitHub:
1. Go to your repository
2. Settings > Secrets and variables > Actions
3. Add repository secrets:
   - `HEROKU_API_KEY`: Your Heroku API key
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `SCHWAB_API_KEY`: Your Schwab client ID
   - `SCHWAB_API_SECRET`: Your Schwab client secret

## Step 6: Branch Protection (Recommended)

### Protect Main Branch
1. Go to GitHub repository settings
2. Branches > Add rule
3. Branch name pattern: `main`
4. Enable:
   - Require pull request reviews
   - Require status checks to pass
   - Require branches to be up to date

## Step 7: Review Apps (Optional)

Enable review apps for pull requests:
1. In Heroku dashboard, go to "Deploy" tab
2. Scroll to "Review Apps" section
3. Click "Enable Review Apps"
4. Configure settings:
   - Create new review apps for new pull requests
   - Destroy stale review apps automatically

## Deployment Workflow

### Development Workflow
1. Create feature branch: `git checkout -b feature/new-feature`
2. Make changes and commit: `git commit -m "Add new feature"`
3. Push to GitHub: `git push origin feature/new-feature`
4. Create pull request on GitHub
5. Review app automatically created (if enabled)
6. After review, merge to main
7. Automatic deployment to production

### Monitoring Deployments
```bash
# View deployment activity
heroku releases

# View build logs
heroku builds

# Monitor application logs
heroku logs --tail
```

## Benefits of GitHub Integration

1. **Automatic Deployments**: Every push to main triggers deployment
2. **Review Apps**: Test features in isolated environments
3. **Rollback Capability**: Easy rollback to previous versions
4. **CI/CD Pipeline**: Automated testing before deployment
5. **Team Collaboration**: Code review process integration

## Troubleshooting

### Common Issues
- **Build failures**: Check build logs in Heroku dashboard
- **Environment variables**: Ensure all required config vars are set
- **Database migrations**: May need manual trigger after deployment

### Debug Commands
```bash
# Check deployment status
heroku ps

# View recent deployments
heroku releases

# Manual deployment
heroku builds:create

# Restart application
heroku restart
```

Your Arbion platform is now configured for seamless GitHub integration with Heroku!