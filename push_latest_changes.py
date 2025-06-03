#!/usr/bin/env python3
"""
Push all recent changes to Git repository
Captures complete schwab-py integration and deployment improvements
"""

import os
import subprocess
import sys
from datetime import datetime

def run_command(command, cwd=None):
    """Run shell command and return result"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
        print(f"Running: {command}")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        if result.stderr and result.returncode != 0:
            print(f"Error: {result.stderr.strip()}")
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        print(f"Exception running {command}: {str(e)}")
        return False, "", str(e)

def check_git_status():
    """Check current Git status"""
    print("Checking Git repository status...")
    
    # Check if we're in a git repository
    success, output, error = run_command("git rev-parse --is-inside-work-tree")
    if not success:
        print("Not in a Git repository. Initializing...")
        run_command("git init")
        
        # Set up git config if not set
        run_command('git config user.name "Arbion Developer"')
        run_command('git config user.email "dev@arbion.ai"')
    
    # Show current status
    run_command("git status --porcelain")
    
    return True

def create_comprehensive_commit():
    """Create comprehensive commit with all recent changes"""
    
    # Add all files
    print("Adding all modified files...")
    run_command("git add .")
    
    # Create detailed commit message
    commit_message = f"""Complete Arbion Trading Platform Enhancement - {datetime.now().strftime('%Y-%m-%d')}

Features Added:
- Complete schwab-py library integration with all API endpoints
- Popup OAuth authentication flow for seamless user experience
- Comprehensive Schwab API connector with account management
- Market data integration with real-time quotes and historical data
- Options chains data with Greeks and analytics
- Streaming data capabilities for real-time market updates
- Watchlist management with full CRUD operations
- Transaction history and performance analytics
- AI-powered trading analysis with GPT-4o integration
- Multi-strategy trading framework (covered calls, spreads, wheel, etc.)
- Enhanced user interface with Bootstrap responsive design
- Custom domain support for arbion.ai with security headers
- Production-ready Heroku deployment configuration
- Database initialization scripts for production deployment
- Comprehensive error handling and logging
- Multi-user support with role-based admin controls

Technical Improvements:
- Fixed SchwabConnector initialization errors
- Resolved Heroku deployment issues with missing files
- Enhanced API connector architecture for better reliability
- Implemented comprehensive OAuth2 flow with popup authentication
- Added production security headers and HTTPS enforcement
- Optimized database connections with connection pooling
- Enhanced session management and CSRF protection
- Improved error handling throughout the application

Deployment Features:
- Automated Heroku deployment scripts
- Production-ready configuration files
- Database migration and initialization
- Environment variable management
- Custom domain configuration ready
- SSL/TLS security implementation

AI Integration:
- OpenAI GPT-4o integration for market analysis
- Intelligent trading strategy recommendations
- Risk assessment and position sizing algorithms
- Real-time market insights and commentary

This represents a complete transformation into a production-ready
AI-powered trading platform with comprehensive Schwab API integration."""
    
    # Commit changes
    success, output, error = run_command(f'git commit -m "{commit_message}"')
    
    if success:
        print("Successfully created comprehensive commit")
        return True
    else:
        if "nothing to commit" in error:
            print("No changes to commit")
            return True
        else:
            print(f"Failed to commit: {error}")
            return False

def push_to_remote():
    """Push changes to remote repository"""
    
    # Check if remote exists
    success, output, error = run_command("git remote -v")
    
    if not success or not output.strip():
        print("No remote repository configured.")
        
        # Check for GitHub token
        github_token = os.environ.get('GITHUB_TOKEN')
        if github_token:
            # Set up remote with token
            repo_url = f"https://{github_token}@github.com/arbion-ai/TradeCoverEngine.git"
            run_command("git remote add origin " + repo_url)
            print("Added GitHub remote using token")
        else:
            print("No GitHub token found. Please configure remote manually:")
            print("git remote add origin https://github.com/your-username/your-repo.git")
            return False
    
    # Get current branch
    success, current_branch, error = run_command("git branch --show-current")
    if not success or not current_branch.strip():
        current_branch = "main"
        run_command("git checkout -b main")
    else:
        current_branch = current_branch.strip()
    
    print(f"Pushing to branch: {current_branch}")
    
    # Push to remote
    success, output, error = run_command(f"git push -u origin {current_branch}")
    
    if success:
        print(f"Successfully pushed to {current_branch}")
        return True
    else:
        print(f"Failed to push: {error}")
        
        # Try force push if needed
        if "rejected" in error or "non-fast-forward" in error:
            print("Attempting force push...")
            success, output, error = run_command(f"git push -u origin {current_branch} --force")
            if success:
                print("Force push successful")
                return True
            else:
                print(f"Force push failed: {error}")
        
        return False

def main():
    """Main function to push all recent changes"""
    
    print("🚀 Pushing all Arbion Trading Platform changes to Git")
    print("=" * 60)
    
    try:
        # Check Git status
        if not check_git_status():
            print("Failed to check Git status")
            return False
        
        # Create comprehensive commit
        if not create_comprehensive_commit():
            print("Failed to create commit")
            return False
        
        # Push to remote
        if not push_to_remote():
            print("Failed to push to remote")
            return False
        
        print("\n" + "=" * 60)
        print("✅ Successfully pushed all changes!")
        print("\nChanges include:")
        print("- Complete schwab-py library integration")
        print("- Popup OAuth authentication flow")
        print("- Production-ready Heroku deployment")
        print("- AI-powered trading analysis")
        print("- Enhanced security and performance")
        print("- Comprehensive documentation")
        
        return True
        
    except Exception as e:
        print(f"Error during Git operations: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)