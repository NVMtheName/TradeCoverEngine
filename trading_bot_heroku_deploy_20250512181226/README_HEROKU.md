# Trading Bot - GitHub to Heroku Deployment

This package contains a ready-to-deploy version of the Trading Bot application for Heroku.

## SUPER EASY GITHUB DEPLOYMENT (EASIEST OPTION)

1. **Create a Heroku Account**:
   Go to https://signup.heroku.com/ and create a free account

2. **Create a GitHub Account**:
   Go to https://github.com/join if you don't already have one

3. **Deploy from GitHub**:

   a. Upload this entire folder to a GitHub repository:
      - Create a new repository on GitHub
      - Upload all these files (drag and drop in the GitHub web interface)
   
   b. Connect to Heroku:
      - Go to https://dashboard.heroku.com/
      - Click "New" and "Create new app"
      - Give your app a name and click "Create app"
      
   c. Connect to GitHub:
      - In your Heroku app, go to the "Deploy" tab
      - Select "GitHub" in the "Deployment method" section
      - Connect your GitHub account
      - Search for and select your repository
      
   d. Set up automatic deploys:
      - Scroll down to "Automatic deploys"
      - Click "Enable Automatic Deploys"
      
   e. Perform manual deploy:
      - Scroll to "Manual deploy"
      - Click "Deploy Branch"

   f. Set up database:
      - Go to "Resources" tab
      - Click "Find more add-ons"
      - Find "Heroku Postgres" and select "Mini" plan
      - Click "Submit Order Form"

   g. Initialize database:
      - Go to "More" button (top right) and select "Run console"
      - Type `python migrate_db.py` and click "Run"

4. **Set up API Keys**:
   - Go to "Settings" tab
   - Click "Reveal Config Vars"
   - Add your API keys:
     - Key: `SCHWAB_API_KEY` / Value: your_key_here
     - Key: `SCHWAB_API_SECRET` / Value: your_secret_here
     - Key: `OPENAI_API_KEY` / Value: your_openai_key_here

5. **Open Your App**:
   - Click "Open app" button at the top right

That's it! No command line, no scripts, just click-and-deploy!

## ULTRA-EASY ONE-CLICK DEPLOYMENT

If your GitHub repository is already set up, you can use the "Deploy to Heroku" button below to deploy with a single click:

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

This button will:
1. Create a new Heroku app
2. Set up the required buildpacks
3. Create a PostgreSQL database
4. Initialize the database
5. Prompt you for API keys
6. Deploy your application

## Troubleshooting

- **Application errors**:
  Go to "More" button, select "View logs"

- **Need to update your app**?
  Just make changes on GitHub and they will deploy automatically!
  
## Additional Resources

- Heroku Python Support: https://devcenter.heroku.com/articles/python-support
- Heroku PostgreSQL: https://devcenter.heroku.com/articles/heroku-postgresql
