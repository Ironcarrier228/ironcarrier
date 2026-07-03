#!/usr/bin/env python3
"""
Port Scanner
SYN/Connect port scanning with service detection and banner grabbing
"""

import socket
import threading
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class PortResult:
    port: int
    state: str
    service: str
    banner: str
    protocol: str = 'tcp'


class PortScanner:
    """Multi-threaded port scanner"""
    
    COMMON_PORTS = {
        21: 'ftp', 22: 'ssh', 23: 'telnet', 25: 'smtp', 53: 'dns',
        80: 'http', 110: 'pop3', 111: 'rpcbind', 135: 'msrpc',
        139: 'netbios-ssn', 143: 'imap', 443: 'https', 445: 'smb',
        993: 'imaps', 995: 'pop3s', 1433: 'mssql', 1521: 'oracle',
        3306: 'mysql', 3389: 'rdp', 5432: 'postgresql', 5900: 'vnc',
        6379: 'redis', 8080: 'http-proxy', 8443: 'https-alt',
        27017: 'mongodb', 11211: 'memcached', 6443: 'kubernetes-api',
        9200: 'elasticsearch', 5601: 'kibana',
    }
    
    WELL_KNOWN_PORTS = {
        7: 'echo', 9: 'discard', 13: 'daytime', 17: 'qotd', 19: 'chargen',
        37: 'time', 43: 'whois', 49: 'tacacs', 67: 'dhcp-server', 68: 'dhcp-client',
        69: 'tftp', 79: 'finger', 87: 'link', 88: 'kerberos', 113: 'ident',
        119: 'nntp', 123: 'ntp', 161: 'snmp', 162: 'snmptrap', 179: 'bgp',
        194: 'irc', 264: 'bgmp', 389: 'ldap', 464: 'kpasswd', 500: 'isakmp',
        512: 'exec', 513: 'login', 514: 'syslog', 515: 'lpd', 520: 'rip',
        521: 'ripng', 523: 'ibm-db2', 530: 'courier', 543: 'klogin',
        544: 'kshell', 548: 'afp', 554: 'rtsp', 587: 'submission',
        631: 'ipp', 636: 'ldaps', 873: 'rsync', 902: 'vmware',
        1080: 'socks', 1099: 'rmi', 1433: 'mssql', 1524: 'ingres-lock',
        2049: 'nfs', 2082: 'cpanel', 2083: 'cpanel-ssl', 2086: 'whm',
        2087: 'whm-ssl', 2095: 'webmail', 2096: 'webmail-ssl',
        2222: 'ssh-alt', 2601: 'zebra', 3300: 'mysql-cluster',
        3690: 'svn', 4369: 'epmd', 5432: 'postgresql', 5901: 'vnc-1',
        5902: 'vnc-2', 5903: 'vnc-3', 6000: 'x11', 6646: 'unknown',
        7070: 'realserver', 8000: 'http-alt', 8008: 'http-alt',
        8009: 'ajp13', 8081: 'http-proxy', 8443: 'https-alt',
        8888: 'sun-answerbook', 9100: 'jetdirect', 9900: 'iptel',
        10000: 'webmin', 11371: 'pgpkeyserver', 27017: 'mongodb',
        28017: 'mongodb-web', 50000: 'unknown',
    }
    
    def __init__(self, target: str, timeout: float = 1.0, threads: int = 200):
        self.target = target
        self.timeout = timeout
        self.threads = threads
        self.results: List[PortResult] = []
        self._lock = threading.Lock()
        self._progress = 0
        self._total = 0
    
    def _grab_banner(self, sock: socket.socket, port: int) -> str:
        """Attempt to grab service banner"""
        try:
            sock.settimeout(2)
            
            # Send protocol-specific probe
            if port in [80, 8080, 8000, 8888, 8008]:
                sock.send(b"HEAD / HTTP/1.0\r\nHost: {self.target}\r\n\r\n")
            elif port in [443, 8443]:
                sock.send(b"\x16\x03\x01\x00\x05\x01\x00\x00\x01\x00")
            elif port in [25, 587]:
                sock.send(b"EHLO scanner\r\n")
            elif port in [110, 995]:
                sock.send(b"CAPA\r\n")
            elif port in [143, 993]:
                sock.send(b"A001 CAPABILITY\r\n")
            elif port in [21]:
                sock.send(b"\r\n")
            elif port in [53]:
                sock.send(b"\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00")
            else:
                sock.send(b"\r\n")
            
            banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
            # Clean up banner
            lines = banner.split('\n')
            return lines[0][:200] if lines else ''
        except Exception:
            return ''
    
    def _scan_port(self, port: int) -> Optional[PortResult]:
        """Scan single port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((self.target, port))
            
            if result == 0:
                service = self.COMMON_PORTS.get(port, self.WELL_KNOWN_PORTS.get(port, 'unknown'))
                banner = self._grab_banner(sock, port)
                
                port_result = PortResult(
                    port=port,
                    state='open',
                    service=service,
                    banner=banner
                )
                
                with self._lock:
                    self.results.append(port_result)
                    self._progress += 1
                
                sock.close()
                return port_result
            
            sock.close()
        except Exception:
            pass
        
        with self._lock:
            self._progress += 1
        
        return None
    
    def scan_ports(self, ports: List[int]) -> List[PortResult]:
        """Scan specific list of ports"""
        self._total = len(ports)
        self._progress = 0
        self.results = []
        
        with ThreadPoolExecutor(max_workers=self.threads) as pool:
            list(pool.map(self._scan_port, ports))
        
        return sorted(self.results, key=lambda x: x.port)
    
    def scan_range(self, start: int, end: int) -> List[PortResult]:
        """Scan port range"""
        ports = list(range(start, end + 1))
        return self.scan_ports(ports)
    
    def scan_common(self) -> List[PortResult]:
        """Scan top common ports"""
        return self.scan_ports(sorted(self.COMMON_PORTS.keys()))
    
    def scan_top100(self) -> List[PortResult]:
        """Scan top 100 ports"""
        top_ports = [
            7, 9, 13, 21, 22, 23, 25, 26, 37, 53, 79, 80, 81, 88, 106, 110, 111,
            113, 119, 135, 139, 143, 144, 179, 199, 389, 427, 443, 444, 445, 465,
            513, 514, 515, 543, 544, 548, 554, 587, 631, 646, 873, 990, 993, 995,
            1025, 1026, 1027, 1028, 1029, 1110, 1433, 1720, 1723, 1755, 1900,
            2000, 2001, 2049, 2121, 2717, 3000, 3128, 3306, 3389, 3986, 4899,
            5000, 5009, 5051, 5060, 5101, 5190, 5357, 5432, 5631, 5666, 5800,
            5900, 6000, 6001, 6646, 7070, 8000, 8008, 8009, 8080, 8443, 8888,
            9100, 9999, 10000, 27017, 32768, 49152, 49153, 49154
        ]
        return self.scan_ports(top_ports)
    
    def scan_full(self) -> List[PortResult]:
        """Scan all 65535 ports"""
        return self.scan_range(1, 65535)
    
    def get_progress(self) -> Tuple[int, int]:
        """Get scan progress (done, total)"""
        return self._progress, self._total
    
    def print_results(self) -> None:
        """Print formatted results"""
        print(f"\n{'PORT':<8} {'STATE':<8} {'SERVICE':<20} {'BANNER'}")
        print("-" * 80)
        for r in self.results:
            banner = r.banner[:45] + '...' if len(r.banner) > 45 else r.banner
            print(f"{r.port:<8} {r.state:<8} {r.service:<20} {banner}")
        print(f"\n[+] Found {len(self.results)} open ports")
