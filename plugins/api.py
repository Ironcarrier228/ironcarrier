#!/usr/bin/env python3
"""
Plugin API
Base classes and interfaces for plugin development
"""

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class PluginPriority(Enum):
    HIGHEST = 0
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


class PluginState(Enum):
    LOADED = "loaded"
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PluginMetadata:
    """Plugin metadata descriptor"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    priority: PluginPriority = PluginPriority.NORMAL
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict = field(default_factory=dict)


class PluginContext:
    """Context object passed to plugins for C2/Engine interaction"""
    
    def __init__(self):
        self.c2_server = None
        self.engine = None
        self.config = {}
        self.logger = None
        self._event_handlers: Dict[str, List[Callable]] = {}
    
    def emit(self, event: str, data: Any = None) -> None:
        """Emit event to registered handlers"""
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception:
                pass
    
    def on(self, event: str, handler: Callable) -> None:
        """Register event handler"""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    def off(self, event: str, handler: Callable = None) -> None:
        """Remove event handler"""
        if handler:
            self._event_handlers.get(event, []).remove(handler)
        else:
            self._event_handlers.pop(event, None)
    
    def get_agent(self, agent_id: str):
        """Get agent from C2 server"""
        if self.c2_server:
            return self.c2_server.get_agent(agent_id)
        return None
    
    def get_agents(self) -> List:
        """Get all agents"""
        if self.c2_server:
            return self.c2_server.get_agents()
        return []
    
    def send_to_agent(self, agent_id: str, message) -> bool:
        """Send message to agent"""
        if self.c2_server:
            return self.c2_server.send_to_agent(agent_id, message)
        return False
    
    def broadcast(self, message) -> int:
        """Broadcast to all agents"""
        if self.c2_server:
            return self.c2_server.broadcast(message)
        return 0
    
    def log(self, level: str, message: str) -> None:
        """Log message"""
        if self.logger:
            getattr(self.logger, level.lower(), self.logger.info)(f"[{self.__class__.__name__}] {message}")
        else:
            print(f"[{level}] {message}")


class PluginInterface(ABC):
    """Base plugin interface - all plugins must implement this"""
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        pass
    
    @abstractmethod
    def on_load(self, context: PluginContext) -> None:
        """Called when plugin is loaded"""
        pass
    
    @abstractmethod
    def on_unload(self) -> None:
        """Called when plugin is unloaded"""
        pass
    
    def on_attack_start(self, job: Any) -> None:
        """Called when attack starts"""
        pass
    
    def on_attack_end(self, stats: Dict) -> None:
        """Called when attack ends"""
        pass
    
    def on_attack_stats(self, stats: Dict) -> None:
        """Called with periodic stats updates"""
        pass
    
    def on_agent_connect(self, agent: Any) -> None:
        """Called when agent connects"""
        pass
    
    def on_agent_disconnect(self, agent_id: str) -> None:
        """Called when agent disconnects"""
        pass
    
    def on_message(self, agent_id: str, message: Any) -> None:
        """Called when message received from agent"""
        pass
    
    def on_shell_output(self, agent_id: str, output: str, exit_code: int) -> None:
        """Called when shell command output received"""
        pass
    
    def on_error(self, error: Exception) -> None:
        """Called on plugin error"""
        pass
    
    def get_config(self) -> Dict:
        """Return plugin configuration"""
        return {}
    
    def set_config(self, config: Dict) -> None:
        """Update plugin configuration"""
        pass
    
    def get_commands(self) -> Dict[str, Callable]:
        """Return custom commands {name: handler}"""
        return {}


class PluginConfig:
    """Plugin configuration manager"""
    
    def __init__(self, plugin_name: str, config: Dict = None):
        self.plugin_name = plugin_name
        self._config = config or {}
        self._defaults = {}
        self._callbacks: List[Callable] = []
    
    def set_default(self, key: str, value: Any) -> 'PluginConfig':
        """Set default value for key"""
        self._defaults[key] = value
        if key not in self._config:
            self._config[key] = value
        return self
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value"""
        return self._config.get(key, self._defaults.get(key, default))
    
    def set(self, key: str, value: Any) -> None:
        """Set config value"""
        old = self._config.get(key)
        self._config[key] = value
        
        for callback in self._callbacks:
            try:
                callback(key, old, value)
            except Exception:
                pass
    
    def on_change(self, callback: Callable) -> None:
        """Register change callback"""
        self._callbacks.append(callback)
    
    def to_dict(self) -> Dict:
        return dict(self._config)
    
    def load(self, config: Dict) -> None:
        """Load config from dict"""
        self._config.update(config)
    
    def save(self) -> Dict:
        """Export config"""
        return self.to_dict()


