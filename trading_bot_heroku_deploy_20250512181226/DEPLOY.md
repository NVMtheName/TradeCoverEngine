# Trading Bot Deployment - Easiest Options

## OPTION 1: ONE-CLICK DEPLOY

Just click the button below:

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

Follow the prompts to set up your app.

## OPTION 2: GITHUB + HEROKU

1. Upload this folder to GitHub:
   - Create a repository at github.com
   - Upload all files using drag & drop in your browser
   
2. Connect to Heroku:
   - Go to dashboard.heroku.com
   - Create a new app
   - Go to "Deploy" tab
   - Select "GitHub" and connect your repository
   - Click "Enable Automatic Deploys"
   - Click "Deploy Branch"
   
3. Add database:
   - Go to "Resources" tab
   - Add "Heroku Postgres" (mini plan)
   
4. Initialize database:
   - Go to "More" → "Run console"
   - Run: `python migrate_db.py`
   
5. Set up API Keys:
   - Go to "Settings" → "Config Vars"
   - Add your API keys (SCHWAB_API_KEY, etc.)
   
6. Click "Open app" button

That's it! No command line, no git commands!

For detailed instructions, see README_HEROKU.md
