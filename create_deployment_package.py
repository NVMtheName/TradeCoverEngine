#!/usr/bin/env python3
"""
Create a deployment package for manual upload to GitHub
This script creates a ZIP file with all necessary files for Heroku deployment
"""

import os
import zipfile
import datetime

def create_deployment_zip():
    """Create ZIP file with all deployment files"""
    
    # Define files to include in deployment
    deployment_files = [
        # Core application
        'app.py',
        'models.py', 
        'forms.py',
        'config.py',
        
        # Deployment configuration
        'Procfile',
        'runtime.txt',
        'app.json',
        'requirements.txt',
        '.gitignore',
        
        # GitHub workflows
        '.github/workflows/heroku-deploy.yml',
        '.github/workflows/test.yml',
        
        # Documentation
        'README.md',
        'connect_existing_github_repo.md',
        'GITHUB_SETUP_INSTRUCTIONS.md',
        'heroku_deployment_checklist.md',
        'FILES_TO_PUSH.md',
        
        # Utility scripts
        'validate_deployment_setup.py',
        'quick_heroku_connect.sh',
        'repush_to_github.sh',
        'heroku_optimization.py',
        'heroku_cli_install_guide.md',
        
        # Templates and static files
        'templates/',
        'static/',
        'trading_bot/',
        
        # Test files
        'test.py',
        'tests/'
    ]
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"arbion_deployment_{timestamp}.zip"
    
    print(f"Creating deployment package: {zip_filename}")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in deployment_files:
            if os.path.exists(item):
                if os.path.isfile(item):
                    zipf.write(item)
                    print(f"Added file: {item}")
                elif os.path.isdir(item):
                    for root, dirs, files in os.walk(item):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path)
                            zipf.write(file_path, arcname)
                            print(f"Added: {arcname}")
            else:
                print(f"Skipped (not found): {item}")
    
    print(f"\nDeployment package created: {zip_filename}")
    print(f"File size: {os.path.getsize(zip_filename)} bytes")
    
    return zip_filename

if __name__ == "__main__":
    create_deployment_zip()