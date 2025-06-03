#!/bin/bash
# Git troubleshooting and push commands

echo "=== Git Repository Diagnostics ==="

# Check current repository status
echo "1. Current branch:"
git branch

echo -e "\n2. Remote repositories:"
git remote -v

echo -e "\n3. Git status:"
git status --porcelain | head -5

echo -e "\n4. Recent commits:"
git log --oneline -3

echo -e "\n5. Check if main branch exists on remote:"
git ls-remote --heads origin

echo -e "\n=== Suggested Commands ==="
echo "Based on the diagnostics above, try these commands:"
echo ""
echo "# Option 1: Push to main branch"
echo "git push origin main"
echo ""
echo "# Option 2: Push to master branch"
echo "git push origin master"
echo ""
echo "# Option 3: Create and push main branch"
echo "git checkout -b main"
echo "git push -u origin main"
echo ""
echo "# Option 4: Force push (use carefully)"
echo "git push origin main --force"
echo ""
echo "# Option 5: Set upstream and push"
echo "git push --set-upstream origin main"