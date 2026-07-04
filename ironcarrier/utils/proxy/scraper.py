#!/usr/bin/env python3
"""
Proxy Scraper
Scrape free proxies from public sources
"""

import re
import ssl
import json
import urllib.request
import threading
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from .manager import Proxy, ProxyType


class ProxyScraper:
    """Scrape free proxies from multiple sources"""
    
    SOURCES = [
        {
            'name': 'free-proxy-list',
            'url': 'https://free-proxy-list.net/',
            'type': ProxyType.HTTP,
            'pattern': r'<tr><td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td><td>(\d+)</td><td>(\w+)</td>',
        },
        {
            'name': 'geonode',
            'url': 'https://geonode.com/free-proxy-list',
            'type': ProxyType.HTTP,
            'pattern': r'"proxy":"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)"',
        },
        {
            'name': 'proxyscrape',
            'url': 'https://proxyscrape.com/?requesttype=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all',
            'type': ProxyType.HTTP,
            'pattern': r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>\s*<td>(\d+)</td>',
        },
        {
            'name': 'sslproxies',
            'url': 'https://sslproxies.org/',
            'type': ProxyType.HTTPS,
            'pattern': r'<tr><td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td><td>(\d+)</td>',
        },
        {
            'name': 'socks-proxy',
            'url': 'https://www.socks-proxy.net/',
            'type': ProxyType.SOCKS5,
            'pattern': r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td><td>(\d+)</td>',
        },
        {
            'name': 'sockslist',
            'url': 'https://www.sockslist.net/',
            'type': ProxyType.SOCKS5,
            'pattern': r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td><td>(\d+)</td>',
        },
        {
            'name': 'api-pxapi',
            'url': 'https://pxapi.ru/api/?type=http&limit=100',
            'type': ProxyType.HTTP,
            'api': True,
        },
        {
            'name': 'api-github',
            'url': 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
            'type': ProxyType.HTTP,
            'plain': True,
        },
        {
            'name': 'api-github-socks5',
            'url': 'https://raw.githubusercontent.com/TheSpeedX/SOCKS5-List/master/socks5.txt',
            'type': ProxyType.SOCKS5,
            'plain': True,
        },
    ]
    
    def __init__(self, timeout: float = 15.0, threads: int = 10):
        self.timeout = timeout
        self.threads = threads
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
    
    def _fetch(self, source: dict) -> List[Tuple[str, int]]:
        """Fetch and parse proxies from source"""
        proxies = []
        
        try:
            req = urllib.request.Request(
                source['url'],
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
                data = resp.read().decode('utf-8', errors='ignore')
            
            if source.get('plain'):
                for line in data.split('\n'):
                    line = line.strip()
                    if ':' in line:
                        parts = line.split(':')
                        try:
                            proxies.append((parts[0], int(parts[1])))
                        except ValueError:
                            continue
            elif source.get('api'):
                try:
                    json_data = json.loads(data)
                    for item in json_data.get('data', json_data if isinstance(json_data, list) else []):
                        if isinstance(item, dict):
                            ip = item.get('ip', item.get('host', ''))
                            port = item.get('port', 0)
                            if ip and port:
                                proxies.append((ip, int(port)))
                except json.JSONDecodeError:
                    pass
            else:
                matches = re.findall(source['pattern'], data)
                for match in matches:
                    ip = match[0]
                    port = int(match[1])
                    proxies.append((ip, port))
        
        except Exception:
            pass
        
        return proxies
    
    def scrape(self, sources: List[dict] = None, callback=None) -> List[Tuple[str, int, str]]:
        """Scrape proxies from all or specified sources"""
        sources = sources or self.SOURCES
        results = []
        
        def _scrape_source(source):
            name = source.get('name', 'unknown')
            proxy_type = source.get('type', ProxyType.HTTP)
            found = self._fetch(source)
            
            if callback:
                callback(name, len(found))
            
            return [(ip, port, proxy_type.value) for ip, port in found]
        
        with ThreadPoolExecutor(max_workers=self.threads) as pool:
            futures = [pool.submit(_scrape_source, s) for s in sources]
            for future in futures:
                try:
                    results.extend(future.result())
                except Exception:
                    pass
        
        return results
    
    def scrape_to_manager(self, manager, sources: List[dict] = None) -> int:
        """Scrape and add directly to manager"""
        results = self.scrape(sources)
        count = 0
        for address, port, ptype in results:
            proxy = Proxy(
                address=address,
                port=port,
                proxy_type=ProxyType(ptype)
            )
            manager.add(proxy)
            count += 1
        return count
    
    def list_sources(self) -> List[Dict]:
        """List available sources"""
        return [{'name': s['name'], 'type': s['type'].value, 'url': s['url']} for s in self.SOURCES]
