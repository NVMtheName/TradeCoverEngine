#!/bin/bash

# GitHub Integration Setup Script
# This script configures automatic Git operations for the TradeCoverEngine repository

echo "Setting up GitHub integration for TradeCoverEngine..."

# Repository configuration
REPO_URL="https://github.com/NVMtheName/TradeCoverEngine.git"
BRANCH="main"

# Initialize Git configuration
git config --global user.name "Replit Auto Deploy"
git config --global user.email "auto-deploy@replit.com"

# Check if we have a remote configured
if ! git remote get-url origin 2>/dev/null; then
    echo "Adding remote origin..."
    git remote add origin $REPO_URL
else
    echo "Setting remote origin..."
    git remote set-url origin $REPO_URL
fi

# Set up the branch
git checkout -B $BRANCH

# Create auto-deploy function
echo "Creating auto-deploy functionality..."

cat > auto_deploy.py << 'EOF'
#!/usr/bin/env python3
"""
Automatic deployment script for TradeCoverEngine repository
This script automatically commits and pushes changes to GitHub
"""

import subprocess
import sys
import os
from datetime import datetime

def run_command(cmd, cwd=None):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{cmd}': {e.stderr}")
        return None

def auto_deploy():
    """Automatically deploy changes to GitHub"""
    print("Starting automatic deployment...")
    
    # Check Git status
    status = run_command("git status --porcelain")
    if not status:
        print("No changes to deploy.")
        return True
    
    print(f"Found changes to deploy:\n{status}")
    
    # Add all changes
    if run_command("git add .") is None:
        return False
    
    # Create commit message with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"Auto-deploy Arbion platform updates - {timestamp}"
    
    # Commit changes
    if run_command(f'git commit -m "{commit_msg}"') is None:
        return False
    
    # Push to repository
    if run_command("git push origin main") is None:
        return False
    
    print("✅ Successfully deployed to GitHub!")
    return True

if __name__ == "__main__":
    success = auto_deploy()
    sys.exit(0 if success else 1)
EOF

chmod +x auto_deploy.py

echo "✅ GitHub integration setup complete!"
echo "To deploy changes automatically, run: python auto_deploy.py"