#!/usr/bin/env python3

"""
Proxy server for Schwab API requests to avoid CORS issues

This module provides proxy endpoints that handle requests to Schwab API
from the server-side to avoid CORS restrictions in the browser.
"""

import os
import logging
import requests
from flask import Blueprint, request, jsonify, current_app

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

schwab_proxy = Blueprint('schwab_proxy', __name__)

@schwab_proxy.route('/proxy/oauth/authorize', methods=['GET'])
def proxy_oauth_authorize():
    """Proxy for Schwab API OAuth authorization endpoint"""
    # Get query parameters from the original request
    params = request.args.to_dict()
    
    # Determine if we're using sandbox or production based on settings
    is_sandbox = current_app.config.get('USE_SANDBOX', False)
    
    # Construct the appropriate base URL
    if is_sandbox:
        base_url = "https://sandbox.schwabapi.com/v1/oauth/authorize"
    else:
        base_url = "https://api.schwabapi.com/v1/oauth/authorize"
    
    logger.info(f"Proxying OAuth authorize request to {base_url}")
    
    try:
        # Forward the request to Schwab API
        response = requests.get(
            base_url,
            params=params,
            headers={
                "User-Agent": "TradingBot OAuth Proxy"
            },
            allow_redirects=False  # Don't follow redirects, let the client handle them
        )
        
        logger.info(f"Proxy response status: {response.status_code}")
        
        # If there's a redirect, we need to pass it back to the client
        if response.status_code in (301, 302, 303, 307, 308):
            redirect_url = response.headers.get('Location')
            logger.info(f"Received redirect to: {redirect_url}")
            
            # Return a JSON response with the redirect URL
            return jsonify({
                "status": "redirect",
                "redirect_url": redirect_url
            })
        
        # For other responses, pass through status code and content
        return (
            response.content,
            response.status_code,
            {'Content-Type': response.headers.get('Content-Type', 'text/html')}
        )
        
    except requests.RequestException as e:
        logger.error(f"Error proxying request: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Proxy error: {str(e)}"
        }), 500

@schwab_proxy.route('/proxy/oauth/token', methods=['POST'])
def proxy_oauth_token():
    """Proxy for Schwab API OAuth token endpoint"""
    # Get form data from the original request
    data = request.form.to_dict()
    
    # Determine if we're using sandbox or production based on settings
    is_sandbox = current_app.config.get('USE_SANDBOX', False)
    
    # Construct the appropriate base URL
    if is_sandbox:
        base_url = "https://sandbox.schwabapi.com/v1/oauth/token"
    else:
        base_url = "https://api.schwabapi.com/v1/oauth/token"
    
    logger.info(f"Proxying OAuth token request to {base_url}")
    
    try:
        # Forward the request to Schwab API
        response = requests.post(
            base_url,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": "TradingBot OAuth Proxy"
            }
        )
        
        logger.info(f"Proxy response status: {response.status_code}")
        
        # Parse response as JSON
        try:
            response_data = response.json()
        except ValueError:
            response_data = {"raw_content": response.text}
        
        # Return the response with the same status code
        return jsonify(response_data), response.status_code
        
    except requests.RequestException as e:
        logger.error(f"Error proxying token request: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Proxy error: {str(e)}"
        }), 500

@schwab_proxy.route('/proxy/gateway/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_gateway(subpath):
    """General proxy for Schwab gateway requests"""
    # Get query parameters and headers from the original request
    params = request.args.to_dict()
    headers = {key: value for key, value in request.headers.items() 
               if key.lower() not in ('host', 'content-length')}
    
    # Add custom user agent
    headers['User-Agent'] = "TradingBot Gateway Proxy"
    
    # Construct the full URL for the gateway
    gateway_url = f"https://sws-gateway.schwab.com/{subpath}"
    
    logger.info(f"Proxying {request.method} request to {gateway_url}")
    
    try:
        # Forward the request with the appropriate method
        if request.method == 'GET':
            response = requests.get(gateway_url, params=params, headers=headers)
        elif request.method == 'POST':
            response = requests.post(gateway_url, params=params, data=request.get_data(), headers=headers)
        elif request.method == 'PUT':
            response = requests.put(gateway_url, params=params, data=request.get_data(), headers=headers)
        elif request.method == 'DELETE':
            response = requests.delete(gateway_url, params=params, headers=headers)
        else:
            return jsonify({"error": "Method not supported"}), 405
        
        logger.info(f"Proxy gateway response status: {response.status_code}")
        
        # Try to parse as JSON, but fall back to raw content if needed
        try:
            response_data = response.json()
            return jsonify(response_data), response.status_code
        except ValueError:
            # Return raw response content
            return (
                response.content,
                response.status_code,
                {'Content-Type': response.headers.get('Content-Type', 'text/plain')}
            )
            
    except requests.RequestException as e:
        logger.error(f"Error proxying gateway request: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Proxy error: {str(e)}"
        }), 500
