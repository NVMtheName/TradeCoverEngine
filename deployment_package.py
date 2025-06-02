#!/usr/bin/env python3
"""
Create a deployment package for Arbion Trading Platform
This script creates a ZIP file with all necessary files for manual deployment
"""

import os
import zipfile
import datetime

def create_deployment_package():
    """Create a ZIP file with all deployment files"""
    
    # Essential files for deployment
    files_to_include = [
        'app.py',
        'models.py', 
        'forms.py',
        'config.py',
        'requirements.txt',
        'Procfile',
        'runtime.txt',
        'app.json',
        '.gitignore',
        'README.md'
    ]
    
    # Directories to include
    directories_to_include = [
        'trading_bot',
        'templates', 
        'static',
        '.github',
        'tests'
    ]
    
    # Optional files
    optional_files = [
        'connect_existing_github_repo.md',
        'GITHUB_SETUP_INSTRUCTIONS.md',
        'heroku_deployment_checklist.md',
        'validate_deployment_setup.py'
    ]
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"arbion_deployment_{timestamp}.zip"
    
    print(f"Creating deployment package: {zip_filename}")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        
        # Add essential files
        for file in files_to_include:
            if os.path.exists(file):
                zipf.write(file)
                print(f"✓ Added {file}")
            else:
                print(f"⚠ Missing {file}")
        
        # Add optional files
        for file in optional_files:
            if os.path.exists(file):
                zipf.write(file)
                print(f"✓ Added {file}")
        
        # Add directories
        for directory in directories_to_include:
            if os.path.exists(directory):
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path)
                        print(f"✓ Added {file_path}")
    
    print(f"\n✅ Deployment package created: {zip_filename}")
    print(f"📦 File size: {os.path.getsize(zip_filename) / 1024:.1f} KB")
    
    return zip_filename

if __name__ == "__main__":
    package_file = create_deployment_package()
    
    print("\n📋 Next steps:")
    print("1. Download the ZIP file")
    print("2. Extract to your local development environment")  
    print("3. Push to your GitHub repository")
    print("4. Connect GitHub to Heroku")
    print("5. Set up API credentials in Heroku")