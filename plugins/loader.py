#!/usr/bin/env python3
"""
Plugin Loader
Dynamic plugin discovery, loading, and lifecycle management
"""

import os
import sys
import importlib
import importlib.util
import inspect
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Type
from dataclasses import dataclass, field

from .api import (
    PluginInterface, PluginMetadata, PluginContext, PluginState,
    PluginPriority, PluginConfig, PluginStateHolder
)


@dataclass
class LoadedPlugin:
    """Container for a loaded plugin instance"""
    name: str
    instance: PluginInterface
    metadata: PluginMetadata
    state: PluginState = PluginState.LOADED
    config: PluginConfig = None
    state_holder: PluginStateHolder = None
    module: object = None
    load_time: float = field(default_factory=time.time)
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = PluginConfig(self.name)
        if self.state_holder is None:
            self.state_holder = PluginStateHolder()


class PluginLoader:
    """Dynamic plugin loader and manager"""
    
    def __init__(self, plugin_dirs: List[str] = None, context: PluginContext = None):
        self.plugin_dirs = plugin_dirs or ['plugins', 'ironcarrier/plugins/examples']
        self.context = context or PluginContext()
        self._plugins: Dict[str, LoadedPlugin] = {}
        self._lock = threading.Lock()
        self._watch_thread: Optional[threading.Thread] = None
        self._running = False
    
    def discover(self, directories: List[str] = None) -> List[Path]:
        """Find all potential plugin files"""
        dirs = directories or self.plugin_dirs
        plugin_files = []
        
        for d in dirs:
            path = Path(d)
            if not path.exists():
                continue
            
            if path.is_dir():
                for py_file in path.rglob('*.py'):
                    if py_file.name.startswith('_'):
                        continue
                    if py_file.name == '__init__.py':
                        continue
                    plugin_files.append(py_file)
        
        return plugin_files
    
    def _find_plugin_class(self, module) -> Optional[Type[PluginInterface]]:
        """Find PluginInterface subclass in module"""
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, PluginInterface) and obj != PluginInterface:
                return obj
        return None
    
    def _find_plugin_instance(self, module) -> Optional[PluginInterface]:
        """Find plugin instance or class in module"""
        # Check for instance first
        for name, obj in inspect.getmembers(module):
            if isinstance(obj, PluginInterface):
                return obj
            if inspect.isclass(obj) and issubclass(obj, PluginInterface) and obj != PluginInterface:
                return obj()
        return None
    
    def load_from_file(self, filepath: str, config: Dict = None) -> Optional[str]:
        """Load plugin from Python file"""
        filepath = Path(filepath)
        if not filepath.exists():
            return None
        
        module_name = f"plugin_{filepath.stem}"
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        
        if not spec or not spec.loader:
            return None
        
        try:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            plugin = self._find_plugin_instance(module)
            if not plugin:
                return None
            
            return self._register_plugin(plugin, module, config)
        except Exception as e:
            return None
    
    def load_from_module(self, module_path: str, config: Dict = None) -> Optional[str]:
        """Load plugin from module path (e.g., 'ironcarrier.plugins.examples.telegram')"""
        try:
            module = importlib.import_module(module_path)
            plugin = self._find_plugin_instance(module)
            if not plugin:
                return None
            
            return self._register_plugin(plugin, module, config)
        except Exception as e:
            return None
    
    def _register_plugin(self, plugin: PluginInterface, module: object, config: Dict = None) -> str:
        """Register loaded plugin"""
        metadata = plugin.get_metadata()
        name = metadata.name
        
        with self._lock:
            if name in self._plugins:
                self.unload(name)
            
            loaded = LoadedPlugin(
                name=name,
                instance=plugin,
                metadata=metadata,
                state=PluginState.LOADED,
                module=module,
            )
            
            if config:
                loaded.config.load(config)
            
            self._plugins[name] = loaded
        
        return name
    
    def load_all(self, directories: List[str] = None) -> Dict[str, bool]:
        """Load all plugins from directories"""
        files = self.discover(directories)
        results = {}
        
        for filepath in files:
            name = self.load_from_file(str(filepath))
            if name:
                results[name] = True
            else:
                results[filepath.stem] = False
        
        return results
    
    def initialize(self, name: str) -> bool:
        """Initialize a loaded plugin"""
        with self._lock:
            plugin = self._plugins.get(name)
            if not plugin or plugin.state != PluginState.LOADED:
                return False
            
            try:
                plugin.instance.on_load(self.context)
                plugin.state = PluginState.INITIALIZED
                return True
            except Exception as e:
                plugin.state = PluginState.ERROR
                plugin.error = str(e)
                return False
    
    def initialize_all(self) -> Dict[str, bool]:
        """Initialize all loaded plugins"""
        results = {}
        with self._lock:
            for name, plugin in self._plugins.items():
                if plugin.state == PluginState.LOADED:
                    results[name] = self.initialize(name)
        return results
    
    def start(self, name: str) -> bool:
        """Start a plugin"""
        with self._lock:
            plugin = self._plugins.get(name)
            if not plugin:
                return False
            
            if plugin.state == PluginState.LOADED:
                if not self.initialize(name):
                    return False
            
            plugin.state = PluginState.RUNNING
            return True
    
    def stop(self, name: str) -> bool:
        """Stop a plugin"""
        with self._lock:
            plugin = self._plugins.get(name)
            if not plugin:
                return False
            plugin.state = PluginState.STOPPED
            return True
    
    def unload(self, name: str) -> bool:
        """Unload a plugin"""
        with self._lock:
            plugin = self._plugins.get(name)
            if not plugin:
                return False
            
            try:
                plugin.instance.on_unload()
            except Exception:
                pass
            
            if plugin.module and hasattr(plugin.module, '__name__'):
                sys.modules.pop(plugin.module.__name__, None)
            
            del self._plugins[name]
            return True
    
    def reload(self, name: str) -> bool:
        """Reload a plugin"""
        plugin = self._plugins.get(name)
        if not plugin or not plugin.module:
            return False
        
        filepath = getattr(plugin.module, '__file__', None)
        if not filepath:
            return False
        
        config = plugin.config.to_dict()
        self.unload(name)
        new_name = self.load_from_file(filepath, config)
        
        if new_name:
            self.initialize(new_name)
            return True
        return False
    
    def get_plugin(self, name: str) -> Optional[LoadedPlugin]:
        """Get loaded plugin"""
        with self._lock:
            return self._plugins.get(name)
    
    def get_all(self) -> Dict[str, LoadedPlugin]:
        """Get all loaded plugins"""
        with self._lock:
            return dict(self._plugins)
    
    def list_plugins(self) -> List[Dict]:
        """List all plugins with metadata"""
        with self._lock:
            return [
                {
                    'name': p.name,
                    'version': p.metadata.version,
                    'description': p.metadata.description,
                    'author': p.metadata.author,
                    'state': p.state.value,
                    'priority': p.metadata.priority.name,
                    'tags': p.metadata.tags,
                    'error': p.error,
                    'load_time': p.load_time,
                }
                for p in self._plugins.values()
            ]
    
    def get_by_tag(self, tag: str) -> List[LoadedPlugin]:
        """Get plugins by tag"""
        with self._lock:
            return [p for p in self._plugins.values() if tag in p.metadata.tags]
    
    def get_by_priority(self, reverse: bool = False) -> List[LoadedPlugin]:
        """Get plugins sorted by priority"""
        with self._lock:
            plugins = list(self._plugins.values())
            return sorted(plugins, key=lambda p: p.metadata.priority.value, reverse=reverse)
    
    def call_hook(self, hook_name: str, *args, **kwargs) -> List:
        """Call hook on all running plugins"""
        results = []
        with self._lock:
            for plugin in self._plugins.values():
                if plugin.state == PluginState.RUNNING:
                    handler = getattr(plugin.instance, hook_name, None)
                    if handler and callable(handler):
                        try:
                            result = handler(*args, **kwargs)
                            results.append((plugin.name, result))
                        except Exception as e:
                            results.append((plugin.name, None))
        return results
    
    def on_attack_start(self, job: Any) -> None:
        """Notify plugins of attack start"""
        self.call_hook('on_attack_start', job)
    
    def on_attack_end(self, stats: Dict) -> None:
        """Notify plugins of attack end"""
        self.call_hook('on_attack_end', stats)
    
    def on_attack_stats(self, stats: Dict) -> None:
        """Notify plugins of stats update"""
        self.call_hook('on_attack_stats', stats)
    
    def on_agent_connect(self, agent: Any) -> None:
        """Notify plugins of agent connect"""
        self.call_hook('on_agent_connect', agent)
    
    def on_agent_disconnect(self, agent_id: str) -> None:
        """Notify plugins of agent disconnect"""
        self.call_hook('on_agent_disconnect', agent_id)
    
    def on_message(self, agent_id: str, message: Any) -> None:
        """Notify plugins of message"""
        self.call_hook('on_message', agent_id, message)
    
    def start_watch(self, interval: float = 5.0) -> None:
        """Start file watcher for hot reload"""
        self._running = True
        
        def _watch():
            last_mtimes = {}
            while self._running:
                for name, plugin in self.get_all().items():
                    if plugin.module and hasattr(plugin.module, '__file__'):
                        filepath = plugin.module.__file__
                        try:
                            mtime = os.path.getmtime(filepath)
                            if filepath in last_mtimes and mtime != last_mtimes[filepath]:
                                self.context.log('info', f"Reloading plugin: {name}")
                                self.reload(name)
                            last_mtimes[filepath] = mtime
                        except Exception:
                            pass
                time.sleep(interval)
        
        self._watch_thread = threading.Thread(target=_watch, daemon=True)
        self._watch_thread.start()
    
    def stop_watch(self) -> None:
        """Stop file watcher"""
        self._running = False
