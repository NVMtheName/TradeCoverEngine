#!/usr/bin/env python3
"""
Trading Bot Project Export Script

This script creates a ZIP file containing all necessary files for the trading bot project,
ready to be uploaded to GitHub.

Usage:
    python export_project.py

This will create a trading-bot-export.zip file with all project files, properly organized,
and including GitHub configuration files.
"""

import os
import zipfile
import json
import shutil
import tempfile
from datetime import datetime

# Files to include in the export
FILES_TO_INCLUDE = [
    # Python files
    '*.py',
    # Templates and static files
    'templates/**/*',
    'static/**/*',
    # Trading bot modules
    'trading_bot/**/*',
    # Configuration files
    'pyproject.toml',
]

# Files to exclude
FILES_TO_EXCLUDE = [
    # Temporary files
    '*.pyc',
    '__pycache__',
    '.replit',
    'replit.nix',
    # Database files
    '*.db',
    '*.sqlite',
    # Environment variables
    '.env',
    # Session files
    'flask_session/*',
]

# GitHub repository config files to create
GITHUB_CONFIG = {
    '.gitignore': """
# Python
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
flask_session/
.webassets-cache

# Environment variables
.env
.venv
env/
venv/
ENV/

# Database
*.db
*.sqlite
*.sqlite3

# Heroku
.heroku/

# Logs
*.log
logs/

# IDE specific files
.idea/
.vscode/
*.swp
*.swo
*.sublime-workspace
*.sublime-project

# OS specific files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
""",
    'README.md': """
# Schwab Trading Bot

A sophisticated Python-based trading bot that leverages multi-provider API integrations, advanced AI technologies, and intelligent automation to execute complex trading strategies with comprehensive market analysis.

## Key Features

- Multi-provider API integration (Alpaca, TD Ameritrade, Schwab)
- Advanced OAuth2 authentication flow
- AI-powered market insights and strategy recommendations
- Real-time stock data processing and analysis
- Robust error handling and API management
- Scalable trading strategy framework with AI advisor support
- Forex trading capabilities
- Simulation mode for testing without real API connections

## Setup Instructions

### Local Development

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/trading-bot.git
   cd trading-bot
   ```

2. Set up a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables
   Create a `.env` file with the following:
   ```
   DATABASE_URL=sqlite:///instance/tradingbot.db
   SCHWAB_API_KEY=your_api_key
   SCHWAB_API_SECRET=your_api_secret
   SECRET_KEY=your_secret_key
   OPENAI_API_KEY=your_openai_api_key
   ```

5. Initialize the database
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

6. Run the application
   ```bash
   python main.py
   ```

### Heroku Deployment

Follow the instructions in [HEROKU.md](HEROKU.md) to deploy this application to Heroku.

## Supported Trading Strategies

- Covered Call
- Wheel Strategy
- Collar Strategy
- Put Credit Spread
- Iron Condor

## Security Notes

- Never commit API keys or secrets to the repository
- Use environment variables for all sensitive information
- Enable simulation mode for testing

## License

[MIT License](LICENSE)
""",
    'HEROKU.md': """
# Heroku Deployment Guide

## Prerequisites

- Heroku CLI installed
- Git repository initialized
- Schwab API credentials

## Setup Steps

1. Create a new Heroku app
   ```bash
   heroku create schwab-trading-bot
   ```

2. Add PostgreSQL database
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   ```

3. Add a static IP for Schwab API whitelisting
   ```bash
   heroku addons:create quotaguardstatic:starter
   ```

4. Configure environment variables
   ```bash
   heroku config:set SCHWAB_API_KEY=your_api_key
   heroku config:set SCHWAB_API_SECRET=your_api_secret
   heroku config:set SECRET_KEY=your_random_secret_key
   heroku config:set OPENAI_API_KEY=your_openai_api_key
   ```

5. Deploy to Heroku
   ```bash
   git push heroku main
   ```

6. Initialize the database
   ```bash
   heroku run python -c "from app import app, db; with app.app_context(): db.create_all()"
   ```

7. Scale the application
   ```bash
   heroku ps:scale web=1
   ```

## Schwab API Integration

1. Get your static IP from Heroku
   ```bash
   heroku config | grep QUOTAGUARDSTATIC_URL
   ```

2. Update your Schwab Developer Portal app with:
   - New callback URL: `https://your-app-name.herokuapp.com/oauth/callback`
   - Request IP whitelisting for your QuotaGuard static IP

## Monitoring

Monitor your application with:
```bash
heroku logs --tail
```

## Scheduler for Automated Trading

If you need scheduled tasks:
```bash
heroku addons:create scheduler:standard
```

Then configure jobs through the Heroku dashboard.
""",
    'LICENSE': """
MIT License

Copyright (c) 2025 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""",
    'requirements.txt': """
flask==2.0.1
flask-login==0.5.0
flask-session==0.4.0
flask-sqlalchemy==3.0.3
flask-wtf==1.0.0
flask-migrate==3.1.0
gunicorn==20.1.0
matplotlib==3.5.1
numpy==1.22.3
pandas==1.4.2
psycopg2-binary==2.9.3
python-dateutil==2.8.2
requests==2.27.1
oauthlib==3.2.0
openai==0.27.0
werkzeug==2.0.3
wtforms==3.0.1
email-validator==1.1.3
trafilatura==1.4.0
sqlalchemy==1.4.46
python-dotenv==0.20.0
""",
    'Procfile': """web: gunicorn main:app""",
    'runtime.txt': """python-3.9.13""",
    '.env.example': """
# Database connection
DATABASE_URL=postgresql://username:password@localhost:5432/tradingbot

# Schwab API credentials
SCHWAB_API_KEY=your_api_key_here
SCHWAB_API_SECRET=your_api_secret_here

# OpenAI API key (optional, for AI features)
OPENAI_API_KEY=your_openai_api_key_here

# Flask session security
SECRET_KEY=generate_a_secure_random_key_here
""",
    'proxies.py': """
import os
import urllib.parse

def get_proxy_session():
    \"\"\"Create a requests session configured to use the QuotaGuard Static proxy\"\"\"
    import requests
    
    session = requests.Session()
    
    # Check if QUOTAGUARDSTATIC_URL is set
    quotaguardstatic_url = os.environ.get('QUOTAGUARDSTATIC_URL')
    if quotaguardstatic_url:
        url = urllib.parse.urlparse(quotaguardstatic_url)
        
        # Configure proxy settings
        proxy_url = f"{url.scheme}://{url.netloc}"
        proxy_auth = f"{url.username}:{url.password}"
        
        session.proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # Add proxy authentication
        session.auth = (url.username, url.password)
        
    return session
""",
    '.github/workflows/python-app.yml': """
name: Python application

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python 3.9
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
    - name: Run tests
      run: |
        # Add your test commands here
        echo "No tests configured yet"
    - name: Lint with flake8
      run: |
        pip install flake8
        # stop the build if there are Python syntax errors or undefined names
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
""",
    '.github/dependabot.yml': """
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
"""
}

