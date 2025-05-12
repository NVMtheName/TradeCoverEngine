#!/usr/bin/env python3
"""
Heroku One-Stop Deployment Package Creator

This script creates a complete, ready-to-deploy Heroku package with all necessary files.
The output is a ZIP file that can be:
1. Downloaded
2. Extracted
3. Deployed directly to Heroku without any additional configuration

Usage:
    python create_heroku_package.py

The script will:
1. Create a clean directory structure with only required files
2. Generate appropriate Heroku configuration files
3. Ensure all dependencies are properly listed
4. Create a ready-to-deploy ZIP package
"""

import os
import shutil
import zipfile
import datetime
import sys


# Files required for Heroku deployment
REQUIRED_FILES = [
    # Core application files
    'main.py',
    'app.py',
    'models.py',
    'forms.py',
    'config.py',
    'utils.py',
    'proxies.py',
    'schwab_proxy.py',
    
    # Templates and static files
    'templates',
    'static',
    
    # Trading bot modules
    'trading_bot',
    
    # Heroku configuration
    'Procfile',
    'heroku.yml',
    'app.ci',
    'heroku_test_runner.py',
    'run_tap_tests.py',
    
    # Database migrations
    'migrate_db.py',
    'migrate_settings.py',
    'migrate_ai_settings.py',
    
    # Tests
    'tests',
    
    # Dependencies
    'requirements.txt',
    'requirements-heroku.txt',
    'fixed_requirements.txt',
    
    # App-specific configuration and scripts
    'app.json',
    'pyproject.toml',
]

# Files to exclude even if they're in subdirectories of included directories
EXCLUDE_PATTERNS = [
    '__pycache__',
    '.pyc',
    '.git',
    '.github',
    '.pytest_cache',
    '.env',
    'venv',
    'env',
    '.DS_Store',
    'node_modules',
]

# Files that should not be excluded by .gitignore
FORCE_INCLUDE = [
    'requirements.txt',
    'requirements-heroku.txt',
    'requirements.txt',
    'Procfile',
    'runtime.txt',
    'app.json',
]

