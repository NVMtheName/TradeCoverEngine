#!/usr/bin/env python3
"""
Create a basic export with just the essential files needed for Heroku deployment.
This lightweight script won't try to copy the entire project.
"""

import os
import zipfile
import sys

# Essential files for Heroku deployment
ESSENTIAL_FILES = [
    'main.py',
    'app.py',
    'models.py',
    'forms.py',
    'utils.py',
    'config.py',
    'schwab_proxy.py',
    'proxies.py',
    'requirements.txt',
    'REQUIREMENTS.txt',
    'requirements-heroku.txt',
    'Procfile',
    '.python-version',
    'app.json',
    'heroku.yml',
    '.buildpacks'
]

# Create fresh requirements
with open('requirements.txt', 'w') as f:
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
beautifulsoup4>=4.11.1""")

# Create zip file
print("Creating basic export zip...")
zip_filename = 'heroku_deploy_basic.zip'
with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add essential files
    for file in ESSENTIAL_FILES:
        if os.path.exists(file):
            print(f"Adding {file}")
            zipf.write(file)
    
    # Add trading_bot directory
    if os.path.exists('trading_bot'):
        for root, _, files in os.walk('trading_bot'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    print(f"Adding {file_path}")
                    zipf.write(file_path)
    
    # Add templates directory
    if os.path.exists('templates'):
        for root, _, files in os.walk('templates'):
            for file in files:
                if file.endswith('.html'):
                    file_path = os.path.join(root, file)
                    print(f"Adding {file_path}")
                    zipf.write(file_path)
    
    # Add static directory
    if os.path.exists('static'):
        for root, _, files in os.walk('static'):
            for file in files:
                file_path = os.path.join(root, file)
                print(f"Adding {file_path}")
                zipf.write(file_path)

print(f"\nBasic export created successfully: {zip_filename}")
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