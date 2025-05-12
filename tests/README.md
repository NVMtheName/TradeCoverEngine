# Trading Bot Test Suite

This directory contains tests for the Trading Bot application, structured to use the Test Anything Protocol (TAP) for reporting.

## Directory Structure

- `unit/`: Contains unit tests for individual components
  - `test_utils.py`: Tests for utility functions
  
- `integration/`: Contains integration tests spanning multiple components
  - `test_routes.py`: Tests for Flask routes and views
  - `test_database.py`: Tests for database models and relationships

- `conftest.py`: Pytest configuration and fixtures

## Running Tests

You can run tests using the included `run_tap_tests.py` script:

```bash
# Run all tests
./run_tap_tests.py

# Run only unit tests
./run_tap_tests.py --unit

# Run only integration tests
./run_tap_tests.py --integration
```

Or you can use pytest directly:

```bash
# Run all tests with TAP output
python -m pytest --tap-files --tap-combined --tap-outdir=test_results

# Run specific test file
python -m pytest tests/unit/test_utils.py --tap-files
```

## TAP Output

Test results are written to the `test_results/` directory in TAP format. The main output file is `testresults.tap`, which contains combined results from all tests.

## CI Integration

These tests are configured to run in Heroku CI using the configuration in `app.ci` at the project root. The CI environment:

1. Sets up a PostgreSQL database for testing
2. Sets the appropriate environment variables
3. Runs the tests with TAP output
4. Collects the test results

## Writing New Tests

When adding new tests:

1. Follow the existing structure (unit or integration)
2. Use the fixtures defined in `conftest.py`
3. Write clear, descriptive test functions
4. Use assertions to verify expected behavior
5. Add appropriate docstrings to explain what each test does

## Database Testing

Database tests use an in-memory SQLite database by default. In CI, they use a PostgreSQL database. The database is reset between test functions to ensure test isolation.