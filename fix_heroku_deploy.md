# How to Fix Heroku Deployment Error

I've created several files to fix the deployment error you're seeing:

## 1. Added Test Directory and Basic Tests

The error in your screenshot shows that Heroku can't detect any runnable tests. I've created:

- `tests/test_basic.py` - A basic test file that verifies the app loads
- `pytest.ini` - Configuration for pytest

## 2. Updated Requirements

- Added `pytest==7.3.1` to `requirements-heroku.txt`
- **Important**: When you download the files, rename `requirements-heroku.txt` to `requirements.txt`

## 3. Added Heroku-specific Configuration Files

- `heroku.yml` - Container definition for Heroku (optional but helpful)
- `Procfile.windows` - For local testing on Windows

## Steps to Deploy Successfully:

1. **Download project files** from Replit (use the three dots in file explorer)

2. **Rename `requirements-heroku.txt` to `requirements.txt`**

3. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Fix Heroku deployment issues"
   git branch -M main
   git remote add origin https://github.com/yourusername/your-repo.git
   git push -u origin main
   ```

4. **Deploy to Heroku** (from your GitHub repo or using Heroku CLI)

5. **If you still get errors**, try these commands:
   ```bash
   # If using Heroku CLI
   heroku buildpacks:set heroku/python
   heroku config:set DISABLE_COLLECTSTATIC=1
   git push heroku main

   # Or if using GitHub deployment, set these in the Heroku dashboard
   # Settings → Config Vars → Add:
   # DISABLE_COLLECTSTATIC = 1
   ```

Let me know if you need help with any specific part of this process.