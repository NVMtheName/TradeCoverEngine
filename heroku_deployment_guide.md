# Trading Bot Heroku Deployment Guide

This guide provides instructions for deploying the Trading Bot application to Heroku using the one-stop deployment package.

## One-Stop Package Deployment

### Step 1: Create the Deployment Package
```bash
python create_heroku_package.py
```
This creates a ZIP file named `trading_bot_heroku_deploy_[timestamp].zip` with all the necessary files for Heroku deployment.

### Step 2: Download the ZIP File
Download the generated ZIP file to your local machine.

### Step 3: Extract the ZIP File
Extract the contents to a new directory on your local machine.

### Step 4: Deploy to Heroku

#### If you're new to Heroku:
1. Sign up for a Heroku account at https://signup.heroku.com/
2. Install the Heroku CLI from https://devcenter.heroku.com/articles/heroku-cli
3. Open a terminal/command prompt and navigate to the extracted directory
4. Log in to Heroku:
   ```bash
   heroku login
   ```
5. Initialize a Git repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```
6. Create a new Heroku app:
   ```bash
   heroku create your-app-name
   ```
   Replace `your-app-name` with your desired application name.
7. Add PostgreSQL database:
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```
8. Deploy the application:
   ```bash
   git push heroku main
   ```
9. Run database migrations:
   ```bash
   heroku run python migrate_db.py
   ```
10. Open your application:
    ```bash
    heroku open
    ```

### Step 5: Configure API Keys
Set up your API keys after deployment:
```bash
heroku config:set SCHWAB_API_KEY=your_key_here
heroku config:set SCHWAB_API_SECRET=your_secret_here
heroku config:set OPENAI_API_KEY=your_openai_key_here
```

## Troubleshooting

### Common Issues:

1. **Build fails**:
   - Check your `requirements.txt` file
   - Ensure you're using Python 3.10 or newer 
   - Run `heroku logs --source=app` to see detailed errors

2. **Database migration errors**:
   - Verify PostgreSQL addon is properly installed:
     ```bash
     heroku addons | grep postgresql
     ```
   - Check database connection:
     ```bash
     heroku pg:info
     ```

3. **Application errors after deployment**:
   - Check application logs:
     ```bash
     heroku logs --tail
     ```

4. **Authentication fails with Charles Schwab API**:
   - Verify your API keys are correctly set in config variables
   - Ensure your OAuth callback URLs are properly configured in Schwab Developer Portal

## Maintenance and Updates

### Updating your application:

1. Make changes to your local files
2. Commit changes:
   ```bash
   git add .
   git commit -m "Description of changes"
   ```
3. Deploy:
   ```bash
   git push heroku main
   ```

### Running tests:

You can run tests on Heroku:
```bash
heroku run python run_tap_tests.py
```

## Additional Resources

- [Heroku Python Support](https://devcenter.heroku.com/articles/python-support)
- [Heroku PostgreSQL](https://devcenter.heroku.com/articles/heroku-postgresql)
- [Managing Environment Variables](https://devcenter.heroku.com/articles/config-vars)
- [Heroku CLI Commands](https://devcenter.heroku.com/articles/heroku-cli-commands)