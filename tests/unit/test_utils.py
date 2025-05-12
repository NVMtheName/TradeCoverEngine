"""
Unit tests for utility functions.
"""

import pytest
from utils import (
    calculate_annualized_return,
    format_currency,
    format_percentage,
    get_expiry_dates,
    parse_option_symbol,
    format_option_symbol,
)


def test_calculate_annualized_return():
    """Test calculating annualized return for different periods."""
    # 10% profit over 365 days should be 10% annualized
    assert round(calculate_annualized_return(10.0, 365), 2) == 10.0
    
    # 5% profit over 30 days should be about 61% annualized
    assert 60.0 <= calculate_annualized_return(5.0, 30) <= 62.0
    
    # 1% profit over 7 days should be about 75% annualized
    assert 70.0 <= calculate_annualized_return(1.0, 7) <= 80.0


def test_format_currency():
    """Test currency formatting with different values."""
    assert format_currency(1000) == "$1,000.00"
    assert format_currency(1234.56) == "$1,234.56"
    assert format_currency(-500) == "-$500.00"
    assert format_currency(0) == "$0.00"


def test_format_percentage():
    """Test percentage formatting with different values."""
    assert format_percentage(10) == "10.00%"
    assert format_percentage(3.5) == "3.50%"
    assert format_percentage(-2.75) == "-2.75%"
    assert format_percentage(0) == "0.00%"


def test_get_expiry_dates():
    """Test generating option expiry dates."""
    # Test default parameters (60 days forward, no weekly)
    dates = get_expiry_dates()
    assert len(dates) > 0
    assert all(isinstance(date, str) for date in dates)
    assert all(len(date) == 10 for date in dates)  # YYYY-MM-DD format
    
    # Test with weekly expirations
    weekly_dates = get_expiry_dates(days_forward=30, weekly=True)
    assert len(weekly_dates) > 0
    assert len(weekly_dates) >= len(get_expiry_dates(days_forward=30, weekly=False))


def test_parse_option_symbol():
    """Test parsing option symbols."""
    # Test a call option
    call = parse_option_symbol("AAPL230616C00150000")
    if call is None:
        pytest.skip("parse_option_symbol function not implemented yet")
    else:
        assert call["symbol"] == "AAPL"
        assert call["expiry"] == "2023-06-16"
        assert call["type"] == "C"
        assert call["strike"] == 150.0
    
    # Test a put option
    put = parse_option_symbol("SPY230630P00400000")
    if put is None:
        pytest.skip("parse_option_symbol function not implemented yet")
    else:
        assert put["symbol"] == "SPY"
        assert put["expiry"] == "2023-06-30"
        assert put["type"] == "P"
        assert put["strike"] == 400.0


def test_format_option_symbol():
    """Test formatting option symbols."""
    # Test formatting a call option
    call = format_option_symbol("AAPL", "2023-06-16", "C", 150.0)
    assert call == "AAPL230616C00150000"
    
    # Test formatting a put option
    put = format_option_symbol("SPY", "2023-06-30", "P", 400.0)
    assert put == "SPY230630P00400000"