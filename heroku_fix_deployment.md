# Fix for Heroku Deployment Issues

## The Problem

Heroku requires a `requirements.txt` file in the root directory of your project to detect and deploy Python applications properly. Without this file, Heroku will fail to build your app with the error:

```
Error: Couldn't find any supported Python package manager files.
```

## The Solution

I've created a simple script to fix this issue. Before pushing to GitHub or deploying to Heroku, run:

```
python fix_heroku_deploy.py
```

This script:
1. Creates a proper `requirements.txt` file in the project root
2. Adds a `runtime.txt` file to specify Python 3.11
3. Ensures a `Procfile` exists for proper web process configuration

## Deployment Steps

1. Run the fix script:
   ```
   python fix_heroku_deploy.py
   ```
   
2. Upload to GitHub:
   - Create a repository at github.com
   - Upload all files using drag & drop in your browser
   - Make sure to include the requirements.txt, runtime.txt and Procfile files
   
3. Connect to Heroku:
   - Create a new app in the Heroku dashboard
   - Go to the "Deploy" tab
   - Select "GitHub" as the deployment method
   - Connect to your GitHub repository
   - Enable automatic deploys
   - Perform a manual deploy

4. Add a database:
   - Go to "Resources" tab
   - Add "Heroku Postgres" (mini plan)
   
5. Initialize database:
   - Go to "More" → "Run console"
   - Run: `python migrate_db.py`
   
6. Set up API Keys:
   - Go to "Settings" → "Config Vars"
   - Add your API keys (SCHWAB_API_KEY, etc.)

## Checklist for Successful Deployment

Ensure the following files are in your repository root directory:
- [x] requirements.txt
- [x] runtime.txt
- [x] Procfile
- [x] app.json (for Heroku button)

These files should NOT be in .gitignore and must be committed to GitHub.