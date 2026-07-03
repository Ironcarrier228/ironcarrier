#!/usr/bin/env python3
"""
TUI Panels
Individual panel builders for TUI layout
"""

from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.layout import Layout
from rich import box


class StatusPanel:
    """Status indicator panel"""
    
    @staticmethod
    def build(online: bool = True, message: str = "") -> Panel:
        status = "[green]● ONLINE[/green]" if online else "[red]● OFFLINE[/red]"
        text = Text(f" {status}  {message}")
        return Panel(text, box=box.SIMPLE_HEAVY)


class AgentsPanel:
    """Agents list panel"""
    
    @staticmethod
    def build(agents: list) -> Panel:
        if not agents:
            return Panel("[dim]No agents[/dim]", title="Agents", box=box.ROUNDED)
        
        table = Table(box=None, show_header=True, header_style="bold dim")
        table.add_column("ID", style="cyan", width=14)
        table.add_column("Host", width=15)
        table.add_column("OS", width=10)
        table.add_column("IP", width=15)
        table.add_column("User", width=10)
        
        for a in agents[:15]:
            agent_id = a.get('agent_id', '')[:12] + ".."
            hostname = a.get('hostname', '')[:14]
            os_name = a.get('os', '')[:9]
            ip = a.get('ip', '')[:14]
            user = a.get('user', '')[:9]
            table.add_row(agent_id, hostname, os_name, ip, user)
        
        return Panel(table, title=f"Agents ({len(agents)})", box=box.ROUNDED)


class AttacksPanel:
    """Active attacks panel"""
    
    @staticmethod
    def build(jobs: list) -> Panel:
        if not jobs:
            return Panel("[dim]No attacks[/dim]", title="Attacks", box=box.ROUNDED)
        
        table = Table(box=None, show_header=True, header_style="bold dim")
        table.add_column("Job", style="magenta", width=10)
        table.add_column("Vector", width=12)
        table.add_column("Target", width=18)
        table.add_column("Status", width=10)
        
        for j in jobs[:15]:
            job_id = j.get('job_id', '')[:9]
            vector = j.get('vector', '')[:11]
            target = f"{j.get('target', '')}:{j.get('port', '')}"[:17]
            status = j.get('status', '')
            
            if status == 'running':
                status_str = "[green]RUNNING[/green]"
            elif status == 'completed':
                status_str = "[dim]DONE[/dim]"
            else:
                status_str = f"[yellow]{status.upper()}[/yellow]"
            
            table.add_row(job_id, vector, target, status_str)
        
        return Panel(table, title=f"Attacks ({len(jobs)})", box=box.ROUNDED)


class LogPanel:
    """Log output panel"""
    
    def __init__(self, max_lines: int = 100):
        self.max_lines = max_lines
        self._entries = []
    
    def add(self, level: str, message: str) -> None:
        from datetime import datetime
        ts = datetime.now().strftime('%H:%M:%S')
        self._entries.append((ts, level, message))
        if len(self._entries) > self.max_lines:
            self._entries.pop(0)
    
    def build(self) -> Panel:
        if not self._entries:
            return Panel("[dim]Waiting for events...[/dim]", title="Logs", box=box.ROUNDED)
        
        lines = []
        for ts, level, msg in self._entries[-20:]:
            if level == 'info':
                lines.append(f"[dim]{ts}[/dim] [blue]INFO[/blue]  {msg}")
            elif level == 'warn':
                lines.append(f"[dim]{ts}[/dim] [yellow]WARN[/yellow] {msg}")
            elif level == 'error':
                lines.append(f"[dim]{ts}[/dim] [red]ERROR[/red] {msg}")
            else:
                lines.append(f"[dim]{ts}[/dim] {msg}")
        
        content = "\n".join(lines)
        return Panel(content, title="Logs", box=box.ROUNDED)
