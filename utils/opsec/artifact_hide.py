#!/usr/bin/env python3
"""
Artifact Hiding
Hide files, directories, and other artifacts
"""

import os
import time
import shutil
from pathlib import Path
from typing import List, Optional


class ArtifactHider:
    """Hide files and artifacts"""
    
    def __init__(self):
        self._hidden = []
    
    def hide_file(self, filepath: str, new_name: Optional[str] = None) -> Optional[str]:
        """Hide file by renaming with dot prefix"""
        path = Path(filepath).expanduser()
        
        if not path.exists():
            return None
        
        if new_name:
            new_path = path.parent / new_name
        else:
            if path.name.startswith('.'):
                return str(path)
            new_path = path.parent / f".{path.name}"
        
        try:
            path.rename(new_path)
            self._hidden.append(str(new_path))
            return str(new_path)
        except Exception:
            return None
    
    def hide_directory(self, dirpath: str, recursive: bool = False) -> Optional[str]:
        """Hide directory by renaming with dot prefix"""
        path = Path(dirpath).expanduser()
        
        if not path.exists() or path.name.startswith('.'):
            return str(path)
        
        new_path = path.parent / f".{path.name}"
        
        try:
            path.rename(new_path)
            self._hidden.append(str(new_path))
            return str(new_path)
        except Exception:
            return None
    
    def hide_artifacts(self, paths: List[str]) -> List[str]:
        """Hide multiple files/directories"""
        hidden = []
        for p in paths:
            path = Path(p).expanduser()
            if path.is_dir():
                result = self.hide_directory(str(path), recursive=True)
            else:
                result = self.hide_file(str(path))
            if result:
                hidden.append(result)
        return hidden
    
    def hide_ironcarrier_artifacts(self, base_dir: str = '.') -> List[str]:
        """Hide IronCarrier-specific artifacts"""
        artifacts = [
            'ironcarrier/',
            'logs/',
            '*.log',
            '*.log.*',
            'reflectors/',
            'wordlists/',
            'configs/default.yaml',
            '*.pyc',
            '__pycache__/',
            '.git/',
        ]
        
        hidden = []
        base = Path(base_dir).expanduser()
        
        for pattern in artifacts:
            for path in base.rglob(pattern):
                result = None
                if path.is_dir():
                    result = self.hide_directory(str(path))
                elif path.is_file():
                    result = self.hide_file(str(path))
                if result:
                    hidden.append(result)
        
        return hidden
    
    def set_immutable(self, filepath: str) -> bool:
        """Make file immutable (Linux)"""
        try:
            os.system(f'chattr +i "{filepath}"')
            return True
        except Exception:
            return False
    
    def set_hidden(self, filepath: str) -> bool:
        """Set hidden attribute (Linux)"""
        try:
            os.system(f'chattr +h "{filepath}"')
            return True
        except Exception:
            return False
    
    def set_unchangeable(self, filepath: str) -> bool:
        """Make file append-only (Linux)"""
        try:
            os.chmod(filepath, 0o444)
            os.system(f'chattr +a "{filepath}"')
            return True
        def return False
    
    def get_hidden_list(self) -> List[str]:
        """Get list of hidden artifacts"""
        return list(self._hidden)
    
    def unhide_all(self) -> int:
        """Unhide all hidden artifacts"""
        count = 0
        for path_str in self._hidden:
            path = Path(path_str)
            if path.exists() and path.name.startswith('.'):
                try:
                    new_path = path.parent / path.name[1:]
                    path.rename(new_path)
                    count += 1
                except Exception:
                    pass
        self._hidden.clear()
        return count
