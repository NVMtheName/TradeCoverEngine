#!/usr/bin/env python3
"""
Test runner script for Heroku CI.
This is a specialized script to ensure tests are properly detected by Heroku CI.
"""

import os
import sys
import subprocess
import argparse


def setup_environment():
    """Configure environment variables for testing."""
    # Use in-memory SQLite for tests if no DATABASE_URL is provided
    if 'DATABASE_URL' not in os.environ:
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    # Set testing environment
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TESTING'] = 'True'


def run_tests():
    """Run the test suite using pytest."""
    print("Running tests with TAP output...")
    
    # Ensure test output directory exists
    os.makedirs('test_results', exist_ok=True)
    
    # Build command with proper args
    cmd = [
        'python', '-m', 'pytest',
        'tests/',
        '--tap-files',
        '--tap-combined',
        '--tap-outdir=test_results',
        '-v'
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """Main function."""
    setup_environment()
    return run_tests()


if __name__ == "__main__":
    sys.exit(main())