# Additional files to create or modify
ADDITIONAL_FILES = {
    'README_HEROKU.md': """# Trading Bot - GitHub to Heroku Deployment

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
""",

    'DEPLOY.md': """# Trading Bot Deployment - Easiest Options

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
""",

    'deploy_to_heroku.bat': """@echo off
echo ===================================
echo Trading Bot Heroku Deployment Script
echo ===================================
echo.

REM Check if Heroku CLI is installed
heroku --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Heroku CLI is not installed!
    echo Please install it from: https://devcenter.heroku.com/articles/heroku-cli
    echo After installing, run this script again.
    echo.
    pause
    exit /b 1
)

echo Checking Heroku login status...
heroku auth:whoami > nul 2>&1
if %errorlevel% neq 0 (
    echo Please log in to your Heroku account:
    heroku login
    if %errorlevel% neq 0 (
        echo Failed to log in to Heroku.
        pause
        exit /b 1
    )
)

echo.
echo === Step 1: Create Heroku App ===
set /p app_name=Enter your app name (leave blank for random name): 
if "%app_name%"=="" (
    echo Creating Heroku app with random name...
    heroku create
) else (
    echo Creating Heroku app with name: %app_name%...
    heroku create %app_name%
)
if %errorlevel% neq 0 (
    echo Failed to create Heroku app.
    pause
    exit /b 1
)

echo.
echo === Step 2: Add PostgreSQL Database ===
echo Adding PostgreSQL database...
heroku addons:create heroku-postgresql:mini
if %errorlevel% neq 0 (
    echo Failed to add PostgreSQL database.
    pause
    exit /b 1
)

echo.
echo === Step 3: Configure Environment ===
echo Setting environment variables...
heroku config:set FLASK_ENV=production

echo.
echo === Step 4: Initialize Git Repository ===
echo Initializing Git repository...
if exist .git (
    echo Git repository already exists.
) else (
    git init
    if %errorlevel% neq 0 (
        echo Failed to initialize Git repository.
        pause
        exit /b 1
    )
)

echo Adding files to Git...
git add .
git commit -m "Initial commit for Heroku deployment"
if %errorlevel% neq 0 (
    echo Failed to commit files to Git.
    pause
    exit /b 1
)

echo.
echo === Step 5: Deploy to Heroku ===
echo Deploying application to Heroku...
git push heroku main
if %errorlevel% neq 0 (
    echo Trying master branch instead...
    git push heroku master
    if %errorlevel% neq 0 (
        echo Failed to deploy to Heroku.
        pause
        exit /b 1
    )
)

echo.
echo === Step 6: Run Database Migrations ===
echo Running database migrations...
heroku run python migrate_db.py
if %errorlevel% neq 0 (
    echo Failed to run database migrations.
    pause
    exit /b 1
)

echo.
echo === Step 7: Open Application ===
echo Opening application in web browser...
heroku open
if %errorlevel% neq 0 (
    echo Failed to open application in browser.
    pause
    exit /b 1
)

echo.
echo ===================================
echo Deployment completed successfully!
echo ===================================
echo.
echo IMPORTANT: Don't forget to set your API keys:
echo heroku config:set SCHWAB_API_KEY=your_key_here
echo heroku config:set SCHWAB_API_SECRET=your_secret_here
echo heroku config:set OPENAI_API_KEY=your_openai_key_here
echo.
pause
""",

    'deploy_to_heroku.sh': """#!/bin/bash

echo "==================================="
echo "Trading Bot Heroku Deployment Script"
echo "==================================="
echo

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "Heroku CLI is not installed!"
    echo "Please install it from: https://devcenter.heroku.com/articles/heroku-cli"
    echo "After installing, run this script again."
    echo
    read -p "Press Enter to exit..."
    exit 1
fi

echo "Checking Heroku login status..."
if ! heroku auth:whoami &> /dev/null; then
    echo "Please log in to your Heroku account:"
    heroku login
    if [ $? -ne 0 ]; then
        echo "Failed to log in to Heroku."
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

echo
echo "=== Step 1: Create Heroku App ==="
read -p "Enter your app name (leave blank for random name): " app_name
if [ -z "$app_name" ]; then
    echo "Creating Heroku app with random name..."
    heroku create
else
    echo "Creating Heroku app with name: $app_name..."
    heroku create "$app_name"
fi
if [ $? -ne 0 ]; then
    echo "Failed to create Heroku app."
    read -p "Press Enter to exit..."
    exit 1
fi

echo
echo "=== Step 2: Add PostgreSQL Database ==="
echo "Adding PostgreSQL database..."
heroku addons:create heroku-postgresql:mini
if [ $? -ne 0 ]; then
    echo "Failed to add PostgreSQL database."
    read -p "Press Enter to exit..."
    exit 1
fi

echo
echo "=== Step 3: Configure Environment ==="
echo "Setting environment variables..."
heroku config:set FLASK_ENV=production

echo
echo "=== Step 4: Initialize Git Repository ==="
echo "Initializing Git repository..."
if [ -d .git ]; then
    echo "Git repository already exists."
else
    git init
    if [ $? -ne 0 ]; then
        echo "Failed to initialize Git repository."
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

echo "Adding files to Git..."
git add .
git commit -m "Initial commit for Heroku deployment"
if [ $? -ne 0 ]; then
    echo "Failed to commit files to Git."
    read -p "Press Enter to exit..."
    exit 1
fi

echo
echo "=== Step 5: Deploy to Heroku ==="
echo "Deploying application to Heroku..."
if ! git push heroku main; then
    echo "Trying master branch instead..."
    if ! git push heroku master; then
        echo "Failed to deploy to Heroku."
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

echo
echo "=== Step 6: Run Database Migrations ==="
echo "Running database migrations..."
heroku run python migrate_db.py
if [ $? -ne 0 ]; then
    echo "Failed to run database migrations."
    read -p "Press Enter to exit..."
    exit 1
fi

echo
echo "=== Step 7: Open Application ==="
echo "Opening application in web browser..."
heroku open
if [ $? -ne 0 ]; then
    echo "Failed to open application in browser."
    read -p "Press Enter to exit..."
    exit 1
fi

echo
echo "==================================="
echo "Deployment completed successfully!"
echo "==================================="
echo
echo "IMPORTANT: Don't forget to set your API keys:"
echo "heroku config:set SCHWAB_API_KEY=your_key_here"
echo "heroku config:set SCHWAB_API_SECRET=your_secret_here"
echo "heroku config:set OPENAI_API_KEY=your_openai_key_here"
echo
read -p "Press Enter to exit..."
""",

    '.gitignore': """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Flask
instance/
.webassets-cache
flask_session/

# Virtual Environment
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Heroku
.env
.env.test
"""
}


