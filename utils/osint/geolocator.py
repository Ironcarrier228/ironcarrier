#!/usr/bin/env python3
"""
Geolocator
IP geolocation using free APIs
"""

import json
import ssl
import urllib.request
import threading
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor


class Geolocator:
    """IP geolocation via multiple free APIs"""
    
    APIS = [
        'http://ip-api.com/json/{ip}?fields=status,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query',
        'https://ipapi.co/{ip}/json/',
    ]
    
    def __init__(self, timeout: float = 10.0, threads: int = 20):
        self.timeout = timeout
        self.threads = threads
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
    
    def lookup(self, ip: str) -> Optional[Dict]:
        """Geolocate single IP"""
        for api in self.APIS:
            try:
                url = api.format(ip=ip)
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
                    data = json.loads(resp.read().decode())
                    if data.get('status') == 'fail':
                        continue
                    return {
                        'ip': data.get('query', data.get('ip', ip)),
                        'country': data.get('country', 'Unknown'),
                        'country_code': data.get('countryCode', data.get('country_code', '??')),
                        'region': data.get('regionName', data.get('region', 'Unknown')),
                        'city': data.get('city', 'Unknown'),
                        'zip': data.get('zip', ''),
                        'lat': data.get('lat', 0),
                        'lon': data.get('lon', 0),
                        'timezone': data.get('timezone', 'Unknown'),
                        'isp': data.get('isp', 'Unknown'),
                        'org': data.get('org', 'Unknown'),
                        'as': data.get('as', 'Unknown'),
                    }
            except Exception:
                continue
        return None
    
    def batch_lookup(self, ips: List[str]) -> Dict[str, Dict]:
        """Geolocate multiple IPs"""
        results = {}
        def _lookup(ip):
            data = self.lookup(ip)
            if data:
                results[ip] = data
        
        with ThreadPoolExecutor(max_workers=self.threads) as pool:
            list(pool.map(_lookup, ips))
        return results
    
    def my_ip(self) -> Optional[str]:
        """Get current public IP"""
        try:
            url = 'https://api.ipify.org?format=json'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
                data = json.loads(resp.read().decode())
                return data.get('ip')
        except Exception:
            try:
                url = 'https://ifconfig.me/ip'
                req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.0'})
                with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
                    return resp.read().decode().strip()
            except Exception:
                return None
    
    def print_result(self, data: Dict) -> None:
        """Print formatted geolocation"""
        print(f"""
  IP:          {data.get('ip', 'N/A')}
  Location:    {data.get('city', 'N/A')}, {data.get('region', 'N/A')}, {data.get('country', 'N/A')} [{data.get('country_code', '??')}]
  Coordinates: {data.get('lat', 0)}, {data.get('lon', 0)}
  ISP:         {data.get('isp', 'N/A')}
  Organization:{data.get('org', 'N/A')}
  AS:          {data.get('as', 'N/A')}
  Timezone:    {data.get('timezone', 'N/A')}
  Zip:         {data.get('zip', 'N/A')}
""")
