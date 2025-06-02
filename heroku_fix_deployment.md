# Fix Heroku CI Test Detection Error

## The Issue
Heroku CI can't find runnable tests, causing deployment failures.

## Solution
I've updated the `app.json` file to fix the test configuration. Upload this updated file to your GitHub repository to resolve the issue.

## Changes Made
- Added proper test environment variables (FLASK_ENV, OPENAI_API_KEY, SCHWAB_API_KEY, SCHWAB_API_SECRET)
- Configured test script to use the TAP test runner: `python run_tap_tests.py --unit`
- Added database setup step for testing

## Next Steps
1. Replace the `app.json` file in your GitHub repository with this updated version
2. Commit and push the changes
3. Heroku will automatically retry the build with working tests

The updated configuration will allow Heroku CI to properly detect and run your tests during deployment.