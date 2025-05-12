#!/bin/bash

echo "==================================="
echo "Trading Bot Heroku Deployment Script"
echo "==================================="
echo

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "Heroku CLI is not installed!"
    echo "Please install it from: https://devcenter.heroku.com/articles/heroku-cli"
    echo "After installing, run this script again."
    echo
    read -p "Press Enter to exit..."
    exit 1
fi

echo "Checking Heroku login status..."
if ! heroku auth:whoami &> /dev/null; then
    echo "Please log in to your Heroku account:"
    heroku login
    if [ $? -ne 0 ]; then
        echo "Failed to log in to Heroku."
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

echo
echo "=== Step 1: Create Heroku App ==="
read -p "Enter your app name (leave blank for random name): " app_name
if [ -z "$app_name" ]; then
    echo "Creating Heroku app with random name..."
    heroku create
else
    echo "Creating Heroku app with name: $app_name..."
    heroku create "$app_name"
fi
if [ $? -ne 0 ]; then
    echo "Failed to create Heroku app."
    read -p "Press Enter to exit..."
    exit 1
fi

echo
echo "=== Step 2: Add PostgreSQL Database ==="
echo "Adding PostgreSQL database..."
heroku addons:create heroku-postgresql:mini
if [ $? -ne 0 ]; then
    echo "Failed to add PostgreSQL database."
    read -p "Press Enter to exit..."
    exit 1
fi

echo
echo "=== Step 3: Configure Environment ==="
echo "Setting environment variables..."
heroku config:set FLASK_ENV=production

echo
echo "=== Step 4: Initialize Git Repository ==="
echo "Initializing Git repository..."
if [ -d .git ]; then
    echo "Git repository already exists."
else
    git init
    if [ $? -ne 0 ]; then
        echo "Failed to initialize Git repository."
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

echo "Adding files to Git..."
git add .
git commit -m "Initial commit for Heroku deployment"
if [ $? -ne 0 ]; then
    echo "Failed to commit files to Git."
    read -p "Press Enter to exit..."
    exit 1
fi

echo
echo "=== Step 5: Deploy to Heroku ==="
echo "Deploying application to Heroku..."
if ! git push heroku main; then
    echo "Trying master branch instead..."
    if ! git push heroku master; then
        echo "Failed to deploy to Heroku."
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

echo
echo "=== Step 6: Run Database Migrations ==="
echo "Running database migrations..."
heroku run python migrate_db.py
if [ $? -ne 0 ]; then
    echo "Failed to run database migrations."
    read -p "Press Enter to exit..."
    exit 1
fi

echo
echo "=== Step 7: Open Application ==="
echo "Opening application in web browser..."
heroku open
if [ $? -ne 0 ]; then
    echo "Failed to open application in browser."
    read -p "Press Enter to exit..."
    exit 1
fi

echo
echo "==================================="
echo "Deployment completed successfully!"
echo "==================================="
echo
echo "IMPORTANT: Don't forget to set your API keys:"
echo "heroku config:set SCHWAB_API_KEY=your_key_here"
echo "heroku config:set SCHWAB_API_SECRET=your_secret_here"
echo "heroku config:set OPENAI_API_KEY=your_openai_key_here"
echo
read -p "Press Enter to exit..."
