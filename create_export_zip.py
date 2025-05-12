#!/usr/bin/env python3
"""
Export Trading Bot Project to ZIP File

This script creates a clean ZIP file with all necessary files for deployment,
ensuring that requirements.txt and other essential files are included.
"""

import os
import shutil
import zipfile
import tempfile
import sys

# Files to include (everything except certain files/folders)
EXCLUDE_PATTERNS = [
    '.git/', '.github/', '.replit/', '.upm/', '__pycache__/', 
    '.DS_Store', '.gitignore', '.env', '*.pyc', 'venv/', 'env/',
    '*.zip', 'tmp/', 'temp/', 'test_results/', 'flask_session/'
]

# Essential files that must be included for Heroku
ESSENTIAL_FILES = [
    'requirements.txt',
    'REQUIREMENTS.txt',
    'requirements-heroku.txt',
    'Procfile',
    '.python-version',
    'app.json',
    'heroku.yml',
    '.buildpacks'
]

def should_include(path):
    """Check if a file/folder should be included."""
    for pattern in EXCLUDE_PATTERNS:
        if pattern.endswith('/'):  # Directory
            if path.startswith(pattern[:-1]):
                return False
        elif '*' in pattern:  # Wildcard pattern
            ext = pattern.replace('*', '')
            if path.endswith(ext):
                return False
        elif path == pattern:  # Exact match
            return False
    return True

def create_zip_export():
    """Create a clean zip file with all project files."""
    print("Creating deployment export ZIP file...")
    
    # Generate fresh requirements files
    if os.path.exists('fix_heroku_requirements.py'):
        print("Generating fresh requirements files...")
        os.system('python fix_heroku_requirements.py')
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        print(f"Using temporary directory: {tmp_dir}")
        
        # Copy all files to temp directory
        print("Copying project files...")
        for root, dirs, files in os.walk('.'):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if should_include(os.path.join(root, d) + '/')]
            
            for file in files:
                src_path = os.path.join(root, file)
                if should_include(src_path):
                    # Preserve directory structure
                    rel_path = os.path.relpath(src_path, '.')
                    dst_path = os.path.join(tmp_dir, rel_path)
                    
                    # Create destination directory if it doesn't exist
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    
                    # Copy the file
                    shutil.copy2(src_path, dst_path)
        
        # Check essential files
        missing_files = []
        for file in ESSENTIAL_FILES:
            if not os.path.exists(os.path.join(tmp_dir, file)):
                missing_files.append(file)
        
        if missing_files:
            print("WARNING: Missing essential files for Heroku deployment:")
            for file in missing_files:
                print(f"  - {file}")
            print("These files will be created automatically...")
            
            # Create missing files
            for file in missing_files:
                if file == 'requirements.txt' or file == 'REQUIREMENTS.txt' or file == 'requirements-heroku.txt':
                    with open(os.path.join(tmp_dir, file), 'w') as f:
                        f.write("""flask>=2.2.0
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
beautifulsoup4>=4.11.1
""")
                elif file == 'Procfile':
                    with open(os.path.join(tmp_dir, file), 'w') as f:
                        f.write('web: pip install -r requirements-heroku.txt && gunicorn --workers=2 --bind 0.0.0.0:$PORT --timeout 60 main:app\nrelease: python -c "from app import app, db; app.app_context().push(); db.create_all()"')
                elif file == '.python-version':
                    with open(os.path.join(tmp_dir, file), 'w') as f:
                        f.write('3.10.12')
                elif file == 'app.json':
                    with open(os.path.join(tmp_dir, file), 'w') as f:
                        f.write("""
{
  "name": "Trading Bot",
  "description": "A sophisticated trading bot with multi-provider API integration",
  "repository": "https://github.com/username/trading-bot",
  "keywords": ["python", "flask", "trading", "bot", "api"],
  "success_url": "/",
  "buildpacks": [
    {
      "url": "heroku/python"
    }
  ],
  "env": {
    "FLASK_ENV": {
      "description": "The environment to run the application in",
      "value": "production"
    },
    "FLASK_SECRET_KEY": {
      "description": "A secret key for verifying the integrity of signed cookies",
      "generator": "secret"
    }
  },
  "addons": [
    {
      "plan": "heroku-postgresql:mini",
      "as": "DATABASE"
    }
  ],
  "scripts": {
    "postdeploy": "python -c \\"from app import app, db; app.app_context().push(); db.create_all()\\""
  }
}""")
                elif file == 'heroku.yml':
                    with open(os.path.join(tmp_dir, file), 'w') as f:
                        f.write("""build:
  languages:
    python: "3.10.12"

setup:
  addons:
    - plan: heroku-postgresql:mini
      as: DATABASE

run:
  web: gunicorn --workers=2 --bind 0.0.0.0:$PORT --timeout 60 main:app""")
                elif file == '.buildpacks':
                    with open(os.path.join(tmp_dir, file), 'w') as f:
                        f.write('https://github.com/heroku/heroku-buildpack-python.git')
        
        # Create the ZIP file
        zip_filename = 'trading_bot_deployment.zip'
        print(f"Creating ZIP file: {zip_filename}")
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(tmp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, tmp_dir)
                    zipf.write(file_path, arcname)
    
    print("\nExport completed successfully!")
    print(f"ZIP file created: {zip_filename}")
    print("\nTo deploy to Heroku:")
    print("1. Extract the ZIP file")
    print("2. Initialize a Git repository in the extracted folder:")
    print("   git init")
    print("   git add .")
    print("   git commit -m \"Initial deployment\"")
    print("3. Connect to your Heroku app:")
    print("   heroku git:remote -a your-app-name")
    print("4. Push to Heroku:")
    print("   git push heroku main")
    
    return 0

if __name__ == "__main__":
    sys.exit(create_zip_export())