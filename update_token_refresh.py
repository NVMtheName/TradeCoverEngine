#!/usr/bin/env python3
"""
Script to update token refresh methods in api_connector.py
Replaces TD Ameritrade specific refresh methods with the standardized approach
"""

import re

# Path to the API connector file
api_connector_path = 'trading_bot/api_connector.py'

# Read the file
with open(api_connector_path, 'r') as f:
    content = f.read()

# Pattern to match the TD Ameritrade refresh token checks
pattern = r'# Handle the case where _refresh_td_ameritrade_token may not exist\s+refresh_method = getattr\(self, \'_refresh_td_ameritrade_token\', None\)'

# Updated content with standardized approach
updated_content = re.sub(pattern, '# Use standardized refresh access token method', content)

# Write the updated content back
with open(api_connector_path, 'w') as f:
    f.write(updated_content)

print("Successfully updated token refresh methods in api_connector.py")
