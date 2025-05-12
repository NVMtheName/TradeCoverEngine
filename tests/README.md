# Testing Framework

This project uses pytest with TAP (Test Anything Protocol) output for standardized test reporting.

## Structure

- `tests/unit/`: Unit tests for individual components
- `tests/integration/`: Integration tests that test multiple components together
- `conftest.py`: Shared pytest fixtures and configuration
- `pytest.ini`: Configuration for pytest and TAP output

## Running Tests

To run all tests with TAP output:

```bash
python -m pytest
```

The test output will be saved in TAP format in the `test_results` directory.

## TAP Output

TAP (Test Anything Protocol) is a simple text-based interface between testing modules. It provides a standardized way to report test results that can be easily parsed by other tools.

Example TAP output:
```
TAP version 13
1..3
ok 1 - test_calculate_annualized_return
ok 2 - test_format_currency
ok 3 - test_format_percentage
```

## Continuous Integration

GitHub Actions is configured to run tests automatically on pushes to main and develop branches, as well as on pull requests to main. The workflow is defined in `.github/workflows/test_with_tap.yml`.

## Adding New Tests

1. For unit tests, add test files to `tests/unit/`.
2. For integration tests, add test files to `tests/integration/`.
3. Follow the naming convention: `test_*.py` for files, `test_*` for functions.
4. Run your tests to ensure they generate valid TAP output.

## Best Practices

1. Keep unit tests isolated - they should not depend on external services.
2. Use fixtures from `conftest.py` to share setup code.
3. For database tests, use the in-memory SQLite database.
4. Always clean up after tests to avoid affecting other tests.