def is_excluded(path):
    """Check if path should be excluded based on patterns."""
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path:
            return True
    return False


def copy_required_files(source_dir, target_dir):
    """Copy all required files to the target directory."""
    os.makedirs(target_dir, exist_ok=True)
    
    for item in REQUIRED_FILES:
        source_path = os.path.join(source_dir, item)
        target_path = os.path.join(target_dir, item)
        
        if not os.path.exists(source_path):
            print(f"Warning: Required file/directory not found: {item}")
            continue
        
        if os.path.isfile(source_path):
            if not is_excluded(source_path):
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(source_path, target_path)
                print(f"Copied file: {item}")
        elif os.path.isdir(source_path):
            for root, dirs, files in os.walk(source_path):
                for file in files:
                    src_file_path = os.path.join(root, file)
                    if not is_excluded(src_file_path):
                        rel_path = os.path.relpath(src_file_path, source_dir)
                        dst_file_path = os.path.join(target_dir, rel_path)
                        os.makedirs(os.path.dirname(dst_file_path), exist_ok=True)
                        shutil.copy2(src_file_path, dst_file_path)
            print(f"Copied directory: {item}")


def create_additional_files(target_dir):
    """Create additional files needed for deployment."""
    for filename, content in ADDITIONAL_FILES.items():
        file_path = os.path.join(target_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Created file: {filename}")


def ensure_requirements(target_dir):
    """Ensure requirements.txt has all needed dependencies."""
    requirements_path = os.path.join(target_dir, 'requirements.txt')
    heroku_requirements_path = os.path.join(target_dir, 'requirements-heroku.txt')
    
    # Create a basic requirements.txt file if none exists
    if not os.path.exists(requirements_path) and not os.path.exists(heroku_requirements_path):
        default_requirements = """flask==2.2.3
flask-login==0.6.2
flask-sqlalchemy==3.0.3
flask-wtf==1.1.1
gunicorn==20.1.0
matplotlib==3.7.1
numpy==1.24.2
pandas==2.0.0
psycopg2-binary==2.9.6
pytest==7.3.1
pytest-tap==3.3
python-dateutil==2.8.2
requests==2.28.2
sqlalchemy==2.0.9
werkzeug==2.2.3
wtforms==3.0.1
"""
        with open(requirements_path, 'w') as req_file:
            req_file.write(default_requirements)
        print("Created new requirements.txt with essential dependencies")
        return
    
    # Check if we have Heroku specific requirements
    if os.path.exists(heroku_requirements_path):
        with open(heroku_requirements_path, 'r') as heroku_file:
            heroku_requirements = heroku_file.read()
        
        # Update the main requirements file to include Heroku requirements
        with open(requirements_path, 'w') as req_file:
            req_file.write(heroku_requirements)
            
        print("Updated requirements.txt with Heroku-specific dependencies")
    else:
        # Make sure requirements.txt exists
        if not os.path.exists(requirements_path):
            default_requirements = """flask==2.2.3
flask-login==0.6.2
flask-sqlalchemy==3.0.3
flask-wtf==1.1.1
gunicorn==20.1.0
matplotlib==3.7.1
numpy==1.24.2
pandas==2.0.0
psycopg2-binary==2.9.6
pytest==7.3.1
pytest-tap==3.3
python-dateutil==2.8.2
requests==2.28.2
sqlalchemy==2.0.9
werkzeug==2.2.3
wtforms==3.0.1
"""
            with open(requirements_path, 'w') as req_file:
                req_file.write(default_requirements)
            print("Created new requirements.txt with essential dependencies")
        
    # Create a runtime.txt file to specify Python version
    runtime_path = os.path.join(target_dir, 'runtime.txt')
    with open(runtime_path, 'w') as runtime_file:
        runtime_file.write('python-3.11.0')
    print("Created runtime.txt to specify Python 3.11.0")
    
    # Create app.json for Heroku button
    app_json_path = os.path.join(target_dir, 'app.json')
    with open(app_json_path, 'w') as app_json_file:
        app_json_file.write("""
{
  "name": "Trading Bot",
  "description": "Advanced trading bot with AI-powered analysis and multi-provider API integration",
  "repository": "https://github.com/yourusername/trading-bot",
  "logo": "https://raw.githubusercontent.com/yourusername/trading-bot/main/static/img/logo.png",
  "keywords": ["python", "flask", "trading", "finance", "ai", "schwab"],
  "addons": ["heroku-postgresql:mini"],
  "env": {
    "FLASK_ENV": {
      "description": "Flask environment",
      "value": "production"
    },
    "SCHWAB_API_KEY": {
      "description": "Your Charles Schwab API key (client ID)",
      "required": true
    },
    "SCHWAB_API_SECRET": {
      "description": "Your Charles Schwab API secret (client secret)",
      "required": true
    },
    "OPENAI_API_KEY": {
      "description": "Your OpenAI API key for AI analysis features",
      "required": false
    }
  },
  "buildpacks": [
    {
      "url": "heroku/python"
    }
  ],
  "scripts": {
    "postdeploy": "python migrate_db.py"
  }
}
""")
    print("Created app.json for Heroku button deployment")


def create_zip_package(source_dir, output_dir=None):
    """Create a ZIP package of the prepared files."""
    # Generate timestamp for the filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    zip_filename = f"trading_bot_heroku_deploy_{timestamp}.zip"
    
    if output_dir:
        zip_path = os.path.join(output_dir, zip_filename)
    else:
        zip_path = zip_filename
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)
    
    return zip_path


def main():
    """Main function to create the Heroku deployment package."""
    print("=== Creating Heroku Deployment Package ===")
    
    # Setup directories
    current_dir = os.getcwd()
    temp_dir = os.path.join(current_dir, "heroku_deploy_temp")
    output_dir = current_dir
    
    # Clean any existing temp directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    try:
        # Step 1: Copy required files
        print("\n1. Copying required files...")
        copy_required_files(current_dir, temp_dir)
        
        # Step 2: Create additional files
        print("\n2. Creating additional files...")
        create_additional_files(temp_dir)
        
        # Step 3: Ensure requirements are correct
        print("\n3. Updating requirements...")
        ensure_requirements(temp_dir)
        
        # Step 4: Create ZIP package
        print("\n4. Creating ZIP package...")
        zip_path = create_zip_package(temp_dir, output_dir)
        
        print(f"\n✅ Deployment package created successfully: {zip_path}")
        print("You can now download this file, extract it, and deploy directly to Heroku.")
        print("See DEPLOY.md in the package for quick deployment instructions.")
        
    finally:
        # Clean up temp directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()