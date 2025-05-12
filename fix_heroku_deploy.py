#!/usr/bin/env python3
"""
Fix Heroku deployment issues by ensuring that requirements.txt is properly created.
This script makes the requirements.txt file visible to the Heroku buildpack.
"""

import os
import shutil

def ensure_requirements_file():
    """Ensure requirements.txt exists and is in the project root."""
    
    # First check if we have a requirements.txt file
    if os.path.exists('requirements.txt'):
        print("requirements.txt already exists")
        return True
    
    # Check for alternative requirements files
    alt_files = [
        'heroku_requirements.txt',
        'requirements-heroku.txt',
        'fixed_requirements.txt',
    ]
    
    for alt_file in alt_files:
        if os.path.exists(alt_file):
            print(f"Found {alt_file}, copying to requirements.txt")
            shutil.copy(alt_file, 'requirements.txt')
            return True
    
    # If no requirements file found, create a basic one
    print("No requirements file found, creating a basic one")
    with open('requirements.txt', 'w') as f:
        f.write("""flask==2.2.3
flask-login==0.6.2
flask-session==0.5.0
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
""")
    return True

def main():
    """Main function."""
    print("Fixing Heroku deployment issues...")
    
    # Check for requirements.txt
    ensure_requirements_file()
    
    # Check for runtime.txt (to specify Python version)
    if not os.path.exists('runtime.txt'):
        print("Creating runtime.txt file")
        with open('runtime.txt', 'w') as f:
            f.write('python-3.11.0')
    
    # Check for Procfile
    if not os.path.exists('Procfile'):
        print("Creating Procfile")
        with open('Procfile', 'w') as f:
            f.write('web: gunicorn --bind 0.0.0.0:$PORT --workers 2 --max-requests 1200 main:app')
    
    print("\nAll fixes applied. Your project should now deploy properly to Heroku.")
    print("If you encounter issues, please check the following:")
    print("1. Ensure requirements.txt is in the root directory")
    print("2. Ensure requirements.txt is not in .gitignore")
    print("3. Commit the requirements.txt file to your repository with `git add requirements.txt`")

if __name__ == "__main__":
    main()