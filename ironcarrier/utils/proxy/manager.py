#!/usr/bin/env python3
"""
Proxy Manager
Load, store, filter, and manage proxy lists
"""

import json
import time
import threading
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum


class ProxyType(Enum):
    HTTP = 'http'
    HTTPS = 'https'
    SOCKS4 = 'socks4'
    SOCKS5 = 'socks5'
    UNKNOWN = 'unknown'


class ProxyStatus(Enum):
    UNKNOWN = 'unknown'
    ALIVE = 'alive'
    DEAD = 'dead'
    BANNED = 'banned'
    TIMEOUT = 'timeout'


@dataclass
class Proxy:
    address: str
    port: int
    proxy_type: ProxyType = ProxyType.UNKNOWN
    status: ProxyStatus = ProxyStatus.UNKNOWN
    latency: float = 0.0
    country: str = ''
    region: str = ''
    isp: str = ''
    last_check: float = 0.0
    use_count: int = 0
    fail_count: int = 0
    anonymity: str = ''  # transparent, anonymous, elite
    
    @property
    def url(self) -> str:
        return f"{self.proxy_type.value}://{self.address}:{self.port}"
    
    @property
    def hostport(self) -> Tuple[str, int]:
        return (self.address, self.port)
    
    def to_dict(self) -> Dict:
        return {
            'address': self.address,
            'port': self.port,
            'type': self.proxy_type.value,
            'status': self.status.value,
            'latency': round(self.latency, 3),
            'country': self.country,
            'region': self.region,
            'isp': self.isp,
            'last_check': self.last_check,
            'use_count': self.use_count,
            'fail_count': self.fail_count,
            'anonymity': self.anonymity,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Proxy':
        return cls(
            address=data['address'],
            port=data['port'],
            proxy_type=ProxyType(data.get('type', 'unknown')),
            status=ProxyStatus(data.get('status', 'unknown')),
            latency=data.get('latency', 0),
            country=data.get('country', ''),
            region=data.get('region', ''),
            isp=data.get('isp', ''),
            last_check=data.get('last_check', 0),
            use_count=data.get('use_count', 0),
            fail_count=data.get('fail_count', 0),
            anonymity=data.get('anonymity', ''),
        )
    
    @classmethod
    def from_string(cls, line: str, default_type: ProxyType = ProxyType.HTTP) -> Optional['Proxy']:
        line = line.strip()
        if not line or line.startswith('#'):
            return None
        
        parts = line.split(':')
        if len(parts) < 2:
            return None
        
        address = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            return None
        
        proxy_type = default_type
        if len(parts) >= 3:
            try:
                proxy_type = ProxyType(parts[2].lower())
            except ValueError:
                pass
        
        return cls(address=address, port=port, proxy_type=proxy_type)


class ProxyManager:
    """Central proxy management"""
    
    def __init__(self):
        self._proxies: Dict[str, Proxy] = {}
        self._lock = threading.Lock()
    
    def _key(self, address: str, port: int) -> str:
        return f"{address}:{port}"
    
    def add(self, proxy: Proxy) -> None:
        with self._lock:
            key = self._key(proxy.address, proxy.port)
            self._proxies[key] = proxy
    
    def add_from_string(self, line: str, default_type: ProxyType = ProxyType.HTTP) -> Optional[Proxy]:
        proxy = Proxy.from_string(line, default_type)
        if proxy:
            self.add(proxy)
        return proxy
    
    def remove(self, address: str, port: int) -> bool:
        with self._lock:
            key = self._key(address, port)
            if key in self._proxies:
                del self._proxies[key]
                return True
        return False
    
    def get(self, address: str, port: int) -> Optional[Proxy]:
        with self._lock:
            return self._proxies.get(self._key(address, port))
    
    def load_from_file(self, filepath: str, default_type: ProxyType = ProxyType.HTTP) -> int:
        count = 0
        path = Path(filepath)
        if not path.exists():
            return 0
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if self.add_from_string(line, default_type):
                    count += 1
        
        return count
    
    def load_from_list(self, proxies: List[Tuple[str, int]], proxy_type: ProxyType = ProxyType.HTTP) -> int:
        for address, port in proxies:
            self.add(Proxy(address=address, port=port, proxy_type=proxy_type))
        return len(proxies)
    
    def save_to_file(self, filepath: str, status_filter: ProxyStatus = None) -> int:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        count = 0
        with open(path, 'w', encoding='utf-8') as f:
            for proxy in self.get_all(status_filter=status_filter):
                f.write(f"{proxy.address}:{proxy.port}\n")
                count += 1
        
        return count
    
    def save_to_json(self, filepath: str, status_filter: ProxyStatus = None) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'count': len(self._proxies),
            'timestamp': time.time(),
            'proxies': [p.to_dict() for p in self.get_all(status_filter=status_filter)]
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def load_from_json(self, filepath: str) -> int:
        path = Path(filepath)
        if not path.exists():
            return 0
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for pd in data.get('proxies', []):
            proxy = Proxy.from_dict(pd)
            self.add(proxy)
        
        return len(data.get('proxies', []))
    
    def get_all(self, status_filter: ProxyStatus = None, type_filter: ProxyType = None,
                country_filter: str = None, max_latency: float = None) -> List[Proxy]:
        with self._lock:
            proxies = list(self._proxies.values())
        
        if status_filter:
            proxies = [p for p in proxies if p.status == status_filter]
        if type_filter:
            proxies = [p for p in proxies if p.proxy_type == type_filter]
        if country_filter:
            proxies = [p for p in proxies if p.country.lower() == country_filter.lower()]
        if max_latency is not None:
            proxies = [p for p in proxies if p.latency <= max_latency or p.latency == 0]
        
        return proxies
    
    def get_alive(self) -> List[Proxy]:
        return self.get_all(status_filter=ProxyStatus.ALIVE)
    
    def get_by_country(self, country: str) -> List[Proxy]:
        return self.get_all(country_filter=country)
    
    def get_by_type(self, proxy_type: ProxyType) -> List[Proxy]:
        return self.get_all(type_filter=proxy_type)
    
    def update_proxy(self, address: str, port: int, **kwargs) -> bool:
        with self._lock:
            proxy = self._proxies.get(self._key(address, port))
            if not proxy:
                return False
            
            for key, value in kwargs.items():
                if hasattr(proxy, key):
                    setattr(proxy, key, value)
            return True
    
    def mark_dead(self, address: str, port: int) -> None:
        with self._lock:
            proxy = self._proxies.get(self._key(address, port))
            if proxy:
                proxy.status = ProxyStatus.DEAD
                proxy.fail_count += 1
    
    def increment_use(self, address: str, port: int) -> None:
        with self._lock:
            proxy = self._proxies.get(self._key(address, port))
            if proxy:
                proxy.use_count += 1
    
    def remove_dead(self) -> int:
        count = 0
        with self._lock:
            dead_keys = [k for k, p in self._proxies.items() if p.status == ProxyStatus.DEAD]
            for key in dead_keys:
                del self._proxies[key]
                count += 1
        return count
    
    def remove_by_fail_count(self, max_fails: int = 3) -> int:
        count = 0
        with self._lock:
            fail_keys = [k for k, p in self._proxies.items() if p.fail_count >= max_fails]
            for key in fail_keys:
                del self._proxies[key]
                count += 1
        return count
    
    def clear(self) -> int:
        with self._lock:
            count = len(self._proxies)
            self._proxies.clear()
            return count
    
    @property
    def count(self) -> int:
        with self._lock:
            return len(self._proxies)
    
    @property
    def alive_count(self) -> int:
        with self._lock:
            return sum(1 for p in self._proxies.values() if p.status == ProxyStatus.ALIVE)
    
    @property
    def dead_count(self) -> int:
        with self._lock:
            return sum(1 for p in self._proxies.values() if p.status == ProxyStatus.DEAD)
    
    def stats(self) -> Dict:
        with self._lock:
            type_counts = {}
            status_counts = {}
            country_counts = {}
            total_uses = 0
            total_latency = 0
            latency_count = 0
            
            for proxy in self._proxies.values():
                pt = proxy.proxy_type.value
                type_counts[pt] = type_counts.get(pt, 0) + 1
                
                ps = proxy.status.value
                status_counts[ps] = status_counts.get(ps, 0) + 1
                
                if proxy.country:
                    country_counts[proxy.country] = country_counts.get(proxy.country, 0) + 1
                
                total_uses += proxy.use_count
                if proxy.latency > 0:
                    total_latency += proxy.latency
                    latency_count += 1
            
            avg_latency = total_latency / latency_count if latency_count > 0 else 0
            
            return {
                'total': len(self._proxies),
                'by_type': type_counts,
                'by_status': status_counts,
                'by_country': country_counts,
                'total_uses': total_uses,
                'avg_latency': round(avg_latency, 3),
            }
    
    def print_summary(self) -> None:
        s = self.stats()
        print(f"\n  Proxy Pool Statistics")
        print(f"  {'─' * 40}")
        print(f"  Total:     {s['total']}")
        print(f"  By Status: {s['by_status']}")
        print(f"  By Type:   {s['by_type']}")
        print(f"  Avg Latency: {s['avg_latency']:.3f}s")
        print(f"  Total Uses: {s['total_uses']}")
        print()
