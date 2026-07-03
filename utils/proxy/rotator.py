#!/usrthon/env python3
"""
Proxy Rotator
Thread-safe proxy rotation with multiple strategies
"""

import random
import threading
import time
from typing import Dict, Optional, List, Tuple
from enum import Enum

from .manager import ProxyManager, Proxy, ProxyStatus, ProxyType


class RotationStrategy(Enum):
    ROUND_ROBIN = 'round_robin'
    RANDOM = 'random'
    LEAST_USED = 'least_used'
    FASTEST = 'fastest'
    GEO_RANDOM = 'geo_random'


class ProxyRotator:
    """Thread-safe proxy rotation"""
    
    def __init__(self, manager: ProxyManager, strategy: RotationStrategy = RotationStrategy.ROUND_ROBIN,
                 max_uses: int = 0, preferred_countries: List[str] = None,
                 exclude_countries: List[str] = None):
        self.manager = manager
        self.strategy = strategy
        self.max_uses = max_uses
        self.preferred_countries = preferred_countries or []
        self.exclude_countries = exclude_countries or []
        
        self._index = 0
        self._lock = threading.Lock()
        self._use_counts: Dict[str, int] = {}
        self._cooldown: Dict[str, float] = {}
        self._cooldown_seconds = 30.0
    
    def _is_available(self, proxy: Proxy) -> bool:
        if proxy.status != ProxyStatus.ALIVE:
            return False
        if self.max_uses > 0 and proxy.use_count >= self.max_uses:
            return False
        if proxy.country in self.exclude_countries:
            return False
        key = f"{proxy.address}:{proxy.port}"
        if key in self._cooldown:
            if time.time() - self._cooldown[key] < self._cooldown_seconds:
                return False
        return True
    
    def _get_pool(self) -> List[Proxy]:
        pool = self.manager.get_alive()
        if self.preferred_countries:
            preferred = [p for p in pool if p.country in self.preferred_countries]
            if preferred:
                return preferred
        return [p for p in pool if self._is_available(p)]
    
    def get(self) -> Optional[Proxy]:
        """Get next proxy based on strategy"""
        with self._lock:
            pool = self._get_pool()
            if not pool:
                return None
            
            if self.strategy == RotationStrategy.ROUND_ROBIN:
                proxy = self._round_robin(pool)
            elif self.strategy == RotationStrategy.RANDOM:
                proxy = self._random(pool)
            elif self.strategy == RotationStrategy.LEAST_USED:
                proxy = self._least_used(pool)
            elif self.strategy == RotationStrategy.FASTEST:
                proxy = self._fastest(pool)
            elif self.strategy == RotationStrategy.GEO_RANDOM:
                proxy = self._geo_random(pool)
            else:
                proxy = random.choice(pool)
            
            if proxy:
                key = f"{proxy.address}:{proxy.port}"
                self._use_counts[key] = self._use_counts.get(key, 0) + 1
                self.manager.increment_use(proxy.address, proxy.port)
            
            return proxy
    
    def get_multiple(self, count: int) -> List[Proxy]:
        """Get multiple unique proxies"""
        proxies = []
        with self._lock:
            pool = self._get_pool()
            random.shuffle(pool)
            
            for proxy in pool:
                if len(proxies) >= count:
                    break
                key = f"{proxy.address}:{proxy.port}"
                if key not in {f"{p.address}:{p.port}" for p in proxies}:
                    proxies.append(proxy)
                    self._use_counts[key] = self._use_counts.get(key, 0) + 1
                    self.manager.increment_use(proxy.address, proxy.port)
        
        return proxies
    
    def _round_robin(self, pool: List[Proxy]) -> Optional[Proxy]:
        if not pool:
            return None
        proxy = pool[self._index % len(pool)]
        self._index += 1
        return proxy
    
    def _random(self, pool: List[Proxy]) -> Optional[Proxy]:
        return random.choice(pool) if pool else None
    
    def _least_used(self, pool: List[Proxy]) -> Optional[Proxy]:
        if not pool:
            return None
        return min(pool, key=lambda p: p.use_count)
    
    def _fastest(self, pool: List[Proxy]) -> Optional[Proxy]:
        valid = [p for p in pool if p.latency > 0]
        if not valid:
            return random.choice(pool) if pool else None
        return min(valid, key=lambda p: p.latency)
    
    def _geo_random(self, pool: List[Proxy]) -> Optional[Proxy]:
        if not pool:
            return None
        countries = list(set(p.country for p in pool if p.country))
        if countries:
            country = random.choice(countries)
            country_pool = [p for p in pool if p.country == country]
            if country_pool:
                return random.choice(country_pool)
        return random.choice(pool)
    
    def report_failure(self, proxy: Proxy) -> None:
        """Report proxy failure, add to cooldown"""
        with self._lock:
            key = f"{proxy.address}:{proxy.port}"
            self._cooldown[key] = time.time()
            self.manager.mark_dead(proxy.address, proxy.port)
    
    def report_success(self, proxy: Proxy) -> None:
        """Report proxy success, remove from cooldown"""
        with self._lock:
            key = f"{proxy.address}:{proxy.port}"
            self._cooldown.pop(key, None)
            self.manager.update_proxy(proxy.address, proxy.port, status=ProxyStatus.ALIVE)
    
    def set_strategy(self, strategy: RotationStrategy) -> None:
        with self._lock:
            self.strategy = strategy
            self._index = 0
    
    def set_max_uses(self, max_uses: int) -> None:
        self.max_uses = max_uses
    
    def set_preferred_countries(self, countries: List[str]) -> None:
        self.preferred_countries = countries
    
    def set_exclude_countries(self, countries: List[str]) -> None:
        self.exclude_countries = countries
    
    def get_stats(self) -> Dict:
        with self._lock:
            return {
                'strategy': self.strategy.value,
                'max_uses': self.max_uses,
                'total_rotations': sum(self._use_counts.values()),
                'in_cooldown': len(self._cooldown),
                'preferred_countries': self.preferred_countries,
                'exclude_countries': self.exclude_countries,
            }
