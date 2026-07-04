#!/usr/bin/env python3
"""
Shodan Integration
Query Shodan API for host information
"""

import json
import ssl
import urllib.request
from typing import Dict, List, Optional


class ShodanClient:
    """Shodan API client"""
    
    BASE_URL = 'https://api.shodan.io'
    
    def __init__(self, api_key: str, timeout: float = 30.0):
        self.api_key = api_key
        self.timeout = timeout
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
    
    def _request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make API request"""
        url = f"{self.BASE_URL}{endpoint}?key={self.api_key}"
        if params:
            for k, v in params.items():
                url += f"&{k}={urllib.parse.quote(str(v))}"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'IronCarrier/2.0'})
        with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
            return json.loads(resp.read().decode())
    
    def host(self, ip: str) -> Optional[Dict]:
        """Get host information"""
        try:
            return self._request(f'/shodan/host/{ip}')
        except Exception as e:
            return {'error': str(e)}
    
    def search(self, query: str, page: int = 1, limit: int = 100) -> Optional[Dict]:
        """Search Shodan"""
        try:
            return self._request('/shodan/host/search', {'query': query, 'page': page, 'limit': limit})
        except Exception as e:
            return {'error': str(e)}
    
    def count(self, query: str) -> Optional[int]:
        """Count results for query"""
        try:
            result = self._request('/shodan/host/count', {'query': query})
            return result.get('total', 0)
        except Exception:
            return None
    
    def my_ip(self) -> Optional[str]:
        """Get your public IP from Shodan's perspective"""
        try:
            result = self._request('/tools/myip')
            return result.get('ip_str')
        except Exception:
            return None
    
    def query_search(self, query: str, max_pages: int = 5) -> List[Dict]:
        """Search and paginate through results"""
        all_results = []
        for page in range(1, max_pages + 1):
            result = self.search(query, page=page)
            if not result or 'error' in result:
                break
            matches = result.get('matches', [])
            if not matches:
                break
            all_results.extend(matches)
        return all_results
