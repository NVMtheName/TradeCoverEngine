#!/usr/bin/env python3
"""
Deployment Setup Validation for Arbion Trading Platform
Validates that all files and configurations are ready for GitHub to Heroku deployment
"""

import os
import json
import sys

def check_required_files():
    """Check if all required deployment files exist"""
    required_files = [
        'app.py',
        'requirements.txt', 
        'Procfile',
        'runtime.txt',
        'app.json',
        '.gitignore',
        'README.md',
        '.github/workflows/heroku-deploy.yml',
        '.github/workflows/test.yml'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
        else:
            print(f"✓ {file}")
    
    if missing_files:
        print(f"✗ Missing files: {missing_files}")
        return False
    return True

def validate_app_json():
    """Validate app.json configuration"""
    try:
        with open('app.json', 'r') as f:
            config = json.load(f)
        
        required_keys = ['name', 'description', 'buildpacks', 'addons', 'env']
        for key in required_keys:
            if key not in config:
                print(f"✗ app.json missing key: {key}")
                return False
        
        print("✓ app.json configuration valid")
        return True
    except Exception as e:
        print(f"✗ app.json validation failed: {e}")
        return False

def validate_procfile():
    """Validate Procfile configuration"""
    try:
        with open('Procfile', 'r') as f:
            content = f.read()
        
        if 'web:' not in content:
            print("✗ Procfile missing web process")
            return False
        
        if 'gunicorn' not in content:
            print("✗ Procfile should use gunicorn")
            return False
        
        print("✓ Procfile configuration valid")
        return True
    except Exception as e:
        print(f"✗ Procfile validation failed: {e}")
        return False

def validate_github_workflows():
    """Validate GitHub Actions workflows"""
    workflow_files = [
        '.github/workflows/heroku-deploy.yml',
        '.github/workflows/test.yml'
    ]
    
    for workflow in workflow_files:
        if not os.path.exists(workflow):
            print(f"✗ Missing workflow: {workflow}")
            return False
        
        try:
            with open(workflow, 'r') as f:
                content = f.read()
            
            if 'on:' not in content:
                print(f"✗ Invalid workflow format: {workflow}")
                return False
            
            print(f"✓ {workflow} valid")
        except Exception as e:
            print(f"✗ Workflow validation failed {workflow}: {e}")
            return False
    
    return True

def check_environment_requirements():
    """Check if environment variable documentation is complete"""
    required_env_docs = [
        'OPENAI_API_KEY',
        'SCHWAB_API_KEY', 
        'SCHWAB_API_SECRET',
        'FLASK_ENV',
        'SESSION_SECRET'
    ]
    
    try:
        with open('app.json', 'r') as f:
            config = json.load(f)
        
        env_section = config.get('env', {})
        missing_env = []
        
        for env_var in required_env_docs:
            if env_var not in env_section:
                missing_env.append(env_var)
        
        if missing_env:
            print(f"✗ Missing environment variables in app.json: {missing_env}")
            return False
        
        print("✓ Environment variables documented")
        return True
    except Exception as e:
        print(f"✗ Environment validation failed: {e}")
        return False

def main():
    """Run all validation checks"""
    print("Validating Arbion Deployment Setup")
    print("=" * 40)
    
    checks = [
        ("Required Files", check_required_files),
        ("app.json Configuration", validate_app_json),
        ("Procfile Configuration", validate_procfile), 
        ("GitHub Workflows", validate_github_workflows),
        ("Environment Variables", check_environment_requirements)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("✓ All validation checks passed!")
        print("\nNext steps:")
        print("1. Create GitHub repository")
        print("2. Push code to GitHub")
        print("3. Create Heroku app")
        print("4. Connect GitHub to Heroku")
        print("5. Set up environment variables")
        print("\nRefer to GITHUB_SETUP_INSTRUCTIONS.md for detailed steps")
        return 0
    else:
        print("✗ Some validation checks failed")
        print("Please fix the issues above before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())