#!/usr/bin/env python3
"""
DNS Enumeration
DNS record lookup and zone transfer attempts
"""

import socket
import struct
from typing import Dict, List, Optional

try:
    import dns.resolver
    import dns.message
    import dns.query
    import dns.rdatatype
    import dns.flags
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False


class DNSEnum:
    """DNS record enumeration"""
    
    RECORD_TYPES = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA', 'SRV', 'PTR', 'CAA', 'DS']
    
    def __init__(self, timeout: float = 5.0, dns_server: str = None):
        self.timeout = timeout
        self.dns_server = dns_server
        self._resolver = None
        if HAS_DNSPYTHON:
            self._resolver = dns.resolver.Resolver()
            self._resolver.timeout = timeout
            self._resolver.lifetime = timeout
            if dns_server:
                self._resolver.nameservers = [dns_server]
    
    def _simple_resolve(self, domain: str) -> List[str]:
        """Fallback resolver using system DNS"""
        try:
            return [socket.gethostbyname(domain)]
        except socket.gaierror:
            return []
    
    def query(self, domain: str, record_type: str, server: str = None) -> List[str]:
        """Query specific DNS record type"""
        if not HAS_DNSPYTHON:
            if record_type.upper() == 'A':
                return self._simple_resolve(domain)
            return []
        
        resolver = self._resolver
        if server and server != self.dns_server:
            resolver = dns.resolver.Resolver()
            resolver.timeout = self.timeout
            resolver.nameservers = [server]
        
        try:
            answers = resolver.resolve(domain, record_type)
            return [str(rdata) for rdata in answers]
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.DNSException):
            return []
    
    def get_all_records(self, domain: str) -> Dict[str, List[str]]:
        """Get all common DNS records"""
        results = {}
        for rtype in self.RECORD_TYPES:
            records = self.query(domain, rtype)
            if records:
                results[rtype] = records
        return results
    
    def get_a_records(self, domain: str) -> List[str]:
        """Get A records"""
        return self.query(domain, 'A')
    
    def get_aaaa_records(self, domain: str) -> List[str]:
        """Get AAAA records"""
        return self.query(domain, 'AAAA')
    
    def get_mx_records(self, domain: str) -> List[str]:
        """Get MX records"""
        return self.query(domain, 'MX')
    
    def get_ns_records(self, domain: str) -> List[str]:
        """Get NS records"""
        return self.query(domain, 'NS')
    
    def get_txt_records(self, domain: str) -> List[str]:
        """Get TXT records"""
        return self.query(domain, 'TXT')
    
    def get_soa_record(self, domain: str) -> List[str]:
        """Get SOA record"""
        return self.query(domain, 'SOA')
    
    def get_cname_records(self, domain: str) -> List[str]:
        """Get CNAME records"""
        return self.query(domain, 'CNAME')
    
    def get_srv_records(self, domain: str) -> List[str]:
        """Get SRV records"""
        return self.query(domain, 'SRV')
    
    def get_caa_records(self, domain: str) -> List[str]:
        """Get CAA records (Certificate Authority Authorization)"""
        return self.query(domain, 'CAA')
    
    def check_dnssec(self, domain: str) -> Optional[bool]:
        """Check if DNSSEC is enabled"""
        if not HAS_DNSPYTHON:
            return None
        try:
            resolver = dns.resolver.Resolver()
            resolver.set_flags(dns.flags.AD)
            if self.dns_server:
                resolver.nameservers = [self.dns_server]
            answers = resolver.resolve(domain, 'A')
            return bool(answers.response.flags & dns.flags.AD)
        except Exception:
            return None
    
    def zone_transfer(self, domain: str, ns_server: str = None) -> Optional[List[str]]:
        """Attempt DNS zone transfer (AXFR)"""
        if not HAS_DNSPYTHON:
            return None
        
        if not ns_server:
            ns_records = self.get_ns_records(domain)
            if not ns_records:
                return None
            ns_server = ns_records[0]
        
        # Strip trailing dot if present
        ns_server = ns_server.rstrip('.')
        
        try:
            zone = dns.query.xfr(ns_server, domain, timeout=self.timeout)
            records = []
            for rset in zone:
                records.append(str(rset))
            return records if records else None
        except Exception:
            return None
    
    def reverse_dns(self, ip: str) -> Optional[str]:
        """Reverse DNS lookup"""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except (socket.herror, socket.gaierror):
            return None
    
    def print_results(self, records: Dict[str, List[str]], domain: str) -> None:
        """Print formatted DNS records"""
        print(f"\n  DNS Records for: {domain}")
        print(f"  {'─' * 50}")
        
        for rtype in self.RECORD_TYPES:
            if rtype in records:
                values = records[rtype]
                if isinstance(values, list):
                    for v in values:
                        print(f"  {rtype:<8} {v}")
                else:
                    print(f"  {rtype:<8} {values}")
        
        print(f"  {'─' * 50}\n")
