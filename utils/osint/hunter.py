#!/usr/bin/env python3
"""
Hunter.io Integration
Email and domain reconnaissance via Hunter.io API
"""

import json
import ssl
import urllib.request
from typing import Dict, List, Optional


class HunterClient:
    """Hunter.io API client"""
    
    BASE_URL = 'https://api.hunter.io/v2'
    
    def __init__(self, api_key: str, timeout: float = 30.0):
        self.api_key = api_key
        self.timeout = timeout
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
    
    def _request(self, endpoint: str, params: Dict = None) -> Dict:
        url = f"{self.BASE_URL}{endpoint}?api_key={self.api_key}"
        if params:
            for k, v in params.items():
                url += f"&{k}={urllib.parse.quote(str(v))}"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'IronCarrier/2.0'})
        with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
            return json.loads(resp.read().decode())
    
    def domain_search(self, domain: str, limit: int = 100) -> Optional[Dict]:
        """Search emails for domain"""
        try:
            return self._request('/domain-search', {'domain': domain, 'limit': limit})
        except Exception as e:
            return {'error': str(e)}
    
    def email_finder(self, domain: str, first_name: str = None, last_name: str = None) -> Optional[Dict]:
        """Find specific email"""
        params = {'domain': domain}
        if first_name:
            params['first_name'] = first_name
        if last_name:
            params['last_name'] = last_name
        try:
            return self._request('/email-finder', params)
        except Exception as e:
            return {'error': str(e)}
    
    def email_verifier(self, email: str) -> Optional[Dict]:
        """Verify email address"""
        try:
            return self._request('/email-verifier', {'email': email})
        except Exception as e:
            return {'error': str(e)}
    
    def get_emails(self, domain: str) -> List[str]:
        """Get all emails for domain"""
        result = self.domain_search(domain)
        if 'error' in result:
            return []
        emails = []
        for entry in result.get('data', {}).get('emails', []):
            emails.append(entry.get('value', ''))
        return emails
    
    def get_department_emails(self, domain: str) -> Dict[str, List[str]]:
        """Group emails by department"""
        result = self.domain_search(domain)
        departments = {}
        for entry in result.get('data', {}).get('emails', []):
            dept = entry.get('department', 'general') or 'general'
            email = entry.get('value', '')
            if email:
                if dept not in departments:
                    departments[dept] = []
                departments[dept].append(email)
        return departments
