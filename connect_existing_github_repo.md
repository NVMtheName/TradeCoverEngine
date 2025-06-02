# Connect Your Existing GitHub Repository to Heroku

## Step 1: Update Your Repository with Deployment Files

Push the following files to your existing GitHub repository:

```bash
# Add the new deployment configuration files
git add .
git commit -m "Add Heroku deployment configuration and GitHub Actions"
git push origin main
```

## Step 2: Create Heroku Application

If you haven't created a Heroku app yet:

```bash
heroku create your-arbion-app-name
heroku addons:create heroku-postgresql:essential-0
```

## Step 3: Connect GitHub to Heroku Dashboard

1. Go to https://dashboard.heroku.com/apps/your-app-name
2. Navigate to the **Deploy** tab
3. In "Deployment method" section, click **GitHub**
4. Click "Connect to GitHub" and authorize if prompted
5. Search for your repository name
6. Click **Connect** next to your repository

## Step 4: Set Up GitHub Secrets

In your GitHub repository settings:
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add these repository secrets:

```
HEROKU_API_KEY=your_heroku_api_key
HEROKU_APP_NAME=your-arbion-app-name
HEROKU_EMAIL=your-heroku-email
HEROKU_APP_URL=https://your-arbion-app-name.herokuapp.com
```

To get your Heroku API key:
```bash
heroku auth:token
```

## Step 5: Configure Heroku Environment Variables

Set these in Heroku dashboard under **Settings** → **Config Vars**:

```
FLASK_ENV=production
SESSION_SECRET=(will be auto-generated)
OPENAI_API_KEY=your_openai_key
SCHWAB_API_KEY=your_schwab_client_id
SCHWAB_API_SECRET=your_schwab_client_secret
REPLIT_DEV_DOMAIN=your-app-name.herokuapp.com
```

## Step 6: Enable Automatic Deployments

Back in Heroku dashboard **Deploy** tab:
1. In "Automatic deploys" section
2. Select branch: **main**
3. Check "Wait for CI to pass before deploy"
4. Click **Enable Automatic Deploys**

## Step 7: Test the Integration

Make a small change to trigger deployment:
```bash
echo "# Updated $(date)" >> README.md
git add README.md
git commit -m "Test automatic deployment"
git push origin main
```

Watch the deployment progress in:
- GitHub Actions tab for build/test status
- Heroku dashboard Activity tab for deployment status

Your Arbion platform will now automatically deploy when you push to the main branch!