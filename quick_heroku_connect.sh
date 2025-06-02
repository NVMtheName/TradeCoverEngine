#!/bin/bash

# Quick Heroku GitHub Connection Script
# This bypasses Git issues by using Heroku CLI direct deployment

echo "Setting up direct Heroku deployment..."

# Install Heroku CLI if not present
if ! command -v heroku &> /dev/null; then
    echo "Installing Heroku CLI..."
    curl https://cli-assets.heroku.com/install.sh | sh
fi

# Login to Heroku (user will need to provide auth)
echo "Please run: heroku login"
echo "Then run: heroku git:remote -a your-heroku-app-name"

# Create deployment command
cat > deploy_to_heroku.py << 'EOF'
#!/usr/bin/env python3
"""
Direct Heroku deployment bypass for Git issues
This deploys directly to Heroku without local Git operations
"""

import subprocess
import os
import sys

def deploy_direct():
    """Deploy directly to Heroku"""
    print("Deploying to Heroku...")
    
    # Check if Heroku remote exists
    try:
        result = subprocess.run(['heroku', 'apps:info'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("Please connect to your Heroku app first:")
            print("heroku git:remote -a your-heroku-app-name")
            return False
    except FileNotFoundError:
        print("Heroku CLI not found. Please install it first.")
        return False
    
    # Create a temporary Git repository for deployment
    temp_dir = "/tmp/heroku_deploy"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Copy files to temp directory
    subprocess.run(['cp', '-r', '.', temp_dir], 
                   capture_output=True)
    
    # Initialize Git in temp directory
    os.chdir(temp_dir)
    subprocess.run(['git', 'init'])
    subprocess.run(['git', 'add', '.'])
    subprocess.run(['git', 'commit', '-m', 'Deploy Arbion platform'])
    
    # Deploy to Heroku
    result = subprocess.run(['git', 'push', 'heroku', 'main', '--force'])
    
    if result.returncode == 0:
        print("✅ Successfully deployed to Heroku!")
        return True
    else:
        print("❌ Deployment failed")
        return False

if __name__ == "__main__":
    deploy_direct()
EOF

chmod +x deploy_to_heroku.py

echo "✅ Direct Heroku deployment setup complete!"
echo "Run: python deploy_to_heroku.py"