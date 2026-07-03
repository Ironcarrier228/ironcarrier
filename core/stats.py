#!/usr/bin/env python3
"""
IronCarrier Statistics Collector
Real-time metrics, history tracking, and export
"""

import time
import threading
import sys
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from collections import deque


@dataclass
class AtomicCounter:
    """Thread-safe counter"""
    _value: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    def inc(self, n: int = 1) -> None:
        with self._lock:
            self._value += n
    
    @property
    def value(self) -> int:
        with self._lock:
            return self._value
    
    def reset(self) -> None:
        with self._lock:
            self._value = 0


class StatsCollector:
    """Real-time attack statistics with rolling window calculations"""
    
    def __init__(self, window_seconds: int = 60):
        self.packets = AtomicCounter()
        self.bytes_sent = AtomicCounter()
        self.errors = AtomicCounter()
        self.connections = AtomicCounter()
        
        self.window = window_seconds
        self._pps_history: deque = deque(maxlen=window_seconds)
        self._bps_history: deque = deque(maxlen=window_seconds)
        
        self._prev_packets = 0
        self._prev_bytes = 0
        self._prev_time: Optional[float] = None
        self._start_time: Optional[float] = None
        
        self._running = False
        self._display_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def reset(self) -> None:
        """Reset all counters and history"""
        self.packets.reset()
        self.bytes_sent.reset()
        self.errors.reset()
        self.connections.reset()
        self._pps_history.clear()
        self._bps_history.clear()
        self._prev_packets = 0
        self._prev_bytes = 0
        self._prev_time = None
        self._start_time = time.time()
    
    def add_packets(self, count: int, byte_count: int) -> None:
        """Record transmitted packets"""
        self.packets.inc(count)
        self.bytes_sent.inc(byte_count)
    
    def add_error(self) -> None:
        """Record an error"""
        self.errors.inc()
    
    def add_connection(self) -> None:
        """Record a new connection"""
        self.connections.inc()
    
    def _sample_rates(self) -> Tuple[float, float]:
        """Calculate instantaneous PPS and BPS"""
        now = time.time()
        cur_pkts = self.packets.value
        cur_bytes = self.bytes_sent.value
        
        if self._prev_time is None:
            self._prev_time = now
            self._prev_packets = cur_pkts
            self._prev_bytes = cur_bytes
            return 0.0, 0.0
        
        dt = now - self._prev_time
        if dt < 0.05:
            last_pps = self._pps_history[-1] if self._pps_history else 0.0
            last_bps = self._bps_history[-1] if self._bps_history else 0.0
            return last_pps, last_bps
        
        pps = (cur_pkts - self._prev_packets) / dt
        bps = ((cur_bytes - self._prev_bytes) * 8) / dt
        
        self._prev_time = now
        self._prev_packets = cur_pkts
        self._prev_bytes = cur_bytes
        
        self._pps_history.append(pps)
        self._bps_history.append(bps)
        
        return pps, bps
    
    def _display_loop(self) -> None:
        """Real-time terminal display"""
        C = type('C', (), {
            'R': '\033[91m', 'G': '\033[92m', 'Y': '\033[93m',
            'B': '\033[94m', 'C': '\033[96m', 'W': '\033[97m',
            'END': '\033[0m', 'BOLD': '\033[1m', 'CLR': '\033[2K\r'
        })()
        
        while self._running:
            pps, bps = self._sample_rates()
            mbps = bps / 1_000_000
            elapsed = time.time() - self._start_time if self._start_time else 0
            
            avg_pps = (sum(self._pps_history) / len(self._pps_history)) if self._pps_history else 0
            peak_pps = max(self._pps_history) if self._pps_history else 0
            
            line = (
                f"{C.CLR}"
                f"{C.C}{C.BOLD}[*]{C.END} "
                f"Pkts: {C.G}{self.packets.value:>12,}{C.END} | "
                f"PPS: {C.G}{pps:>10,.0f}{C.END} "
                f"(avg:{avg_pps:,.0f} peak:{peak_pps:,.0f}) | "
                f"BW: {C.G}{mbps:>8.2f}{C.END} Mbps | "
                f"Err: {C.R}{self.errors.value}{C.END} | "
                f"Conn: {C.Y}{self.connections.value}{C.END} | "
                f"{C.Y}{elapsed:.0f}s{C.END}"
            )
            sys.stdout.write(line)
            sys.stdout.flush()
            time.sleep(0.5)
        
        sys.stdout.write('\n')
    
    def start_display(self) -> None:
        """Start the display thread"""
        self.reset()
        self._running = True
        self._display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self._display_thread.start()
    
    def stop_display(self) -> None:
        """Stop the display thread"""
        self._running = False
        if self._display_thread:
            self._display_thread.join(timeout=1.5)
    
    def export(self) -> Dict[str, Any]:
        """Export all statistics as a dictionary"""
        elapsed = (time.time() - self._start_time) if self._start_time else 0
        _, bps = self._sample_rates()
        
        pps_list = list(self._pps_history)
        bps_list = list(self._bps_history)
        
        return {
            'total_packets': self.packets.value,
            'total_bytes': self.bytes_sent.value,
            'total_megabytes': round(self.bytes_sent.value / (1024 * 1024), 3),
            'total_errors': self.errors.value,
            'total_connections': self.connections.value,
            'duration_seconds': round(elapsed, 2),
            'current_pps': round(pps_list[-1], 1) if pps_list else 0,
            'current_bps': round(bps, 1),
            'current_mbps': round(bps / 1_000_000, 3),
            'avg_pps': round(sum(pps_list) / len(pps_list), 1) if pps_list else 0,
            'peak_pps': round(max(pps_list), 1) if pps_list else 0,
            'avg_mbps': round((sum(bps_list) / len(bps_list) / 1_000_000), 3) if bps_list else 0,
            'peak_mbps': round((max(bps_list) / 1_000_000), 3) if bps_list else 0,
            'samples_collected': len(pps_list),
        }
    
    def print_summary(self) -> None:
        """Print formatted summary box"""
        d = self.export()
        
        box = f"""
╔══════════════════════════════════════════════════════════════╗
║                      ATTACK SUMMARY                         ║
╠══════════════════════════════════════════════════════════════╣
║  Total Packets:      {d['total_packets']:>15,}                    ║
║  Total Data:         {d['total_megabytes']:>12.3f} MB                   ║
║  Total Errors:       {d['total_errors']:>15,}                    ║
║  Total Connections:  {d['total_connections']:>15,}                    ║
╠══════════════════════════════════════════════════════════════╣
║  Duration:           {d['duration_seconds']:>12.2f} s                     ║
║  Current PPS:        {d['current_pps']:>12,.0f}                      ║
║  Average PPS:        {d['avg_pps']:>12,.0f}                      ║
║  Peak PPS:           {d['peak_pps']:>12,.0f}                      ║
╠══════════════════════════════════════════════════════════════╣
║  Current Bandwidth:  {d['current_mbps']:>12.3f} Mbps                  ║
║  Average Bandwidth:  {d['avg_mbps']:>12.3f} Mbps                  ║
║  Peak Bandwidth:     {d['peak_mbps']:>12.3f} Mbps                  ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(box)
    
    def to_json(self, path: str) -> None:
        """Export stats to JSON file"""
        import json
        with open(path, 'w') as f:
            json.dump(self.export(), f, indent=2)
    
    def to_csv(self, path: str) -> None:
        """Export stats to CSV file"""
        d = self.export()
        with open(path, 'w') as f:
            f.write('metric,value\n')
            for k, v in d.items():
                f.write(f'{k},{v}\n')
