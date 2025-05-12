#!/usr/bin/env python3
"""
Run TAP-formatted tests for the trading bot application.

This script runs pytest with TAP output formatting and saves the results
to the test_results directory.

Usage:
    python run_tap_tests.py [--unit] [--integration] [--all]

Options:
    --unit          Run only unit tests
    --integration   Run only integration tests
    --all           Run all tests (default)

Example:
    python run_tap_tests.py --unit
"""

import os
import sys
import subprocess
import argparse


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run TAP-formatted tests for the trading bot application."
    )
    parser.add_argument(
        "--unit", action="store_true", help="Run only unit tests"
    )
    parser.add_argument(
        "--integration", action="store_true", help="Run only integration tests"
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all tests (default)"
    )
    
    args = parser.parse_args()
    
    # If no options are specified, run all tests
    if not (args.unit or args.integration or args.all):
        args.all = True
        
    return args


def run_tests(test_path="tests/"):
    """Run pytest with TAP output."""
    # Create test_results directory if it doesn't exist
    os.makedirs("test_results", exist_ok=True)
    
    cmd = [
        "python", "-m", "pytest",
        test_path,
        "--tap-files",
        "--tap-combined",
        "--tap-outdir=test_results"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode


def main():
    """Main function."""
    args = parse_args()
    
    if args.unit:
        print("Running unit tests...")
        return run_tests("tests/unit/")
    elif args.integration:
        print("Running integration tests...")
        return run_tests("tests/integration/")
    else:  # args.all
        print("Running all tests...")
        return run_tests()


if __name__ == "__main__":
    sys.exit(main())