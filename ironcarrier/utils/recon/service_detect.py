#!/usr/bin/env python3
"""
Service Detection
Identify running services and versions via banner analysis
"""

import socket
import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ServiceInfo:
    name: str
    version: str
    os: str
    extra: str


class ServiceDetector:
    """Service fingerprinting via banners and probes"""
    
    PROBES = {
        'http': [
            (b"GET / HTTP/1.0\r\n\r\n", [
                (r'Apache/([\d.]+)', 'Apache', None),
                (r'nginx/([\d.]+)', 'Nginx', None),
                (r'IIS/([\d.]+)', 'IIS', 'Windows'),
                (r'lighttpd/([\d.]+)', 'Lighttpd', None),
                (r'openresty/([\d.]+)', 'OpenResty', None),
                (r'Tomcat/([\d.]+)', 'Tomcat', None),
                (r'Jetty\(([\d.]+)\)', 'Jetty', None),
                (r'Caddy', 'Caddy', None),
                (r'cloudflare', 'Cloudflare', None),
                (r'Server:\s*([^\r\n]+)', None, None),
            ]),
        ],
        'ssh': [
            (b"", [
                (r'SSH-([\d.]+)-OpenSSH_([\d.p]+)', 'OpenSSH', None),
                (r'SSH-([\d.]+)-dropbear_([\d.]+)', 'Dropbear', None),
                (r'SSH-([\d.]+)-(.+)', None, None),
            ]),
        ],
        'ftp': [
            (b"", [
                (r'vsftpd\s+([\d.]+)', 'vsftpd', None),
                (r'ProFTPD\s+([\d.]+)', 'ProFTPD', None),
                (r'Pure-FTPd', 'Pure-FTPd', None),
                (r'FileZilla Server\s+([\d.]+)', 'FileZilla', 'Windows'),
                (r'Microsoft FTP Service', 'IIS FTP', 'Windows'),
            ]),
        ],
        'smtp': [
            (b"EHLO detect\r\n", [
                (r'Postfix', 'Postfix', None),
                (r'Exim\s+([\d.]+)', 'Exim', None),
                (r'Sendmail\s+([\d.]+)', 'Sendmail', None),
                (r'Microsoft ESMTP MAIL', 'Exchange', 'Windows'),
            ]),
        ],
        'mysql': [
            (b"\x00", [
                (r'([\d.]+)-mysql', 'MySQL', None),
                (r'MariaDB\s+([\d.]+)', 'MariaDB', None),
            ]),
        ],
        'redis': [
            (b"INFO\r\n", [
                (r'redis_version:([\d.]+)', 'Redis', None),
            ]),
        ],
    }
    
    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout
    
    def _match_patterns(self, banner: str, patterns: list) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Match banner against regex patterns"""
        for pattern, name, os_match in patterns:
            match = re.search(pattern, banner, re.IGNORECASE)
            if match:
                version = match.group(1) if match.groups() else ''
                detected_name = name if name else match.group(1)
                return detected_name, version, os_match
        return None, None, None
    
    def detect(self, host: str, port: int, service_hint: str = None) -> Optional[ServiceInfo]:
        """Detect service on specified port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((host, port))
            
            # Try to get initial banner first
            initial_banner = b''
            try:
                initial_banner = sock.recv(1024)
            except socket.timeout:
                pass
            
            banner = initial_banner.decode('utf-8', errors='ignore')
            
            # Determine which probes to try
            probe_types = []
            if service_hint and service_hint in self.PROBES:
                probe_types.append(service_hint)
            
            # Auto-detect based on port
            port_service_map = {
                80: 'http', 443: 'http', 8080: 'http', 8443: 'http',
                22: 'ssh', 2222: 'ssh',
                21: 'ftp',
                25: 'smtp', 587: 'smtp',
                3306: 'mysql',
                6379: 'redis',
            }
            
            if port in port_service_map and port_service_map[port] not in probe_types:
                probe_types.append(port_service_map[port])
            
            # Try all relevant probes
            for probe_type in probe_types:
                for probe_data, patterns in self.PROBES.get(probe_type, []):
                    if probe_data:
                        try:
                            sock.send(probe_data)
                            response = sock.recv(2048).decode('utf-8', errors='ignore')
                            banner = initial_banner.decode('utf-8', errors='ignore') + response
                        except Exception:
                            continue
                    
                    name, version, os_info = self._match_patterns(banner, patterns)
                    if name:
                        return ServiceInfo(
                            name=name,
                            version=version,
                            os=os_info or '',
                            extra=banner[:200]
                        )
            
            # Return raw banner if no pattern matched
            if banner.strip():
                return ServiceInfo(
                    name='unknown',
                    version='',
                    os='',
                    extra=banner[:200]
                )
            
            sock.close()
        except Exception:
            pass
        
        return None

