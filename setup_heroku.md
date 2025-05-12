# Heroku Deployment Setup Guide

Based on the logs you shared, Heroku is having trouble finding your `requirements.txt` file in the repository. Let's fix this step by step.

## Problem

Heroku shows this error:
```
Error: Couldn't find any supported Python package manager files.
```

Even though you have `requirements.txt` and `requirements-heroku.txt` files, they're not being recognized by Heroku. This usually happens when:

1. The files aren't properly committed to Git
2. The files might be in `.gitignore`
3. You're deploying from a subdirectory

## Solution

### Step 1: Force Add Requirements to Git

```bash
# Make sure these files aren't being ignored
git rm --cached requirements.txt  # Remove from Git index if it exists
git rm --cached requirements-heroku.txt  # Remove from Git index if it exists

# Force add them even if they're in .gitignore
git add -f requirements.txt
git add -f requirements-heroku.txt

# Commit the changes
git commit -m "Force add requirements files for Heroku"
```

### Step 2: Update Procfile to Use Requirements-Heroku.txt First

The Procfile has already been updated to:
```
web: pip install -r requirements-heroku.txt && gunicorn --workers=2 --bind 0.0.0.0:$PORT --timeout 60 main:app
release: python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

This should work once the requirements files are properly committed.

### Step 3: Use Heroku CLI to Set Buildpack Explicitly

If the above steps don't work, you can explicitly set the Python buildpack:

```bash
heroku buildpacks:clear
heroku buildpacks:set heroku/python
```

### Step 4: Verify .python-version File

We've updated your `.python-version` file to use a supported Python version (3.10.12).

### Step 5: Check for .slugignore

Make sure you don't have a `.slugignore` file that might be excluding your requirements files.

### Step 6: Create a requirements.txt Symlink (Last Resort)

If all else fails, try this approach when deploying:

```bash
# Create a fresh copy of requirements.txt at deploy time
echo "flask>=2.2.0
Flask-Login>=0.6.0
Flask-Session>=0.4.0
Flask-SQLAlchemy>=3.0.3
Flask-WTF>=1.0.0
gunicorn>=20.1.0
matplotlib>=3.5.1
numpy>=1.22.3
pandas>=1.4.2
psycopg2-binary>=2.9.3
python-dateutil>=2.8.2
requests>=2.27.1
oauthlib>=3.2.0
openai>=0.27.0
werkzeug>=2.2.0
wtforms>=3.0.1
email-validator>=1.1.3
trafilatura>=1.4.0
sqlalchemy>=1.4.46
python-dotenv>=0.20.0
pytest>=7.3.1
pytest-tap>=3.5
sendgrid>=6.9.1
beautifulsoup4>=4.11.1" > requirements.txt

# Force commit it
git add -f requirements.txt
git commit -m "Add fresh requirements.txt for Heroku"
git push heroku main
```

## Verifying Deployment

Once deployed, check the logs to make sure everything is working:

```bash
heroku logs --tail
```

## Environment Variables

Make sure all necessary environment variables are set:

```bash
heroku config:set FLASK_ENV=production
heroku config:set FLASK_SECRET_KEY=your_secret_key
heroku config:set DATABASE_URL=your_postgresql_url
```

## Database Migration

After deployment, run migrations:

```bash
heroku run python migrate_db.py
```

This comprehensive approach should resolve the Heroku deployment issues you're experiencing.