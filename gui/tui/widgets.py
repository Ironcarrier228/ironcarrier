#!/usr/bin/env python3
"""
TUI Widgets
Reusable UI components
"""

from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.progress import BarColumn, TextColumn, Progress
from rich import box


class AgentTable:
    """Agent listing table"""
    
    def __init__(self, agents: list, compact: bool = False):
        self.agents = agents
        self.compact = compact
    
    def build(self) -> Table:
        table = Table(box=None, show_header=True, header_style="bold dim", expand=True)
        
        if self.compact:
            table.add_column("ID", style="cyan", width=12)
            table.add_column("Host", width=12)
            table.add_column("IP", width=14)
            table.add_column("OS", width=8)
        else:
            table.add_column("ID", style="cyan", width=14)
            table.add_column("Hostname", width=16)
            table.add_column("OS", width=10)
            table.add_column("Arch", width=8)
            table.add_column("IP", width=15)
            table.add_column("User", width=10)
            table.add_column("Privs", width=6)
        
        for a in self.agents:
            agent_id = a.get('agent_id', '')[:13] + ".." if len(a.get('agent_id', '')) > 13 else a.get('agent_id', '')
            hostname = a.get('hostname', '')[:15]
            os_name = a.get('os', '')[:9]
            arch = a.get('arch', '')[:7]
            ip = a.get('ip', '')[:14]
            user = a.get('user', '')[:9]
            privs = a.get('privileges', '')
            
            if privs == 'root':
                privs_str = "[red]root[/red]"
            else:
                privs_str = f"[dim]{privs}[/dim]"
            
            if self.compact:
                table.add_row(agent_id, hostname, ip, os_name)
            else:
                table.add_row(agent_id, hostname, os_name, arch, ip, user, privs_str)
        
        return table


class AttackTable:
    """Attack listing table"""
    
    def __init__(self, jobs: list, compact: bool = False):
        self.jobs = jobs
        self.compact = compact
    
    def build(self) -> Table:
        table = Table(box=None, show_header=True, header_style="bold dim", expand=True)
        
        if self.compact:
            table.add_column("Job", style="magenta", width=8)
            table.add_column("Vector", width=10)
            table.add_column("Target", width=20)
            table.add_column("Status", width=8)
        else:
            table.add_column("Job ID", style="magenta", width=10)
            table.add_column("Agent", style="cyan", width=14)
            table.add_column("Vector", width=12)
            table.add_column("Target", width=20)
            table.add_column("Duration", width=8)
            table.add_column("Status", width=10)
        
        for j in self.jobs:
            job_id = j.get('job_id', '')[:9]
            agent_id = j.get('agent_id', '')[:13] + ".."
            vector = j.get('vector', '')[:11]
            target = f"{j.get('target', '')}:{j.get('port', '')}"
            duration = f"{j.get('duration', 0)}s"
            status = j.get('status', '')
            
            if status == 'running':
                status_str = "[green]● RUN[/green]"
            elif status == 'completed':
                status_str = "[dim]✓ DONE[/dim]"
            elif status == 'stopped':
                status_str = "[yellow]■ STOP[/yellow]"
            else:
                status_str = f"[dim]{status[:8]}[/dim]"
            
            if self.compact:
                table.add_row(job_id, vector, target[:19], status_str)
            else:
                table.add_row(job_id, agent_id, vector, target[:19], duration, status_str)
        
        return table


class StatsBar:
    """Statistics summary bar"""
    
    def __init__(self, agents: int = 0, active_attacks: int = 0, total_attacks: int = 0,
                 packets: int = 0, bandwidth: float = 0.0):
        self.agents = agents
        self.active_attacks = active_attacks
        self.total_attacks = total_attacks
        self.packets = packets
        self.bandwidth = bandwidth
    
    def build(self) -> Panel:
        text = Text()
        
        text.append(" Agents: ", style="dim")
        text.append(str(self.agents), style="bold green" if self.agents > 0 else "red")
        text.append("  │  ", style="dim")
        
        text.append("Active: ", style="dim")
        text.append(str(self.active_attacks), style="bold red" if self.active_attacks > 0 else "dim")
        text.append("  │  ", style="dim")
        
        text.append("Total: ", style="dim")
        text.append(str(self.total_attacks), style="yellow")
        text.append("  │  ", style="dim")
        
        text.append("Pkts: ", style="dim")
        text.append(f"{self.packets:,}", style="cyan")
        text.append("  │  ", style="dim")
        
        text.append("BW: ", style="dim")
        text.append(f"{self.bandwidth:.2f} Mbps", style="magenta")
        
        return Panel(text, box=box.ROUNDED)


class ProgressBar:
    """Rich progress bar wrapper"""
    
    def __init__(self, description: str = "Progress", total: int = 100):
        self.progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            expand=True
        )
        self.task_id = self.progress.add_task(description, total=total)
    
    def update(self, completed: int) -> None:
        self.progress.update(self.task_id, completed=completed)
    
    def build(self) -> Progress:
        return self.progress


class TreeView:
    """Tree structure display"""
    
    @staticmethod
    def build(title: str, data: dict) -> Panel:
        from rich.tree import Tree
        tree = Tree(f"[bold]{title}[/bold]")
        
        def add_branch(node, items):
            for key, value in items.items():
                if isinstance(value, dict):
                    branch = node.add(f"[cyan]{key}[/cyan]")
                    add_branch(branch, value)
                elif isinstance(value, list):
                    branch = node.add(f"[cyan]{key}[/cyan]")
                    for item in value:
                        branch.add(f"[dim]{item}[/dim]")
                else:
                    node.add(f"[dim]{key}:[/dim] {value}")
        
        add_branch(tree, data)
        return Panel(tree, box=box.ROUNDED)