def create_zip_file():
    """Create a ZIP file with all the project files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"trading-bot-export.zip"
    
    print(f"Creating temporary directory...")
    with tempfile.TemporaryDirectory() as temp_dir:
        export_dir = os.path.join(temp_dir, "trading-bot")
        os.makedirs(export_dir)
        
        # Copy existing project files
        print("Copying project files...")
        for root, dirs, files in os.walk('.'):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', 'flask_session', '.git', 'venv', 'env']]
            
            # Create same directory structure in export_dir
            rel_path = os.path.relpath(root, '.')
            if rel_path == '.':
                target_dir = export_dir
            else:
                target_dir = os.path.join(export_dir, rel_path)
                os.makedirs(target_dir, exist_ok=True)
            
            # Copy files
            for file in files:
                source_file = os.path.join(root, file)
                # Skip certain files
                if any(exclude in source_file for exclude in FILES_TO_EXCLUDE):
                    continue
                
                # Skip this export script itself
                if source_file == './export_project.py':
                    continue
                
                # Skip files that are too large
                if os.path.getsize(source_file) > 10 * 1024 * 1024:  # Skip files > 10MB
                    print(f"Skipping large file: {source_file}")
                    continue
                
                target_file = os.path.join(target_dir, file)
                try:
                    shutil.copy2(source_file, target_file)
                except (shutil.SameFileError, IsADirectoryError, PermissionError) as e:
                    print(f"Error copying {source_file}: {e}")
        
        # Create GitHub config files
        print("Creating GitHub configuration files...")
        for filepath, content in GITHUB_CONFIG.items():
            # Create directory if it doesn't exist
            dir_path = os.path.join(export_dir, os.path.dirname(filepath))
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            # Write file content
            with open(os.path.join(export_dir, filepath), 'w') as f:
                f.write(content.strip())
        
        # Create the zip file
        print(f"Creating ZIP file: {zip_filename}")
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(export_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, rel_path)
    
    print(f"\nExport complete!\n")
    print(f"Your trading bot project has been exported to: {zip_filename}")
    print("This ZIP file includes all project files and GitHub configuration.")
    print("\nTo use this with GitHub:")
    print("1. Unzip the file to a local directory")
    print("2. Navigate to that directory")
    print("3. Initialize a Git repository: git init")
    print("4. Add all files: git add .")
    print("5. Commit: git commit -m \"Initial commit\"")
    print("6. Create a GitHub repository at https://github.com/new")
    print("7. Add remote: git remote add origin https://github.com/yourusername/your-repo.git")
    print("8. Push: git push -u origin main")
    print("\nFor Heroku deployment, follow the instructions in HEROKU.md")
    
    return zip_filename

if __name__ == "__main__":
    zip_file = create_zip_file()
    print(f"ZIP file created: {zip_file}")