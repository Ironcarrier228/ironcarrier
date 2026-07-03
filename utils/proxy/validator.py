#!/usr/bin/env python3
"""
Proxy Validator
Test proxy connectivity and anonymity level
"""

import socket
import ssl
import threading
import time
import urllib.request
import re
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from .manager import Proxy, ProxyManager, ProxyStatus, ProxyType


class ProxyValidator:
    """Validate and test proxies"""
    
    TEST_URL = 'http://httpbin.org/ip'
    ANON_CHECK_URL = 'http://httpbin.org/headers'
    
    def __init__(self, timeout: float = 10.0, threads: int = 200):
        self.timeout = timeout
        self.threads = threads
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
    
    def _test_http(self, proxy: Proxy) -> Tuple[bool, float, str]:
        """Test HTTP/HTTPS proxy"""
        start = time.time()
        
        try:
            handler = urllib.request.HTTPHandler()
            if proxy.proxy_type == ProxyType.HTTPS:
                handler = urllib.request.HTTPSHandler(context=self._ctx)
            
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({'http': proxy.url, 'https': proxy.url}),
                handler
            )
            
            req = urllib.request.Request(self.TEST_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with opener.open(req, timeout=self.timeout) as resp:
                resp.read()
                latency = time.time() - start
                return True, latency, ''
        except urllib.error.HTTPError as e:
            return False, 0, f'HTTP {e.code}'
        except Exception as e:
            return False, 0, str(e)[:50]
    
    def _test_socks(self, proxy: Proxy) -> Tuple[bool, float, str]:
        """Test SOCKS proxy"""
        start = time.time()
        
        try:
            from .socks import socks_connect
            
            sock = socks_connect(
                proxy.address, proxy.port,
                'httpbin.org', 80,
                socks_version=5 if proxy.proxy_type == ProxyType.SOCKS5 else 4,
                timeout=self.timeout
            )
            
            request = f"GET /ip HTTP/1.0\r\nHost: httpbin.org\r\n\r\n"
            sock.sendall(request.encode())
            response = sock.recv(4096)
            sock.close()
            
            latency = time.time() - start
            return True, latency, ''
        except Exception as e:
            return False, 0, str(e)[:50]
    
    def _test_connectivity(self, proxy: Proxy) -> Tuple[bool, float, str]:
        """Test basic TCP connectivity"""
        start = time.time()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((proxy.address, proxy.port))
            latency = time.time() - start
            sock.close()
            return True, latency, ''
        except Exception as e:
            return False, 0, str(e)[:50]
    
    def _check_anonymity(self, proxy: Proxy) -> str:
        """Check proxy anonymity level"""
        try:
            handler = urllib.request.HTTPHandler()
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({'http': proxy.url, 'https': proxy.url}),
                handler
            )
            
            req = urllib.request.Request(self.ANON_CHECK_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with opener.open(req, timeout=self.timeout) as resp:
                data = resp.read().decode()
                
                has_xff = 'X-Forwarded-For' in data
                has_via = 'Via:' in data
                has_real_ip = 'X-Real-Ip' in data
                
                if not has_xff and not has_via and not has_real_ip:
                    return 'elite'
                elif has_xff or has_via:
                    return 'anonymous'
                return 'transparent'
        except Exception:
            return ''
    
    def validate(self, proxy: Proxy, check_anonymity: bool = False) -> Dict:
        """Validate single proxy"""
        result = {
            'address': proxy.address,
            'port': proxy.port,
            'alive': False,
            'latency': 0,
            'error': '',
            'anonymity': '',
        }
        
        if proxy.proxy_type in [ProxyType.HTTP, ProxyType.HTTPS]:
            alive, latency, error = self._test_http(proxy)
        elif proxy.proxy_type in [ProxyType.SOCKS4, ProxyType.SOCKS5]:
            alive, latency, error = self._test_socks(proxy)
        else:
            alive, latency, error = self._test_connectivity(proxy)
        
        result['alive'] = alive
        result['latency'] = latency
        result['error'] = error
        
        if alive and check_anonymity:
            result['anonymity'] = self._check_anonymity(proxy)
        
        return result
    
    def validate_all(self, manager: ProxyManager, check_anonymity: bool = False,
                      callback=None) -> List[Dict]:
        """Validate all proxies in manager"""
        proxies = manager.get_all()
        results = []
        
        def _validate(proxy):
            result = self.validate(proxy, check_anonymity)
            if callback:
                callback(proxy, result)
            return result
        
        with ThreadPoolExecutor(max_workers=self.threads) as pool:
            results = list(pool.map(_validate, proxies))
        
        # Update manager with results
        for result in results:
            if result['alive']:
                manager.update_proxy(
                    result['address'], result['port'],
                    status=ProxyStatus.ALIVE,
                    latency=result['latency'],
                    anonymity=result['anonymity'],
                    last_check=time.time(),
                )
            else:
                manager.mark_dead(result['address'], result['port'])
        
        return results
    
    def validate_list(self, proxies: List[Proxy], check_anonymity: bool = False) -> List[Dict]:
        """Validate list of proxies"""
        with ThreadPoolExecutor(max_workers=self.threads) as pool:
            return list(pool.map(lambda p: self.validate(p, check_anonymity), proxies))
    
    def filter_working(self, proxies: List[Proxy], max_latency: float = 5.0) -> List[Proxy]:
        """Filter to working proxies under latency threshold"""
        return [p for p in proxies if p.status == ProxyStatus.ALIVE and p.latency <= max_latency]
