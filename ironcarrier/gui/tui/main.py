#!/usr/bin/env python3
"""
Terminal UI Main
Rich-based text user interface for IronCarrier
"""

import threading
import time
from typing import Optional

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich.tree import Tree
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from .panels import StatusPanel, AgentsPanel, AttacksPanel, LogPanel
from .widgets import AgentTable, AttackTable, StatsBar


class IronCarrierTUI:
    """Main TUI application"""
    
    def __init__(self, c2_server=None):
        if not HAS_RICH:
            print("[!] Rich library required: pip install rich")
            return
        
        self.console = Console()
        self.c2_server = c2_server
        self.running = False
        self.layout = Layout()
        self._setup_layout()
        self._setup_callbacks()
    
    def _setup_layout(self) -> None:
        """Create layout structure"""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )
        
        self.layout["body"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1),
        )
        
        self.layout["left"].split(
            Layout(name="stats", size=5),
            Layout(name="agents"),
        )
        
        self.layout["right"].split(
            Layout(name="attacks"),
            Layout(name="logs"),
        )
    
    def _setup_callbacks(self) -> None:
        """Setup C2 event callbacks"""
        if not self.c2_server:
            return
        
        def on_connect(agent):
            self._refresh()
        
        def on_disconnect(agent):
            self._refresh()
        
        self.c2_server.on_agent_connect(on_connect)
        self.c2_server.on_agent_disconnect(on_disconnect)
    
    def _build_header(self) -> Panel:
        """Build header panel"""
        text = Text()
        text.append(" IRONCARRIER ", style="bold red")
        text.append("C2 ", style="dim")
        text.append("│ ", style="dim")
        text.append(f"Agents: ", style="dim")
        
        if self.c2_server:
            count = len(self.c2_server._agents)
            text.append(str(count), style="bold green" if count > 0 else "red")
        else:
            text.append("N/A", style="red")
        
        text.append(" │ ", style="dim")
        text.append("Press q to quit", style="dim")
        
        return Panel(text, box=box.HEAVY, style="dim")
    
    def _build_footer(self) -> Panel:
        """Build footer panel"""
        text = Text()
        text.append(f" [{time.strftime('%H:%M:%S')}] ", style="dim")
        text.append("Ready", style="green")
        return Panel(text, box=box.HEAVY, style="dim")
    
    def _build_stats(self) -> Panel:
        """Build stats bar"""
        if not self.c2_server:
            return Panel("[yellow]C2 Server not connected[/yellow]", box=box.ROUNDED)
        
        agents = len(self.c2_server._agents)
        jobs = self.c2_server.get_jobs()
        active = len([j for j in jobs if j['status'] == 'running'])
        
        return StatsBar(agents=agents, active_attacks=active, total_attacks=len(jobs)).build()
    
    def _build_agents(self) -> Panel:
        """Build agents table"""
        if not self.c2_server:
            return Panel("[dim]No C2 connection[/dim]", title="Agents", box=box.ROUNDED)
        
        agents = self.c2_server.get_agents()
        if not agents:
            return Panel("[dim]No agents connected[/dim]", title="Agents", box=box.ROUNDED)
        
        table = AgentTable(agents)
        return Panel(table.build(), title=f"Agents ({len(agents)})", box=box.ROUNDED)
    
    def _build_attacks(self) -> Panel:
        """Build attacks table"""
        if not self.c2_server:
            return Panel("[dim]No C2 connection[/dim]", title="Attacks", box=box.ROUNDED)
        
        jobs = self.c2_server.get_jobs()
        if not jobs:
            return Panel("[dim]No active attacks[/dim]", title="Attacks", box=box.ROUNDED)
        
        table = AttackTable(jobs)
        return Panel(table.build(), title=f"Attacks ({len(jobs)})", box=box.ROUNDED)
    
    def _build_logs(self) -> Panel:
        """Build log panel"""
        return Panel("[dim]Event log will appear here...[/dim]", title="Logs", box=box.ROUNDED)
    
    def _refresh(self) -> None:
        """Update all panels"""
        self.layout["header"].update(self._build_header())
        self.layout["footer"].update(self._build_footer())
        self.layout["stats"].update(self._build_stats())
        self.layout["agents"].update(self._build_agents())
        self.layout["attacks"].update(self._build_attacks())
    
    def run(self) -> None:
        """Start TUI"""
        if not HAS_RICH:
            return
        
        self.running = True
        self._refresh()
        
        try:
            with Live(self.layout, console=self.console, refresh_per_second=1, screen=True) as live:
                while self.running:
                    self._refresh()
                    time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            self.console.print("\n[dim]TUI closed[/dim]")
