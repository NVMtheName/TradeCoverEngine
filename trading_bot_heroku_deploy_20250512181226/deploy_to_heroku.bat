@echo off
echo ===================================
echo Trading Bot Heroku Deployment Script
echo ===================================
echo.

REM Check if Heroku CLI is installed
heroku --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Heroku CLI is not installed!
    echo Please install it from: https://devcenter.heroku.com/articles/heroku-cli
    echo After installing, run this script again.
    echo.
    pause
    exit /b 1
)

echo Checking Heroku login status...
heroku auth:whoami > nul 2>&1
if %errorlevel% neq 0 (
    echo Please log in to your Heroku account:
    heroku login
    if %errorlevel% neq 0 (
        echo Failed to log in to Heroku.
        pause
        exit /b 1
    )
)

echo.
echo === Step 1: Create Heroku App ===
set /p app_name=Enter your app name (leave blank for random name): 
if "%app_name%"=="" (
    echo Creating Heroku app with random name...
    heroku create
) else (
    echo Creating Heroku app with name: %app_name%...
    heroku create %app_name%
)
if %errorlevel% neq 0 (
    echo Failed to create Heroku app.
    pause
    exit /b 1
)

echo.
echo === Step 2: Add PostgreSQL Database ===
echo Adding PostgreSQL database...
heroku addons:create heroku-postgresql:mini
if %errorlevel% neq 0 (
    echo Failed to add PostgreSQL database.
    pause
    exit /b 1
)

echo.
echo === Step 3: Configure Environment ===
echo Setting environment variables...
heroku config:set FLASK_ENV=production

echo.
echo === Step 4: Initialize Git Repository ===
echo Initializing Git repository...
if exist .git (
    echo Git repository already exists.
) else (
    git init
    if %errorlevel% neq 0 (
        echo Failed to initialize Git repository.
        pause
        exit /b 1
    )
)

echo Adding files to Git...
git add .
git commit -m "Initial commit for Heroku deployment"
if %errorlevel% neq 0 (
    echo Failed to commit files to Git.
    pause
    exit /b 1
)

echo.
echo === Step 5: Deploy to Heroku ===
echo Deploying application to Heroku...
git push heroku main
if %errorlevel% neq 0 (
    echo Trying master branch instead...
    git push heroku master
    if %errorlevel% neq 0 (
        echo Failed to deploy to Heroku.
        pause
        exit /b 1
    )
)

echo.
echo === Step 6: Run Database Migrations ===
echo Running database migrations...
heroku run python migrate_db.py
if %errorlevel% neq 0 (
    echo Failed to run database migrations.
    pause
    exit /b 1
)

echo.
echo === Step 7: Open Application ===
echo Opening application in web browser...
heroku open
if %errorlevel% neq 0 (
    echo Failed to open application in browser.
    pause
    exit /b 1
)

echo.
echo ===================================
echo Deployment completed successfully!
echo ===================================
echo.
echo IMPORTANT: Don't forget to set your API keys:
echo heroku config:set SCHWAB_API_KEY=your_key_here
echo heroku config:set SCHWAB_API_SECRET=your_secret_here
echo heroku config:set OPENAI_API_KEY=your_openai_key_here
echo.
pause
