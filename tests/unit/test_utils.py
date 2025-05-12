import os
import sys
import unittest

# Add parent directory to path to import modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from utils import (
    calculate_annualized_return,
    format_currency,
    format_percentage,
    format_option_symbol,
    parse_option_symbol
)


class TestUtils(unittest.TestCase):

    def test_calculate_annualized_return(self):
        """Test calculation of annualized returns"""
        # Test with different scenarios
        self.assertAlmostEqual(calculate_annualized_return(5.0, 30), 60.83, delta=0.1)
        self.assertAlmostEqual(calculate_annualized_return(10.0, 365), 10.0, delta=0.1)
        self.assertAlmostEqual(calculate_annualized_return(2.5, 90), 10.14, delta=0.1)
        
        # Edge cases
        self.assertAlmostEqual(calculate_annualized_return(0, 30), 0.0)
        self.assertEqual(calculate_annualized_return(5.0, 0), 0.0)  # Handle division by zero
    
    def test_format_currency(self):
        """Test currency formatting function"""
        self.assertEqual(format_currency(1234.5678), "$1,234.57")
        self.assertEqual(format_currency(0), "$0.00")
        self.assertEqual(format_currency(-1234.56), "$-1,234.56")  # Current implementation formats negative values this way
    
    def test_format_percentage(self):
        """Test percentage formatting function"""
        self.assertEqual(format_percentage(12.345), "12.35%")
        self.assertEqual(format_percentage(0), "0.00%")
        self.assertEqual(format_percentage(-5.67), "-5.67%")
    
    def test_option_symbol_formatting(self):
        """Test OCC option symbol formatting"""
        # Standard case - note the implementation uses a 6-character padded symbol
        self.assertEqual(
            format_option_symbol("AAPL", "2023-06-16", "C", 150.0),
            "AAPL  230616C00150000"
        )
        
        # Put option
        self.assertEqual(
            format_option_symbol("SPY", "2023-12-15", "P", 400.0),
            "SPY   231215P00400000"
        )
        
        # Stock symbol with different lengths
        self.assertEqual(
            format_option_symbol("F", "2024-01-19", "C", 15.0),
            "F     240119C00015000"
        )
    
    def test_parse_option_symbol(self):
        """Test parsing OCC option symbols"""
        # Standard call option
        result = parse_option_symbol("AAPL230616C00150000")
        self.assertEqual(result["symbol"], "AAPL")
        self.assertEqual(result["expiry"], "2023-06-16")
        self.assertEqual(result["option_type"], "call")
        self.assertEqual(result["strike"], 150.0)
        
        # Put option
        result = parse_option_symbol("SPY231215P00400000")
        self.assertEqual(result["symbol"], "SPY")
        self.assertEqual(result["expiry"], "2023-12-15")
        self.assertEqual(result["option_type"], "put")
        self.assertEqual(result["strike"], 400.0)
        
        # Single-letter stock symbol
        result = parse_option_symbol("F240119C00015000")
        self.assertEqual(result["symbol"], "F")
        self.assertEqual(result["expiry"], "2024-01-19")
        self.assertEqual(result["option_type"], "call")
        self.assertEqual(result["strike"], 15.0)


if __name__ == '__main__':
    unittest.main()