class PluginStateHolder:
    """Manages plugin runtime state"""
    
    def __init__(self):
        self._state = {}
        self._lock = threading.Lock()
    
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._state[key] = value
    
    def increment(self, key: str, amount: int = 1) -> int:
        with self._lock:
            self._state[key] = self._state.get(key, 0) + amount
            return self._state[key]
    
    def delete(self, key: str) -> None:
        with self._lock:
            self._state.pop(key, None)
    
    def clear(self) -> None:
        with self._lock:
            self._state.clear()
    
    def to_dict(self) -> Dict:
        with self._lock:
            return dict(self._state)


class HookPoint:
    """Hook point for plugin system - manages callback chains"""
    
    def __init__(self, name: str):
        self.name = name
        self._handlers: List[tuple] = []  # (priority, handler)
        self._lock = threading.Lock()
    
    def register(self, handler: Callable, priority: int = 50) -> None:
        """Register handler with priority (lower = earlier)"""
        with self._lock:
            self._handlers.append((priority, handler))
            self._handlers.sort(key=lambda x: x[0])
    
    def unregister(self, handler: Callable) -> None:
        """Remove handler"""
        with self._lock:
            self._handlers = [(p, h) for p, h in self._handlers if h != handler]
    
    def call(self, *args, **kwargs) -> Any:
        """Call all handlers in priority order"""
        results = []
        with self._lock:
            handlers = list(self._handlers)
        
        for priority, handler in handlers:
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                results.append(None)
        
        return results
    
    def call_until(self, predicate, *args, **kwargs) -> Any:
        """Call handlers until predicate returns True"""
        with self._lock:
            handlers = list(self._handlers)
        
        for priority, handler in handlers:
            try:
                result = handler(*args, **kwargs)
                if predicate(result):
                    return result
            except Exception:
                continue
        
        return None
    
    @property
    def handler_count(self) -> int:
        with self._lock:
            return len(self._handlers)


class HookRegistry:
    """Registry of all hook points"""
    
    def __init__(self):
        self._hooks: Dict[str, HookPoint] = {}
        self._lock = threading.Lock()
    
    def get_hook(self, name: str) -> HookPoint:
        """Get or create hook point"""
        with self._lock:
            if name not in self._hooks:
                self._hooks[name] = HookPoint(name)
            return self._hooks[name]
    
    def register(self, hook_name: str, handler: Callable, priority: int = 50) -> None:
        """Register handler to hook"""
        hook = self.get_hook(hook_name)
        hook.register(handler, priority)
    
    def unregister(self, hook_name: str, handler: Callable) -> None:
        """Unregister handler from hook"""
        hook = self.get_hook(hook_name)
        hook.unregister(handler)
    
    def call(self, hook_name: str, *args, **kwargs) -> Any:
        """Call all handlers on hook"""
        hook = self.get_hook(hook_name)
        return hook.call(*args, **kwargs)
    
    def list_hooks(self) -> Dict[str, int]:
        """List all hooks with handler counts"""
        with self._lock:
            return {name: hook.handler_count for name, hook in self._hooks.items()}
