# TAP Test Results

This directory contains Test Anything Protocol (TAP) formatted test results for the trading bot application.

## Understanding TAP Output

TAP (Test Anything Protocol) is a simple text-based interface between testing modules. It provides a standardized way to report test results that can be easily parsed by other tools.

### Format Example

```
TAP version 13
1..3
ok 1 - First test passed
not ok 2 - Second test failed
# Detailed diagnostics for the failure
ok 3 - Third test passed
```

### Key Components

- **Version Header**: `TAP version 13` indicates the TAP protocol version
- **Plan Line**: `1..N` where N is the total number of tests
- **Test Result Lines**: Starting with `ok` or `not ok` followed by a test number and description
- **Diagnostics**: Lines starting with `#` providing additional information about test results
- **YAML Blocks**: Some TAP implementations include YAML blocks for structured diagnostics

## Files in This Directory

- `testresults.tap`: Combined TAP output from all tests
- `tap-*.tap`: Individual test files for specific test modules

## Using TAP Results

TAP output can be used with various TAP consumers and test harnesses, including:

- Jenkins TAP Plugin
- GitHub Actions TAP reporting
- Various TAP formatters and pretty-printers

## Troubleshooting Test Failures

When a test fails in TAP output (`not ok` line), check the following:

1. Look for diagnostic messages after the failure (lines starting with `#`)
2. Check the original test file referenced in the TAP output
3. Run the specific test with more detailed output: `python -m pytest <specific_test> -v`

## Generating TAP Reports

To generate fresh TAP reports, run:

```bash
python -m pytest --tap-files --tap-combined --tap-outdir=test_results
```