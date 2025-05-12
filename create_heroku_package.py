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

# Additional files to create or modify
ADDITIONAL_FILES = {
    'README_HEROKU.md': """# Trading Bot - Heroku Deployment

This package contains a ready-to-deploy version of the Trading Bot application for Heroku.

## Super Easy Deployment (No Python Experience Needed)

1. **Create a Heroku Account**:
   Go to https://signup.heroku.com/ and create a free account if you don't already have one.

2. **Install the Heroku CLI**:
   Download and install from https://devcenter.heroku.com/articles/heroku-cli

3. **Extract this ZIP file** to a folder on your computer.

4. **Open Command Prompt or Terminal**:
   - On Windows: Press Win+R, type "cmd" and press Enter
   - On Mac: Open Terminal from Applications > Utilities

5. **Navigate to the extracted folder**:
   ```
   cd path/to/extracted/folder
   ```

6. **Run the deployment helper script**:
   ```
   deploy_to_heroku.bat    (on Windows)
   ```
   or
   ```
   ./deploy_to_heroku.sh   (on Mac/Linux)
   ```

7. **Follow the prompts** in the script - it will:
   - Log you into Heroku
   - Create your app
   - Set up the database
   - Deploy the application
   - Run database migrations
   - Open your app in a browser

## Configuring API Keys (After Deployment)

After your app is running, you'll need to set up your API keys:
```
heroku config:set SCHWAB_API_KEY=your_key_here
heroku config:set SCHWAB_API_SECRET=your_secret_here
heroku config:set OPENAI_API_KEY=your_openai_key_here
```

## Troubleshooting

- **Database issues**: 
  Run `heroku pg:info` to check database status.
  
- **Application errors**: 
  Check logs with `heroku logs --tail`

- **Deployment failures**: 
  Ensure you have the correct buildpacks with `heroku buildpacks`
  
## Additional Resources

- Heroku Python Support: https://devcenter.heroku.com/articles/python-support
- Heroku PostgreSQL: https://devcenter.heroku.com/articles/heroku-postgresql
""",

    'DEPLOY.md': """# Super Quick Deployment Guide

## One-Click Deployment:

1. Extract all files from this zip package
2. Double-click:
   - `deploy_to_heroku.bat` (on Windows)
   - `deploy_to_heroku.sh` (on Mac/Linux)
3. Follow the on-screen prompts

That's it! The script will handle everything else for you.

## What the Script Does:

1. Checks if Heroku CLI is installed (guides you to install if needed)
2. Logs you into Heroku
3. Creates your app 
4. Sets up PostgreSQL database
5. Initializes Git repository
6. Deploys the application
7. Runs database migrations
8. Opens your app in a browser

## After Deployment:

Set your API keys:
```
heroku config:set SCHWAB_API_KEY=your_key_here
heroku config:set SCHWAB_API_SECRET=your_secret_here
heroku config:set OPENAI_API_KEY=your_openai_key_here
```

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
    
    # Check if we have Heroku specific requirements
    if os.path.exists(heroku_requirements_path):
        with open(heroku_requirements_path, 'r') as heroku_file:
            heroku_requirements = heroku_file.read()
        
        # Update the main requirements file to include Heroku requirements
        with open(requirements_path, 'w') as req_file:
            req_file.write(heroku_requirements)
            
        print("Updated requirements.txt with Heroku-specific dependencies")
        
    # Create a runtime.txt file to specify Python version
    runtime_path = os.path.join(target_dir, 'runtime.txt')
    with open(runtime_path, 'w') as runtime_file:
        runtime_file.write('python-3.11.0')
    print("Created runtime.txt to specify Python 3.11.0")


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