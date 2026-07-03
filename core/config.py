#!/usr/bin/env python3
"""
IronCarrier Configuration Manager
Multi-format support (JSON/YAML/TOML) with environment variable overrides
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from copy import deepcopy


class Config:
    """Hierarchical configuration manager"""
    
    DEFAULTS = {
        'general': {
            'name': 'IronCarrier',
            'version': '2.4.0',
            'debug': False,
            'log_level': 'INFO',
        },
        'engine': {
            'max_threads': 500,
            'timeout': 10,
            'retry_count': 3,
            'retry_delay': 1.0,
        },
        'opsec': {
            'randomize_src_port': True,
            'randomize_seq': True,
            'randomize_window': True,
            'ttl': 64,
            'tos': 0,
        },
        'proxy': {
            'enabled': False,
            'file': 'reflectors/proxies.txt',
            'rotation': 'round-robin',
            'max_uses_per_proxy': 100,
            'test_on_start': True,
            'timeout': 5,
        },
        'vectors': {
            'tcp': {
                'flags': ['SYN', 'ACK', 'PSH+ACK', 'RST'],
                'payload_size': 0,
                'checksum': True,
            },
            'udp': {
                'size': 1024,
                'randomize_payload': True,
            },
            'http': {
                'method': 'GET',
                'path': '/',
                'keep_alive': True,
                'follow_redirects': False,
                'randomize_headers': True,
                'cache_bust': True,
            },
            'slowloris': {
                'headers_per_interval': 5,
                'interval': 15,
                'max_connections': 500,
            },
            'amplification': {
                'vector': 'dns',
                'reflector_file': None,
                'spoof_ip': True,
            },
        },
        'logging': {
            'enabled': True,
            'dir': 'logs/',
            'rotate_size_mb': 100,
            'encrypt': False,
            'export_formats': ['json', 'csv'],
        },
    }
    
    def __init__(self, config_path: Optional[str] = None):
        self._data = deepcopy(self.DEFAULTS)
        self._path = config_path
        
        if config_path:
            self.load(config_path)
        
        self._apply_env()
    
    def load(self, path: str) -> 'Config':
        """Load config from file, returns self for chaining"""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config not found: {p}")
        
        ext = p.suffix.lower()
        loaders = {
            '.json': self._load_json,
            '.yaml': self._load_yaml,
            '.yml': self._load_yaml,
            '.toml': self._load_toml,
        }
        
        loader = loaders.get(ext)
        if loader is None:
            raise ValueError(f"Unsupported format: {ext}")
        
        data = loader(p)
        if data:
            self._merge(self._data, data)
        
        return self
    
    def _load_json(self, path: Path) -> Dict:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_yaml(self, path: Path) -> Dict:
        try:
            import yaml
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            raise ImportError("PyYAML required: pip install pyyaml")
    
    def _load_toml(self, path: Path) -> Dict:
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                raise ImportError("tomllib or tomli required")
        
        with open(path, 'rb') as f:
            return tomllib.load(f)
    
    def _merge(self, base: Dict, override: Dict) -> None:
        """Deep merge override into base"""
        for key, val in override.items():
            # Handle nested ironcarrier wrapper
            if key == 'ironcarrier' and isinstance(val, dict):
                self._merge(base, val)
                continue
            
            if key in base and isinstance(base[key], dict) and isinstance(val, dict):
                self._merge(base[key], val)
            else:
                base[key] = val
    
    def _apply_env(self) -> None:
        """Apply IRONCARRIER_SECTION_KEY environment overrides"""
        prefix = 'IRONCARRIER_'
        
        for env_key, env_val in os.environ.items():
            if not env_key.startswith(prefix):
                continue
            
            parts = env_key[len(prefix):].lower().split('_')
            if len(parts) < 2:
                continue
            
            section, *keys = parts
            setting = '_'.join(keys)
            
            if section not in self._data:
                continue
            
            self._data[section][setting] = self._cast(env_val)
    
    def _cast(self, value: str) -> Any:
        """Cast string to appropriate Python type"""
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        if value.isdigit():
            return int(value)
        try:
            return float(value)
        except ValueError:
            pass
        if value.startswith('[') and value.endswith(']'):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return value
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get value by dot-notation path: 'vectors.tcp.flags'"""
        keys = path.split('.')
        current = self._data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def set(self, path: str, value: Any) -> None:
        """Set value by dot-notation path"""
        keys = path.split('.')
        current = self._data
        
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def save(self, path: Optional[str] = None) -> None:
        """Save current config to JSON file"""
        out = Path(path or self._path)
        if not out:
            raise ValueError("No output path specified")
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            json.dump({'ironcarrier': self._data}, f, indent=2)
    
    @property
    def raw(self) -> Dict:
        return deepcopy(self._data)
    
    def __repr__(self) -> str:
        return f"Config(sections={list(self._data.keys())})"
    
    def __getitem__(self, key: str) -> Any:
        return self._data[key]
    
    def __contains__(self, key: str) -> bool:
        return key in self._data
