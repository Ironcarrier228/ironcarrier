#!/usr/bin/env python3
"""
Vulnerability Scanner
Basic service-level vulnerability detection
"""

import socket
import ssl
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor


@dataclass
class VulnResult:
    port: int
    service: str
    vuln_id: str
    severity: str
    description: str
    verified: bool


class VulnScanner:
    """Basic vulnerability scanner for common misconfigurations"""
    
    CHECKS = {
        'ssh_weak_ciphers': {
            'ports': [22],
            'severity': 'medium',
            'description': 'SSH server accepts weak ciphers',
        },
        'ssl_weak_protocol': {
            'ports': [443, 8443, 993, 995],
            'severity': 'high',
            'description': 'SSL/TLS accepts weak protocols (SSLv2/SSLv3)',
        },
        'ssl_self_signed': {
            'ports': [443, 8443],
            'severity': 'low',
            'description': 'Self-signed or invalid SSL certificate',
        },
        'ftp_anonymous': {
            'ports': [21],
            'severity': 'medium',
            'description': 'FTP anonymous login enabled',
        },
        'redis_no_auth': {
            'ports': [6379],
            'severity': 'critical',
            'description': 'Redis without authentication',
        },
        'mongodb_no_auth': {
            'ports': [27017],
            'severity': 'critical',
            'description': 'MongoDB without authentication',
        },
        'memcached_exposed': {
            'ports': [11211],
            'severity': 'high',
            'description': 'Memcached exposed without auth',
        },
        'smb_signing_disabled': {
            'ports': [445],
            'severity': 'medium',
            'description': 'SMB signing not required',
        },
        'rdpExposed': {
            'ports': [3389],
            'severity': 'high',
            'description': 'RDP exposed to network',
        },
        'elasticsearch_open': {
            'ports': [9200],
            'severity': 'critical',
            'description': 'Elasticsearch open without auth',
        },
    }
    
    def __init__(self, target: str, timeout: float = 5.0, threads: int = 20):
        self.target = target
        self.timeout = timeout
        self.threads = threads
        self.results: List[VulnResult] = []
        self._lock = threading.Lock()
    
    def _check_ssl_weak(self, port: int) -> Optional[VulnResult]:
        """Check for weak SSL/TLS protocols"""
        try:
            for protocol in [ssl.PROTOCOL_SSLv23, ssl.PROTOCOL_TLS]:
                ctx = ssl.SSLContext(protocol)
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                wrapped = ctx.wrap_socket(sock, server_hostname=self.target)
                
                cipher = wrapped.cipher()
                version = wrapped.version()
                wrapped.close()
                
                if version and ('SSLv2' in version or 'SSLv3' in version):
                    return VulnResult(
                        port=port, service='ssl', vuln_id='SSL-WEAK-PROTO',
                        severity='high', description=f'Weak protocol: {version}',
                        verified=True
                    )
                
                return None
        except Exception:
            return None
    
    def _check_ssl_self_signed(self, port: int) -> Optional[VulnResult]:
        """Check for self-signed certificate"""
        try:
            ctx = ssl.create_default_context()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            ctx.wrap_socket(sock, server_hostname=self.target)
            return None
        except ssl.SSLCertVerificationError:
            return VulnResult(
                port=port, service='ssl', vuln_id='SSL-SELF-SIGNED',
                severity='low', description='Self-signed or invalid certificate',
                verified=True
            )
        except Exception:
            return None
    
    def _check_ftp_anonymous(self, port: int) -> Optional[VulnResult]:
        """Check for FTP anonymous login"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.target, port))
            banner = sock.recv(1024).decode()
            
            sock.send(b'USER anonymous\r\n')
            resp = sock.recv(1024).decode()
            
            if '331' in resp:
                sock.send(b'PASS anonymous@\r\n')
                resp = sock.recv(1024).decode()
                
                if '230' in resp:
                    sock.send(b'QUIT\r\n')
                    sock.close()
                    return VulnResult(
                        port=port, service='ftp', vuln_id='FTP-ANON',
                        severity='medium', description='Anonymous login successful',
                        verified=True
                    )
            
            sock.close()
        except Exception:
            pass
        return None
    
    def _check_redis_no_auth(self, port: int) -> Optional[VulnResult]:
        """Check for unauthenticated Redis"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.target, port))
            sock.send(b'INFO\r\n')
            resp = sock.recv(1024).decode()
            sock.close()
            
            if 'redis_version' in resp:
                return VulnResult(
                    port=port, service='redis', vuln_id='REDIS-NO-AUTH',
                    severity='critical', description=f'Unauthenticated Redis: {resp[:100]}',
                    verified=True
                )
        except Exception:
            pass
        return None
    
    def _check_mongodb_no_auth(self, port: int) -> Optional[VulnResult]:
        """Check for unauthenticated MongoDB"""
        try:
            import struct
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.target, port))
            
            # MongoDB ismaster query
            query = struct.pack('<i', 16 + 46) + b'\x00\x00\x00\x00' + b'\xd4\x07\x00\x00' + b'\x00\x00\x00\x00' + b'ismaster\x00\x01\x00\x00\x00'
            sock.send(query)
            resp = sock.recv(1024)
            sock.close()
            
            if resp and b'ismaster' in resp:
                return VulnResult(
                    port=port, service='mongodb', vuln_id='MONGO-NO-AUTH',
                    severity='critical', description='Unauthenticated MongoDB',
                    verified=True
                )
        except Exception:
            pass
        return None
    
    def _check_memcached_exposed(self, port: int) -> Optional[VulnResult]:
        """Check for exposed Memcached"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.target, port))
            sock.send(b'stats\r\n')
            resp = sock.recv(1024).decode()
            sock.close()
            
            if 'STAT' in resp:
                return VulnResult(
                    port=port, service='memcached', vuln_id='MEMCACHED-EXPOSED',
                    severity='high', description='Memcached exposed without auth',
                    verified=True
                )
        except Exception:
            pass
        return None
    
    def _check_elasticsearch_open(self, port: int) -> Optional[VulnResult]:
        """Check for open Elasticsearch"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.target, port))
            sock.send(b'GET / HTTP/1.0\r\n\r\n')
            resp = sock.recv(1024).decode()
            sock.close()
            
            if 'elasticsearch' in resp.lower() or 'cluster_name' in resp:
                return VulnResult(
                    port=port, service='elasticsearch', vuln_id='ES-OPEN',
                    severity='critical', description='Elasticsearch open without auth',
                    verified=True
                )
        except Exception:
            pass
        return None
    
    def _run_check(self, check_name: str, check_info: dict) -> None:
        """Execute a single vulnerability check"""
        check_methods = {
            'ssl_weak_protocol': self._check_ssl_weak,
            'ssl_self_signed': self._check_ssl_self_signed,
            'ftp_anonymous': self._check_ftp_anonymous,
            'redis_no_auth': self._check_redis_no_auth,
            'mongodb_no_auth': self._check_mongodb_no_auth,
            'memcached_exposed': self._check_memcached_exposed,
            'elasticsearch_open': self._check_elasticsearch_open,
        }
        
        method = check_methods.get(check_name)
        if not method:
            return
        
        for port in check_info['ports']:
            try:
                result = method(port)
                if result:
                    with self._lock:
                        self.results.append(result)
            except Exception:
                continue
    
    def scan(self, ports: List[int] = None) -> List[VulnResult]:
        """Run vulnerability scan"""
        self.results = []
        
        checks_to_run = {}
        for check_name, check_info in self.CHECKS.items():
            if ports is None or any(p in ports for p in check_info['ports']):
                checks_to_run[check_name] = check_info
        
        print(f"[*] Running {len(checks_to_run)} vulnerability checks against {self.target}")
        
        with ThreadPoolExecutor(max_workers=self.threads) as pool:
            list(pool.map(self._run_check, checks_to_run.keys(), [checks_to_run[k] for k in checks_to_run]))
        
        print(f"[+] Found {len(self.results)} potential vulnerabilities")
        return self.results
    
    def print_results(self) -> None:
        """Print formatted results"""
        if not self.results:
            print("[*] No vulnerabilities found")
            return
        
        severity_colors = {'critical': '\033[91m', 'high': '\033[93m', 'medium': '\033[96m', 'low': '\033[97m'}
        
        print(f"\n{'PORT':<8} {'SEVERITY':<12} {'VULN ID':<18} {'DESCRIPTION'}")
        print("-" * 85)
        
        for r in sorted(self.results, key=lambda x: ['critical', 'high', 'medium', 'low'].index(x.severity)):
            color = severity_colors.get(r.severity, '\033[0m')
            reset = '\033[0m'
            print(f"{r.port:<8} {color}{r.severity:<12}{reset} {r.vuln_id:<18} {r.description[:45]}")
