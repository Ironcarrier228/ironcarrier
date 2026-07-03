#!/usr/bin/env python3
"""
Subdomain Enumeration
Bruteforce and passive subdomain discovery
"""

import socket
import threading
from typing import Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


class SubdomainBruteforcer:
    """Subdomain enumeration via DNS bruteforce"""
    
    DEFAULT_WORDLIST = [
        'www', 'mail', 'ftp', 'localhost', 'webmail', 'smtp', 'pop', 'pop3',
        'imap', 'ns1', 'ns2', 'ns3', 'ns4', 'dns', 'dns1', 'dns2',
        'mx', 'mx1', 'mx2', 'mx3', 'api', 'dev', 'staging', 'test',
        'admin', 'portal', 'blog', 'forum', 'shop', 'store', 'app',
        'cdn', 'static', 'media', 'images', 'img', 'assets', 'files',
        'download', 'uploads', 'upload', 'vpn', 'remote', 'gateway',
        'proxy', 'firewall', 'router', 'switch', 'access', 'panel',
        'cpanel', 'whm', 'webmin', 'plesk', 'directadmin', 'server',
        'cloud', 'aws', 'azure', 'gcp', 'digitalocean', 'heroku',
        'git', 'gitlab', 'github', 'bitbucket', 'svn', 'repo',
        'ci', 'cd', 'jenkins', 'build', 'deploy', 'staging',
        'db', 'database', 'mysql', 'postgres', 'postgresql', 'mongodb',
        'redis', 'memcached', 'elastic', 'elasticsearch', 'kibana',
        'grafana', 'prometheus', 'monitor', 'metrics', 'logs',
        'logstash', 'splunk', 'sentry', 'datadog', 'newrelic',
        'auth', 'login', 'sso', 'oauth', 'identity', 'ldap',
        'docs', 'doc', 'wiki', 'knowledge', 'help', 'support',
        'status', 'health', 'ping', 'check', 'monitoring',
        'api2', 'api-v2', 'v2', 'v3', 'v1', 'api-v1',
        'internal', 'intranet', 'private', 'corp', 'office',
        'stage', 'preprod', 'pre-production', 'uat', 'qa',
        'demo', 'sandbox', 'dev1', 'dev2', 'test1', 'test2',
        'm', 'mobile', 'wap', 'touch', 'pda',
        'video', 'stream', 'live', 'tv', 'radio',
        'chat', 'messenger', 'notify', 'push', 'websocket',
        'search', 'finder', 'lookup', 'query',
        'pay', 'payment', 'billing', 'checkout', 'cart',
        'user', 'users', 'account', 'profile', 'member',
        'cms', 'wordpress', 'wp', 'drupal', 'joomla', 'magento',
        'back', 'backend', 'front', 'frontend', 'web',
        'news', 'press', 'about', 'contact', 'careers', 'jobs',
        'legal', 'privacy', 'terms', 'policy', 'security',
        's3', 'storage', 'bucket', 'files', 'media',
        'edge', 'waf', 'cdn2', 'cdn1',
        'alpha', 'beta', 'gamma', 'delta',
        'old', 'new', 'backup', 'bak', 'archive',
        'mail2', 'smtp2', 'imap2', 'pop4',
        'relay', 'hub', 'node', 'master', 'slave',
        'primary', 'secondary', 'tertiary',
    ]
    
    def __init__(self, domain: str, wordlist: str = 'default', threads: int = 100, timeout: float = 2.0):
        self.domain = domain.rstrip('.')
        self.threads = threads
        self.timeout = timeout
        self.found: List[Dict] = []
        self._lock = threading.Lock()
        self._wordlist: List[str] = []
        
        if wordlist == 'default':
            self._wordlist = self.DEFAULT_WORDLIST
        elif wordlist and Path(wordlist).exists():
            with open(wordlist, 'r') as f:
                self._wordlist = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    def _resolve(self, subdomain: str) -> Optional[Dict]:
        """Resolve single subdomain"""
        fqdn = f"{subdomain}.{self.domain}"
        try:
            socket.setdefaulttimeout(self.timeout)
            ip = socket.gethostbyname(fqdn)
            result = {'subdomain': fqdn, 'ip': ip, 'source': 'bruteforce'}
            with self._lock:
                self.found.append(result)
            return result
        except socket.gaierror:
            return None
    
    def run(self, silent: bool = False) -> List[Dict]:
        """Run subdomain bruteforce"""
        if not self._wordlist:
            print("[-] Empty wordlist")
            return []
        
        if not silent:
            print(f"[*] Bruteforcing {len(self._wordlist)} subdomains for {self.domain}")
        
        with ThreadPoolExecutor(max_workers=self.threads) as pool:
            futures = {pool.submit(self._resolve, sub): sub for sub in self._wordlist}
            for future in as_completed(futures):
                if not silent:
                    result = future.result()
                    if result:
                        print(f"    [+] {result['subdomain']} -> {result['ip']}")
        
        if not silent:
            print(f"[+] Found {len(self.found)} subdomains")
        
        return self.found
    
    def get_domains(self) -> List[str]:
        """Return just the subdomain FQDNs"""
        return [r['subdomain'] for r in self.found]
    
    def get_ips(self) -> List[str]:
        """Return just the IPs"""
        return list(set(r['ip'] for r in self.found))
    
    def print_results(self) -> None:
        """Print formatted results"""
        print(f"\n{'SUBDOMAIN':<40} {'IP ADDRESS':<18}")
        print("─" * 60)
        for r in sorted(self.found, key=lambda x: x['subdomain']):
            print(f"{r['subdomain']:<40} {r['ip']:<18}")
        print(f"\n[+] Total: {len(self.found)} subdomains\n")


class PassiveSubdomainCollector:
    """Collect subdomains from passive sources"""
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
    
    def _cert_transparency(self, domain: str) -> List[str]:
        """Get subdomains from Certificate Transparency logs"""
        import json
        import ssl
        import urllib.request
        
        subdomains = []
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
                data = json.loads(resp.read().decode())
                for entry in data:
                    name = entry.get('name_value', '')
                    for n in name.split('\n'):
                        n = n.strip().lstrip('*.')
                        if n.endswith(f'.{domain}') and n != domain:
                            subdomains.append(n)
                return list(set(subdomains))
        except Exception:
            return []
    
    def collect(self, domain: str) -> List[str]:
        """Collect subdomains from all passive sources"""
        results = set()
        
        ct_results = self._cert_transparency(domain)
        results.update(ct_results)
        
        return sorted(results)
