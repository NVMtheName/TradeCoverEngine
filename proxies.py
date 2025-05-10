import os
import urllib.parse
from requests.auth import HTTPBasicAuth

def get_proxy_session():
    """Create a requests session configured to use the QuotaGuard Static proxy"""
    import requests
    
    session = requests.Session()
    
    # Check if QUOTAGUARDSTATIC_URL is set
    quotaguardstatic_url = os.environ.get('QUOTAGUARDSTATIC_URL')
    if quotaguardstatic_url:
        url = urllib.parse.urlparse(quotaguardstatic_url)
        
        # Configure proxy settings
        proxy_url = f"{url.scheme}://{url.netloc}"
        
        session.proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # Add proxy authentication if username and password are available
        if url.username and url.password:
            session.auth = HTTPBasicAuth(url.username, url.password)
        
    return session