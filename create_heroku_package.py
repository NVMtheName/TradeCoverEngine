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

## Deployment Instructions

1. **Install the Heroku CLI** (if you haven't already):
   Follow instructions at https://devcenter.heroku.com/articles/heroku-cli

2. **Log in to Heroku**:
   ```
   heroku login
   ```

3. **Create a new Heroku app** (or use an existing one):
   ```
   heroku create your-app-name
   ```

4. **Add a PostgreSQL database**:
   ```
   heroku addons:create heroku-postgresql:mini
   ```

5. **Configure environment variables**:
   ```
   heroku config:set FLASK_ENV=production
   heroku config:set SCHWAB_API_KEY=your_key_here
   heroku config:set SCHWAB_API_SECRET=your_secret_here
   ```

6. **Deploy the application**:
   ```
   git push heroku main
   ```

7. **Initialize the database**:
   ```
   heroku run python migrate_db.py
   ```

8. **Visit your application**:
   ```
   heroku open
   ```

## Troubleshooting

- **Database issues**: 
  Run `heroku pg:info` to check database status.
  
- **Application errors**: 
  Check logs with `heroku logs --tail`

- **Deployment failures**: 
  Ensure you have the correct buildpacks with `heroku buildpacks`
  
## Running Tests

This application includes a TAP testing framework. To run tests in Heroku CI:

1. Enable Heroku CI for your application
2. Push changes to GitHub (if using GitHub integration)
3. Tests will automatically run using the configuration in app.ci

To run tests locally:
```
python run_tap_tests.py
```

## Additional Resources

- Heroku Python Support: https://devcenter.heroku.com/articles/python-support
- Heroku PostgreSQL: https://devcenter.heroku.com/articles/heroku-postgresql
""",

    'DEPLOY.md': """# Quick Deployment Guide

## One-Click Deployment:

1. Extract all files from this zip package
2. Install Heroku CLI
3. Run: `heroku login`
4. Run: `heroku create your-app-name`
5. Run: `heroku addons:create heroku-postgresql:mini`
6. Run: `git init && git add . && git commit -m "Initial commit"`
7. Run: `git push heroku main`
8. Run: `heroku run python migrate_db.py`
9. Run: `heroku open`

## Configuring API Keys:

After deployment, set your API keys:
```
heroku config:set SCHWAB_API_KEY=your_key_here
heroku config:set SCHWAB_API_SECRET=your_secret_here
heroku config:set OPENAI_API_KEY=your_openai_key_here
```

For detailed instructions, see README_HEROKU.md
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