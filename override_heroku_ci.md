# Fixing Heroku CI Test Configuration

If you're encountering the error "Unable to detect any runnable tests" in Heroku CI, this guide will help you fix it.

## The Problem

Heroku CI is not detecting your test files, which is why you're seeing this error:

```
Unable to run test with performance-m dynos. Using standard-2x instead.
An error occurred: Unable to detect any runnable tests
```

## The Solution

I've created an `app.ci` file that explicitly tells Heroku CI how to run your tests. This file configures:

1. The PostgreSQL database for testing
2. Environment variables for the test environment
3. Explicitly defines the test command to run
4. Sets the dyno size to standard-2x

## Steps to Fix

1. Make sure this `app.ci` file is included in your deployment package
2. The file specifies to use the TAP output format for pytest
3. Ensure your tests are in the appropriate structure (which we've already set up)

## How to Verify Tests Locally

Before pushing to Heroku CI, verify your tests work locally:

```bash
# Run all tests
./run_tap_tests.py

# Run only unit tests
./run_tap_tests.py --unit

# Run only integration tests
./run_tap_tests.py --integration
```

## Common Test Failures in CI

If tests pass locally but fail in CI, check for:

1. **Database connection issues**: CI uses a fresh database
2. **Environment variables**: Make sure required variables are set in the app.ci file
3. **Path differences**: CI runs in a different directory
4. **Timing issues**: CI might have different timing constraints

## Additional CI Configuration

You can further customize your CI pipeline by adding scripts to be run at different phases:

```
{
  "environments": {
    "test": {
      "scripts": {
        "test-setup": "python setup_test_data.py",
        "test": "python -m pytest",
        "test-teardown": "python cleanup_test_data.py"
      }
    }
  }
}
```

This structure allows for setup before tests and cleanup afterward.

## After Fixing CI Tests

Once your tests are running properly in CI, you can leverage the TAP output in your deployment workflow by:

1. Setting up a GitHub Action to display test results
2. Using the test results to gate deployments
3. Generating test coverage reports