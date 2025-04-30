"""
Utility functions for the trading bot application.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os
import requests
from flask import flash

# Configure logger
logger = logging.getLogger(__name__)

def calculate_annualized_return(profit_percentage, days):
    """
    Calculate annualized return from a profit percentage and holding period.
    
    Args:
        profit_percentage (float): Profit percentage (e.g., 5.0 for 5%)
        days (int): Number of days in holding period
        
    Returns:
        float: Annualized return percentage
    """
    if days <= 0:
        return 0
    
    annual_factor = 365.0 / days
    return profit_percentage * annual_factor

def format_currency(value):
    """
    Format a number as a currency string.
    
    Args:
        value (float): The number to format
        
    Returns:
        str: Formatted currency string
    """
    if value is None:
        return "$0.00"
        
    return "${:,.2f}".format(value)

def format_percentage(value):
    """
    Format a number as a percentage string.
    
    Args:
        value (float): The number to format
        
    Returns:
        str: Formatted percentage string
    """
    if value is None:
        return "0.00%"
        
    return "{:.2f}%".format(value)

def get_expiry_dates(days_forward=60, weekly=False):
    """
    Generate a list of option expiry dates from today.
    
    Args:
        days_forward (int): Number of days to look forward
        weekly (bool): Whether to include weekly expirations
        
    Returns:
        list: List of expiry dates as strings (YYYY-MM-DD)
    """
    today = datetime.now()
    end_date = today + timedelta(days=days_forward)
    
    # Options typically expire on the third Friday of each month
    dates = []
    current_date = today
    
    while current_date <= end_date:
        # If it's a Friday
        if current_date.weekday() == 4:
            # For monthly options, we want the 3rd Friday
            week_number = (current_date.day - 1) // 7 + 1
            
            if week_number == 3 or (weekly and week_number != 3):
                dates.append(current_date.strftime('%Y-%m-%d'))
        
        current_date += timedelta(days=1)
    
    return dates

def calculate_position_metrics(position):
    """
    Calculate metrics for a trading position.
    
    Args:
        position (dict): Position details
        
    Returns:
        dict: Updated position with calculated metrics
    """
    # Create a copy to avoid modifying the original
    result = position.copy()
    
    if 'current_price' in position and 'avg_entry_price' in position:
        # Calculate unrealized profit/loss
        result['unrealized_pl'] = (position['current_price'] - position['avg_entry_price']) * position.get('quantity', 0)
        
        # Calculate percentage return
        if position['avg_entry_price'] > 0:
            result['unrealized_plpc'] = (position['current_price'] / position['avg_entry_price'] - 1) * 100
        else:
            result['unrealized_plpc'] = 0
    
    # Calculate market value
    if 'current_price' in position and 'quantity' in position:
        result['market_value'] = position['current_price'] * position['quantity']
    
    # Option-specific calculations
    if 'option_premium' in position and 'avg_entry_price' in position:
        # Calculate premium as percentage of stock price
        result['premium_percentage'] = (position['option_premium'] / position['avg_entry_price']) * 100
        
        # Calculate return if assigned
        if 'option_strike' in position:
            result['return_if_assigned'] = ((position['option_strike'] - position['avg_entry_price'] + position['option_premium']) / 
                                           position['avg_entry_price']) * 100
    
    return result

def calculate_options_metrics(stock_price, options_data):
    """
    Calculate additional metrics for options data.
    
    Args:
        stock_price (float): Current stock price
        options_data (dict): Options chain data
        
    Returns:
        dict: Options data with additional metrics
    """
    result = {
        'calls': [],
        'puts': []
    }
    
    # Process call options
    for call in options_data.get('calls', []):
        call_copy = call.copy()
        
        # Calculate additional metrics if we have the necessary data
        if 'strike' in call and 'premium' in call and 'days_to_expiry' in call:
            # Out-of-the-money percentage
            call_copy['otm_percent'] = ((call['strike'] - stock_price) / stock_price) * 100
            
            # Premium as percentage of stock price
            call_copy['premium_percent'] = (call['premium'] / stock_price) * 100
            
            # Potential return if assigned (for covered calls)
            call_copy['return_if_assigned'] = ((call['strike'] - stock_price + call['premium']) / stock_price) * 100
            
            # Annualized return if assigned
            call_copy['annualized_return'] = calculate_annualized_return(call_copy['return_if_assigned'], call['days_to_expiry'])
            
            # Break-even price
            call_copy['break_even'] = stock_price - call['premium']
        
        result['calls'].append(call_copy)
    
    # Process put options
    for put in options_data.get('puts', []):
        put_copy = put.copy()
        
        # Calculate additional metrics if we have the necessary data
        if 'strike' in put and 'premium' in put and 'days_to_expiry' in put:
            # Out-of-the-money percentage
            put_copy['otm_percent'] = ((stock_price - put['strike']) / stock_price) * 100
            
            # Premium as percentage of stock price
            put_copy['premium_percent'] = (put['premium'] / stock_price) * 100
            
            # Potential return if assigned (for cash-secured puts)
            put_copy['return_if_assigned'] = (put['premium'] / put['strike']) * 100
            
            # Annualized return if assigned
            put_copy['annualized_return'] = calculate_annualized_return(put_copy['return_if_assigned'], put['days_to_expiry'])
            
            # Break-even price
            put_copy['break_even'] = put['strike'] - put['premium']
        
        result['puts'].append(put_copy)
    
    # Sort options by strike price
    result['calls'].sort(key=lambda x: x.get('strike', 0))
    result['puts'].sort(key=lambda x: x.get('strike', 0), reverse=True)
    
    return result

def filter_options_by_criteria(options_data, criteria):
    """
    Filter options based on given criteria.
    
    Args:
        options_data (dict): Options chain data
        criteria (dict): Filtering criteria
        
    Returns:
        dict: Filtered options data
    """
    result = {
        'calls': [],
        'puts': []
    }
    
    # Filter call options
    for call in options_data.get('calls', []):
        if all([
            call.get('days_to_expiry', 0) >= criteria.get('min_days', 0),
            call.get('days_to_expiry', float('inf')) <= criteria.get('max_days', float('inf')),
            call.get('otm_percent', 0) >= criteria.get('min_otm_percent', 0),
            call.get('otm_percent', float('inf')) <= criteria.get('max_otm_percent', float('inf')),
            call.get('premium_percent', 0) >= criteria.get('min_premium_percent', 0),
            call.get('delta', 1) <= criteria.get('max_delta', 1)
        ]):
            result['calls'].append(call)
    
    # Filter put options
    for put in options_data.get('puts', []):
        if all([
            put.get('days_to_expiry', 0) >= criteria.get('min_days', 0),
            put.get('days_to_expiry', float('inf')) <= criteria.get('max_days', float('inf')),
            put.get('otm_percent', 0) >= criteria.get('min_otm_percent', 0),
            put.get('otm_percent', float('inf')) <= criteria.get('max_otm_percent', float('inf')),
            put.get('premium_percent', 0) >= criteria.get('min_premium_percent', 0),
            put.get('delta', 1) <= criteria.get('max_delta', 1)
        ]):
            result['puts'].append(put)
    
    return result

def safe_request(method, url, **kwargs):
    """
    Make a safe HTTP request with error handling.
    
    Args:
        method (str): HTTP method (GET, POST, etc.)
        url (str): URL to request
        **kwargs: Additional arguments for requests
        
    Returns:
        dict: Response data or error information
    """
    try:
        # Add a default timeout if not specified
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 10
            
        response = requests.request(method, url, **kwargs)
        
        # Check if the request was successful
        if response.status_code in (200, 201):
            # Try to parse JSON response
            try:
                return {
                    'success': True,
                    'data': response.json(),
                    'status_code': response.status_code
                }
            except ValueError:
                # Not JSON data
                return {
                    'success': True,
                    'data': response.text,
                    'status_code': response.status_code
                }
        else:
            # Request failed
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {response.reason}",
                'status_code': response.status_code,
                'data': response.text
            }
    
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': "Request timed out",
            'status_code': None
        }
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'error': "Connection error",
            'status_code': None
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'status_code': None
        }

def log_trade(user_id, trade_data, db_session, Trade, commit=True):
    """
    Log a trade to the database.
    
    Args:
        user_id (int): User ID or None
        trade_data (dict): Trade details
        db_session: SQLAlchemy database session
        Trade: Trade model class
        commit (bool): Whether to commit the transaction
        
    Returns:
        Trade: Created Trade object
    """
    try:
        # Create a new Trade object
        trade = Trade(
            user_id=user_id,
            symbol=trade_data.get('symbol'),
            trade_type=trade_data.get('trade_type'),
            quantity=trade_data.get('quantity'),
            price=trade_data.get('price'),
            option_strike=trade_data.get('option_strike'),
            option_expiry=trade_data.get('option_expiry'),
            status=trade_data.get('status', 'OPEN'),
            timestamp=datetime.now(),
            profit_loss=trade_data.get('profit_loss')
        )
        
        # Add to session
        db_session.add(trade)
        
        # Commit if requested
        if commit:
            db_session.commit()
            
        logger.info(f"Trade logged: {trade.symbol} {trade.trade_type} {trade.quantity} shares")
        return trade
    
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error logging trade: {str(e)}")
        flash(f"Error logging trade: {str(e)}", "danger")
        return None

def calculate_portfolio_statistics(trades, positions):
    """
    Calculate portfolio performance statistics.
    
    Args:
        trades (list): List of trade objects
        positions (list): List of current positions
        
    Returns:
        dict: Portfolio statistics
    """
    stats = {
        'total_trades': len(trades),
        'open_positions': len(positions),
        'total_premium_collected': 0,
        'total_profit_loss': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'win_rate': 0,
        'average_return': 0,
        'total_investment': sum(p.get('market_value', 0) for p in positions),
        'current_portfolio_value': sum(p.get('market_value', 0) for p in positions)
    }
    
    # Calculate trade statistics
    closed_trades = [t for t in trades if t.status == 'CLOSED']
    covered_call_trades = [t for t in trades if t.trade_type == 'COVERED_CALL']
    
    # Premium collected
    for trade in covered_call_trades:
        # For options, premium is price * quantity / 100 (contract multiplier)
        if trade.trade_type == 'COVERED_CALL':
            stats['total_premium_collected'] += (trade.price * trade.quantity / 100)
    
    # Profit/loss statistics
    if closed_trades:
        for trade in closed_trades:
            if trade.profit_loss:
                if trade.profit_loss >= 0:
                    stats['winning_trades'] += 1
                else:
                    stats['losing_trades'] += 1
                    
                stats['total_profit_loss'] += trade.profit_loss
        
        # Calculate win rate and average return
        stats['win_rate'] = (stats['winning_trades'] / len(closed_trades)) * 100 if closed_trades else 0
        stats['average_return'] = stats['total_profit_loss'] / len(closed_trades) if closed_trades else 0
    
    return stats

def format_option_symbol(symbol, expiry_date, option_type, strike_price):
    """
    Format an option symbol according to OCC format.
    
    Args:
        symbol (str): Stock symbol
        expiry_date (str): Expiry date (YYYY-MM-DD)
        option_type (str): Option type ('C' for call, 'P' for put)
        strike_price (float): Strike price
        
    Returns:
        str: Formatted option symbol
    """
    # Convert expiry date to format YYMMDD
    expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
    expiry_formatted = expiry.strftime('%y%m%d')
    
    # Format strike price (multiply by 1000 and remove decimal)
    strike_formatted = str(int(float(strike_price) * 1000)).zfill(8)
    
    # Combine parts
    return f"{symbol.ljust(6, ' ')}{expiry_formatted}{option_type}{strike_formatted}"

def parse_option_symbol(option_symbol):
    """
    Parse an option symbol in OCC format.
    
    Args:
        option_symbol (str): OCC-formatted option symbol
        
    Returns:
        dict: Parsed option details
    """
    try:
        # Extract parts
        symbol = option_symbol[:6].strip()
        expiry_date = option_symbol[6:12]
        option_type = option_symbol[12]
        strike_price = float(option_symbol[13:]) / 1000
        
        # Convert expiry date from YYMMDD to YYYY-MM-DD
        year = int('20' + expiry_date[:2])
        month = int(expiry_date[2:4])
        day = int(expiry_date[4:6])
        expiry_formatted = f"{year}-{month:02d}-{day:02d}"
        
        return {
            'symbol': symbol,
            'expiry_date': expiry_formatted,
            'option_type': 'CALL' if option_type == 'C' else 'PUT',
            'strike_price': strike_price
        }
    except Exception as e:
        logger.error(f"Error parsing option symbol {option_symbol}: {str(e)}")
        return None
