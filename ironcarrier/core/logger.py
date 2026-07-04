#!/usr/bin/env python3
"""
IronCarrier Logger
Rotating file logger with optional encryption and structured attack logs
"""

import os
import sys
import json
import gzip
import logging
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional, List


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured log entries"""
    
    def __init__(self, include_extras: bool = True):
        super().__init__()
        self.include_extras = include_extras
    
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            'ts': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'msg': record.getMessage(),
        }
        
        if self.include_extras and hasattr(record, 'extra_data'):
            entry.update(record.extra_data)
        
        if record.exc_info and record.exc_info[0] is not None:
            entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(entry)


class AttackLogFormatter(logging.Formatter):
    """Dedicated formatter for attack completion records"""
    
    def format(self, record: logging.LogRecord) -> str:
        if hasattr(record, 'attack_data'):
            return json.dumps(record.attack_data)
        return self.formatMessage(record)


class Logger:
    """Centralized logging system with rotation and optional encryption"""
    
    COLORS = {
        'DEBUG': '\033[90m',
        'INFO': '\033[97m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[91m\033[1m',
        'RESET': '\033[0m',
    }
    
    def __init__(
        self,
        log_dir: str = 'logs',
        max_size_mb: int = 100,
        encrypt: bool = False,
        enc_key: Optional[bytes] = None,
        console: bool = True,
        level: str = 'DEBUG'
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.encrypt = encrypt
        self._enc_key = enc_key
        self._fernet = None
        
        if encrypt:
            self._init_encryption(enc_key)
        
        self._logger = logging.getLogger('ironcarrier')
        self._logger.setLevel(getattr(logging, level.upper(), logging.DEBUG))
        self._logger.handlers.clear()
        
        self._handlers: List[logging.Handler] = []
        self._session = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if console:
            self._add_console_handler()
        
        self._add_file_handler(f'ironcarrier_{self._session}.log', StructuredFormatter())
        self._add_file_handler(f'attacks_{self._session}.log', AttackLogFormatter(), level=logging.INFO)
    
    def _init_encryption(self, key: Optional[bytes]) -> None:
        """Initialize Fernet encryption"""
        try:
            from cryptography.fernet import Fernet
            self._fernet = Fernet(key or Fernet.generate_key())
            if key is None and self._fernet:
                self._enc_key = self._fernet._signing_key
        except ImportError:
            self.encrypt = False
    
    def _add_console_handler(self) -> None:
        """Add colored console output"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        class ColorFormatter(logging.Formatter):
            def format(self, record):
                color = Logger.COLORS.get(record.levelname, Logger.COLORS['RESET'])
                reset = Logger.COLORS['RESET']
                ts = self.formatTime(record, '%H:%M:%S')
                return f"{color}[{ts}] [{record.levelname:<8}]{reset} {record.getMessage()}"
        
        handler.setFormatter(ColorFormatter())
        self._logger.addHandler(handler)
        self._handlers.append(handler)
    
    def _add_file_handler(self, filename: str, formatter: logging.Formatter, level: int = logging.DEBUG) -> None:
        """Add rotating file handler"""
        path = self.log_dir / filename
        handler = RotatingFileHandler(
            path,
            maxBytes=self.log_dir.parent.stat().st_size if False else max_size_mb * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        handler.setLevel(level)
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)
        self._handlers.append(handler)
    
    def _make_record(self, level: int, msg: str, extra: Dict = None) -> logging.LogRecord:
        """Create log record with optional extra data"""
        record = self._logger.makeRecord(
            'ironcarrier', level, '', 0, msg, (), None
        )
        if extra:
            record.extra_data = extra
        return record
    
    def debug(self, msg: str) -> None:
        self._logger.debug(msg)
    
    def info(self, msg: str) -> None:
        self._logger.info(msg)
    
    def warning(self, msg: str) -> None:
        self._logger.warning(msg)
    
    def error(self, msg: str) -> None:
        self._logger.error(msg)
    
    def critical(self, msg: str) -> None:
        self._logger.critical(msg)
    
    def structured(self, msg: str, data: Dict[str, Any]) -> None:
        """Log structured data entry"""
        record = self._make_record(logging.INFO, msg, data)
        for handler in self._handlers:
            if isinstance(handler.formatter, StructuredFormatter):
                handler.handle(record)
    
    def log_attack(self, target: str, vector: str, duration: float, stats: Dict[str, Any]) -> None:
        """Log attack completion with full metrics"""
        record = self._make_record(
            logging.INFO,
            '',
            {
                'type': 'attack_complete',
                'target': target,
                'vector': vector,
                'duration': round(duration, 3),
                'stats': stats,
                'timestamp': datetime.now().isoformat(),
            }
        )
        record.attack_data = record.extra_data
        
        for handler in self._handlers:
            if isinstance(handler.formatter, AttackLogFormatter):
                handler.handle(record)
    
    def _encrypt_file(self, path: Path) -> None:
        """Encrypt a log file in place"""
        if not self._fernet:
            return
        raw = path.read_bytes()
        encrypted = self._fernet.encrypt(raw)
        out = path.with_suffix(path.suffix + '.enc')
        out.write_bytes(encrypted)
        path.unlink()
    
    def _compress_rotated(self) -> None:
        """Compress and optionally encrypt rotated log files"""
        for f in self.log_dir.glob('*.log.*'):
            if f.suffix in ('.gz', '.enc'):
                continue
            compressed = f.with_suffix(f.suffix + '.gz')
            with open(f, 'rb') as src:
                with gzip.open(compressed, 'wb') as dst:
                    dst.writelines(src)
            f.unlink()
            if self.encrypt:
                self._encrypt_file(compressed)
    
    def rotate(self) -> None:
        """Force rotation on all file handlers"""
        for h in self._handlers:
            if isinstance(h, RotatingFileHandler):
                h.doRollover()
        self._compress_rotated()
    
    def close(self) -> None:
        """Flush and close all handlers"""
        self._compress_rotated()
        for h in self._handlers:
            h.close()
            self._logger.removeHandler(h)
        self._handlers.clear()
