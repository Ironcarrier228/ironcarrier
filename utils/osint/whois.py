#!/usr/bin/env python3
"""
WHOIS Lookup
Domain WHOIS queries without external libraries
"""

import socket
import re
from typing import Dict, Optional, List


class WHOISLookup:
    """WHOIS lookup tool"""
    
    SERVERS = {
        'com': 'whois.verisign-grs.com',
        'net': 'whois.verisign-grs.com',
        'org': 'whois.pir.org',
        'info': 'whois.afilias.net',
        'biz': 'whois.nic.biz',
        'me': 'whois.nic.me',
        'io': 'whois.nic.io',
        'ai': 'whois.nic.ai',
        'ru': 'whois.tcinet.ru',
        'su': 'whois.tcinet.ru',
        'uk': 'whois.nic.uk',
        'co.uk': 'whois.nic.uk',
        'de': 'whois.denic.de',
        'fr': 'whois.nic.fr',
        'cn': 'whois.cnnic.cn',
        'jp': 'whois.jprs.jp',
        'br': 'whois.registro.br',
        'in': 'whois.registry.in',
        'au': 'whois.auda.org.au',
        'ca': 'whois.cira.ca',
        'nl': 'whois.sidn.nl',
        'pl': 'whois.dns.pl',
        'ua': 'whois.ua',
        'kz': 'whois.nic.kz',
        'tk': 'whois.nic.tk',
        'ml': 'whois.nic.ml',
        'ga': 'whois.nic.ga',
        'cf': 'whois.nic.cf',
        'gq': 'whois.nic.gq',
    }
    
    PATTERNS = {
        'domain_name': r'(?:Domain Name|Domain name|Название домена):\s*(.+)',
        'registrar': r'(?:Registrar|Регистратор):\s*(.+)',
        'registrar_url': r'(?:Registrar URL|URL регистратора):\s*(.+)',
        'creation_date': r'(?:Creation Date|Created On|Дата создания):\s*(.+)',
        'updated_date': r'(?:Updated Date|Last Updated|Дата обновления):\s*(.+)',
        'expiry_date': r'(?:Registry Expiry Date|Expiry Date|Дата окончания):\s*(.+)',
        'name_servers': r'(?:Name Server|Название сервера):\s*(.+)',
        'registrant_org': r'(?:Registrant Organization|Организация):\s*(.+)',
        'registrant_country': r'(?:Registrant Country|Страна):\s*(.+)',
        'status': r'(?:Domain Status|Статус домена):\s*(.+)',
        'dnssec': r'(?:DNSSEC|ДНСЕК):\s*(.+)',
        'whois_server': r'(?:Registrar WHOIS Server|WHOIS сервер):\s*(.+)',
    }
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
    
    def _get_server(self, domain: str) -> str:
        """Determine WHOIS server for TLD"""
        parts = domain.rstrip('.').split('.')
        
        # Check two-part TLDs first
        if len(parts) >= 2:
            two_part = '.'.join(parts[-2:])
            if two_part in self.SERVERS:
                return self.SERVERS[two_part]
        
        # Single part TLD
        tld = parts[-1].lower()
        return self.SERVERS.get(tld, 'whois.iana.org')
    
    def _query(self, server: str, domain: str, port: int = 43) -> str:
        """Perform WHOIS query"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        
        try:
            sock.connect((server, port))
            
            # Some servers need specific format
            if server == 'whois.denic.de':
                sock.send(f"-T dn,ace {domain}\r\n".encode())
            elif server == 'whois.jprs.jp':
                sock.send(f"{domain}/e\r\n".encode())
            else:
                sock.send(f"{domain}\r\n".encode())
            
            response = b''
            while True:
                try:
                    sock.settimeout(2)
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                except socket.timeout:
                    break
            
            sock.close()
            return response.decode('utf-8', errors='ignore')
        except Exception as e:
            sock.close()
            raise ConnectionError(f"WHOIS query failed: {e}")
    
    def _parse(self, raw: str) -> Dict[str, any]:
        """Extract fields from WHOIS response"""
        result = {}
        
        for field, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, raw, re.IGNORECASE | re.MULTILINE)
            if matches:
                cleaned = [m.strip() for m in matches]
                result[field] = cleaned if len(cleaned) > 1 else cleaned[0]
        
        result['raw'] = raw
        return result
    
    def lookup(self, domain: str, raw: bool = False) -> Dict:
        """Perform WHOIS lookup"""
        domain = domain.lower().strip()
        if not domain.endswith('.'):
            domain += '.'
        
        # Remove duplicate dots
        while '..' in domain:
            domain = domain.replace('..', '.')
        
        server = self._get_server(domain)
        response = self._query(server, domain)
        
        if raw:
            return {'server': server, 'raw': response}
        
        result = self._parse(response)
        result['whois_server'] = server
        
        # Follow referral if present
        referral = result.get('whois_server')
        if referral and referral != server:
            try:
                detailed = self._query(referral, domain)
                detailed_parsed = self._parse(detailed)
                for key, val in detailed_parsed.items():
                    if key != 'raw' and key not in result:
                        result[key] = val
                    elif key == 'raw':
                        result['raw'] = detailed
            except Exception:
                pass
        
        return result
    
    def lookup_raw(self, domain: str) -> str:
        """Get raw WHOIS response"""
        domain = domain.lower().strip()
        if not domain.endswith('.'):
            domain += '.'
        server = self._get_server(domain)
        return self._query(server, domain)
    
    def bulk_lookup(self, domains: List[str]) -> Dict[str, Dict]:
        """Lookup multiple domains"""
        results = {}
        for domain in domains:
            try:
                results[domain] = self.lookup(domain)
            except Exception as e:
                results[domain] = {'error': str(e)}
        return results
    
    def print_result(self, data: Dict) -> None:
        """Print formatted WHOIS result"""
        fields = [
            ('Domain Name', 'domain_name'),
            ('Registrar', 'registrar'),
            ('Registrar URL', 'registrar_url'),
            ('Creation Date', 'creation_date'),
            ('Updated Date', 'updated_date'),
            ('Expiry Date', 'expiry_date'),
            ('Registrant Org', 'registrant_org'),
            ('Registrant Country', 'registrant_country'),
            ('Name Servers', 'name_servers'),
            ('Status', 'status'),
            ('DNSSEC', 'dnssec'),
            ('WHOIS Server', 'whois_server'),
        ]
        
        print(f"\n{'─' * 50}")
        for label, key in fields:
            value = data.get(key)
            if value:
                if isinstance(value, list):
                    for v in value:
                        print(f"  {label:<20}: {v}")
                else:
                    print(f"  {label:<20}: {value}")
        print(f"{'─' * 50}\n")
