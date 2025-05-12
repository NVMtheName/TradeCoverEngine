# Fixing Heroku Deployment Issues

## The Problem

Heroku is having trouble deploying your application due to missing package manager files. The error message shows:

```
Error: Couldn't find any supported Python package manager files.
```

Heroku is looking for one of these files in the root directory:
- `requirements.txt`
- `Pipfile`
- `poetry.lock`

While your repo has a `requirements.txt` file, it seems Heroku isn't detecting it, most likely because:
1. It might be listed in `.gitignore` or `.slugignore`
2. It might not have been properly added to your Git repository
3. There might be case sensitivity issues

## The Solution

### 1. Check Your .gitignore File

First, make sure `requirements.txt` isn't listed in your `.gitignore` file:

```bash
grep -i requirements .gitignore
```

### 2. Ensure requirements.txt is in Git

```bash
git check-ignore requirements.txt
```

If no output, then the file isn't being ignored.

### 3. Add requirements.txt to Git

```bash
git add requirements.txt
git commit -m "Add requirements.txt for Heroku deployment"
git push heroku main
```

### 4. Verify Python Version

Make sure your `runtime.txt` contains a valid Python version that Heroku supports:

```
python-3.10.12
```

Replace with a supported version from: https://devcenter.heroku.com/articles/python-support#supported-runtimes

### 5. Alternative: Create requirements-heroku.txt

If you want to keep using uv in development but Heroku doesn't support it, create a special file for Heroku:

```bash
cp requirements.txt requirements-heroku.txt
```

Then update your Procfile to use this file:

```
web: pip install -r requirements-heroku.txt && gunicorn --workers=2 --bind 0.0.0.0:$PORT --timeout 60 main:app
```

### 6. Last Resort: Use Buildpacks Explicitly

If all else fails, explicitly specify the Python buildpack:

```bash
heroku buildpacks:set heroku/python
```

## Additional Heroku Deployment Tips

1. **Environment Variables**: Make sure all required environment variables are set:

```bash
heroku config:set DATABASE_URL=postgres://...
heroku config:set FLASK_SECRET_KEY=your_secret_key
```

2. **Database Migrations**: Run database migrations after deployment:

```bash
heroku run python migrate_db.py
```

3. **Check Logs**: If deployment succeeds but the app fails to start:

```bash
heroku logs --tail
```

4. **Procfile Settings**: Your optimized Procfile settings should help with performance:

```
web: gunicorn --workers=2 --bind 0.0.0.0:$PORT --timeout 60 main:app
release: python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

These changes ensure database tables are created automatically during deployment.