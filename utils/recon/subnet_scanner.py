#!/usr/bin/env python3
"""
Subnet Scanner
Network discovery - find live hosts on subnet
"""

import socket
import threading
import ipaddress
from typing import List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import time


@dataclass
class HostResult:
    ip: str
    alive: bool
    ports_open: List[int] = None
    mac: str = ''
    hostname: str = ''
    response_time: float = 0.0
    
    def __post_init__(self):
        if self.ports_open is None:
            self.ports_open = []


class SubnetScanner:
    """Subnet host discovery"""
    
    def __init__(self, subnet: str, timeout: float = 0.5, threads: int = 500):
        self.subnet = subnet
        self.timeout = timeout
        self.threads = threads
        self.results: List[HostResult] = []
        self._lock = threading.Lock()
        self._callback: Optional[Callable] = None
    
    def set_callback(self, func: Callable) -> None:
        """Set callback for live host discovery"""
        self._callback = func
    
    def _check_host(self, ip: str) -> Optional[HostResult]:
        """Check if host is alive via TCP handshake"""
        start = time()
        
        # Try common ports
        for port in [80, 443, 22, 445, 139, 3389, 8080]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                result = sock.connect_ex((ip, port))
                sock.close()
                
                if result == 0:
                    response_time = time() - start
                    host = HostResult(
                        ip=ip,
                        alive=True,
                        ports_open=[port],
                        response_time=response_time
                    )
                    
                    # Try reverse DNS
                    try:
                        hostname = socket.gethostbyaddr(ip)[0]
                        host.hostname = hostname
                    except (socket.herror, socket.gaierror):
                        pass
                    
                    with self._lock:
                        self.results.append(host)
                    
                    if self._callback:
                        self._callback(host)
                    
                    return host
            except Exception:
                continue
        
        return None
    
    def _ping_check(self, ip: str) -> Optional[HostResult]:
        """ICMP ping check (requires root)"""
        start = time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            sock.settimeout(self.timeout)
            
            # Build ICMP echo request
            import struct
            icmp_type = 8  # Echo request
            icmp_code = 0
            checksum = 0
            identifier = 1
            sequence = 1
            
            header = struct.pack('!BBHHH', icmp_type, icmp_code, checksum, identifier, sequence)
            data = b'\x00' * 56
            
            # Calculate checksum
            packet = header + data
            s = 0
            for i in range(0, len(packet), 2):
                w = (packet[i] << 8) + packet[i + 1]
                s += w
            s = (s >> 16) + (s & 0xFFFF)
            s += s >> 16
            checksum = ~s & 0xFFFF
            
            header = struct.pack('!BBHHH', icmp_type, icmp_code, checksum, identifier, sequence)
            packet = header + data
            
            sock.sendto(packet, (ip, 0))
            sock.recvfrom(1024)
            sock.close()
            
            response_time = time() - start
            host = HostResult(ip=ip, alive=True, response_time=response_time)
            
            with self._lock:
                self.results.append(host)
            
            if self._callback:
                self._callback(host)
            
            return host
        except Exception:
            return None
    
    def scan_tcp(self) -> List[HostResult]:
        """TCP-based host discovery"""
        network = ipaddress.ip_network(self.subnet, strict=False)
        hosts = [str(ip) for ip in network.hosts()]
        
        print(f"[*] Scanning {len(hosts)} hosts in {self.subnet} via TCP")
        
        with ThreadPoolExecutor(max_workers=self.threads) as pool:
            list(pool.map(self._check_host, hosts))
        
        print(f"[+] Found {len(self.results)} live hosts")
        return sorted(self.results, key=lambda x: x.ip)
    
    def scan_icmp(self) -> List[HostResult]:
        """ICMP-based host discovery (root required)"""
        network = ipaddress.ip_network(self.subnet, strict=False)
        hosts = [str(ip) for ip in network.hosts()]
        
        print(f"[*] Scanning {len(hosts)} hosts in {self.subnet} via ICMP")
        
        with ThreadPoolExecutor(max_workers=self.threads) as pool:
            list(pool.map(self._ping_check, hosts))
        
        print(f"[+] Found {len(self.results)} live hosts")
        return sorted(self.results, key=lambda x: x.ip)
    
    def scan(self, method: str = 'tcp') -> List[HostResult]:
        """Scan with specified method"""
        if method == 'icmp':
            return self.scan_icmp()
        return self.scan_tcp()
    
    def print_results(self) -> None:
        """Print formatted results"""
        print(f"\n{'IP ADDRESS':<18} {'HOSTNAME':<25} {'OPEN PORTS':<15} {'TIME (ms)'}")
        print("-" * 75)
        for h in self.results:
            ports = ','.join(map(str, h.ports_open)) if h.ports_open else ''
            ms = f"{h.response_time * 1000:.1f}"
            print(f"{h.ip:<18} {h.hostname:<25} {ports:<15} {ms}")
        print(f"\n[+] Total: {len(self.results)} hosts")
    
    def export_ips(self) -> List[str]:
        """Export just the IP addresses"""
        return [h.ip for h in self.results]
