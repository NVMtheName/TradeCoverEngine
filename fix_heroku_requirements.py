#!/usr/bin/env python3
"""
This script creates a fresh requirements.txt file in the root directory.
Run this script before pushing to Heroku to ensure the requirements file is detected.
"""

import os
import sys

REQUIREMENTS = """flask>=2.2.0
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
"""

def main():
    """Create requirements.txt in the current directory."""
    # Make sure we're in the project root
    if not os.path.exists('app.py'):
        print("Please run this script from the project root directory.")
        return 1
    
    # Write multiple variations of requirements files
    with open('requirements.txt', 'w') as f:
        f.write(REQUIREMENTS)
    print("✓ Created requirements.txt")
    
    with open('REQUIREMENTS.txt', 'w') as f:
        f.write(REQUIREMENTS)
    print("✓ Created REQUIREMENTS.txt")
    
    with open('requirements-heroku.txt', 'w') as f:
        f.write(REQUIREMENTS)
    print("✓ Created requirements-heroku.txt")
    
    print("\nAll requirements files created successfully!")
    print("Now run the following git commands:")
    print("\ngit add requirements.txt REQUIREMENTS.txt requirements-heroku.txt")
    print("git commit -m \"Add multiple requirements files for Heroku deployment\"")
    print("git push heroku main")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())