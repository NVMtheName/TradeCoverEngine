# Fix for Heroku Deployment Failure

I see you're getting the error "Couldn't find any supported Python package manager files" from Heroku. This is because Replit won't let us directly create a `requirements.txt` file using the editor.

## Here's how to fix it:

1. **Download all your project files** from Replit as a zip (use the three dots menu in the files sidebar)

2. **Rename the file** `requirements-heroku.txt` to `requirements.txt` in your local copy

3. **Upload to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/schwab-trading-bot.git
   git push -u origin main
   ```

4. **Deploy to Heroku** (using either method):

   ### Method 1: Heroku CLI
   ```bash
   heroku create schwab-trading-bot
   heroku git:remote -a schwab-trading-bot
   git push heroku main
   ```

   ### Method 2: Heroku Dashboard
   - Go to https://dashboard.heroku.com/apps
   - Click "New" → "Create new app"
   - Follow the GitHub connection instructions
   
5. **Add the required add-ons**:
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   heroku addons:create quotaguardstatic:starter
   ```

6. **Set up environment variables**:
   ```bash
   heroku config:set SCHWAB_API_KEY=kLgjtAjFRFsdGjm3ZUuGTWPEHmVtwQoX
   heroku config:set SCHWAB_API_SECRET=tTNTKFos4LKybsiG
   heroku config:set SECRET_KEY=$(openssl rand -hex 32)
   heroku config:set OPENAI_API_KEY=your_openai_api_key_if_you_have_one
   ```

7. **Initialize the database**:
   ```bash
   heroku run python -c "from app import app, db; with app.app_context(): db.create_all()"
   ```

## For Static IP Whitelisting with Schwab API:

1. **Find your assigned static IP**:
   ```bash
   heroku config | grep QUOTAGUARDSTATIC_URL
   ```

2. **The IP address** will be in the URL shown (e.g., if URL is `quotaguardstatic://username:password@12.34.56.78:9292` then IP is `12.34.56.78`)

3. **Contact Schwab API support** to whitelist this IP