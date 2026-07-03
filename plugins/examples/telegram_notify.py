#!/usr/bin/env python3
"""
Telegram Notification Plugin
Sends attack and agent notifications to Telegram chat
"""

import json
import ssl
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from plugins.api import PluginInterface, PluginMetadata, PluginContext, PluginConfig


class TelegramNotify(PluginInterface):
    """Telegram notification plugin"""
    
    API_URL = 'https://api.telegram.org/bot{token}/sendMessage'
    
    def __init__(self):
        self.config = None
        self.context = None
        self._bot_token = ''
        self._chat_id = ''
        self._enabled = True
        self._notify_attacks = True
        self._notify_agents = True
        self._notify_errors = True
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name='telegram_notify',
            version='1.0.0',
            description='Send notifications to Telegram',
            author='IronCarrier',
            tags=['notifications', 'telegram', 'alerts'],
            priority=10,
        )
    
    def on_load(self, context: PluginContext) -> None:
        self.context = context
        self.config = PluginConfig('telegram_notify')
        self.config.set_default('bot_token', '')
        self.config.set_default('chat_id', '')
        self.config.set_default('enabled', True)
        self.config.set_default('notify_attacks', True)
        self.config.set_default('notify_agents', True)
        self.config.set_default('notify_errors', True)
        self.config.set_default('parse_mode', 'HTML')
        
        # Load from context config if available
        if context.config and 'telegram_notify' in context.config:
            self.config.load(context.config['telegram_notify'])
        
        self._bot_token = self.config.get('bot_token', '')
        self._chat_id = self.config.get('chat_id', '')
        self._enabled = self.config.get('enabled', True)
        self._notify_attacks = self.config.get('notify_attacks', True)
        self._notify_agents = self.config.get('notify_agents', True)
        self._notify_errors = self.config.get('notify_errors', True)
    
    def on_unload(self) -> None:
        pass
    
    def _send(self, text: str, disable_notification: bool = False) -> bool:
        """Send message to Telegram"""
        if not self._enabled or not self._bot_token or not self._chat_id:
            return False
        
        try:
            url = self.API_URL.format(token=self._bot_token)
            payload = {
                'chat_id': self._chat_id,
                'text': text,
                'parse_mode': self.config.get('parse_mode', 'HTML'),
                'disable_notification': disable_notification,
            }
            
            data = urllib.parse.urlencode(payload).encode()
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                result = json.loads(resp.read().decode())
                return result.get('ok', False)
        except Exception as e:
            if self.context:
                self.context.log('error', f"Telegram send failed: {e}")
            return False
    
    def _escape(self, text: str) -> str:
        """Escape HTML special chars"""
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    def on_attack_start(self, job: Any) -> None:
        if not self._notify_attacks:
            return
        
        target = getattr(job, 'target', job.get('target', 'N/A') if isinstance(job, dict) else 'N/A')
        vector = getattr(job, 'vector', job.get('vector', 'N/A') if isinstance(job, dict) else 'N/A')
        port = getattr(job, 'port', job.get('port', 'N/A') if isinstance(job, dict) else 'N/A')
        duration = getattr(job, 'duration', job.get('duration', 'N/A') if isinstance(job, dict) else 'N/A')
        
        msg = (
            f"⚡ <b>Attack Started</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 Vector: <code>{self._escape(str(vector))}</code>\n"
            f"🎯 Target: <code>{self._escape(str(target))}:{self._escape(str(port))}</code>\n"
            f"⏱ Duration: {duration}s\n"
        )
        
        self._send(msg)
    
    def on_attack_end(self, stats: Dict) -> None:
        if not self._notify_attacks:
            return
        
        packets = stats.get('total_packets', 0)
        mb = stats.get('total_megabytes', 0)
        peak_pps = stats.get('peak_pps', 0)
        peak_mbps = stats.get('peak_mbps', 0)
        errors = stats.get('total_errors', 0)
        
        msg = (
            f"✅ <b>Attack Completed</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📦 Packets: <code>{packets:,}</code>\n"
            f"📊 Data: <code>{mb:.2f} MB</code>\n"
            f"📈 Peak PPS: <code>{peak_pps:,.0f}</code>\n"
            f"📈 Peak BW: <code>{peak_mbps:.2f} Mbps</code>\n"
            f"❌ Errors: <code>{errors}</code>\n"
        )
        
        self._send(msg)
    
    def on_agent_connect(self, agent: Any) -> None:
        if not self._notify_agents:
            return
        
        agent_id = getattr(agent, 'agent_id', agent.get('agent_id', 'N/A') if isinstance(agent, dict) else 'N/A')
        hostname = getattr(agent, 'hostname', agent.get('hostname', 'N/A') if isinstance(agent, dict) else 'N/A')
        ip = getattr(agent, 'ip', agent.get('ip', 'N/A') if isinstance(agent, dict) else 'N/A')
        os_name = getattr(agent, 'os_name', agent.get('os', 'N/A') if isinstance(agent, dict) else 'N/A')
        user = getattr(agent, 'username', agent.get('user', 'N/A') if isinstance(agent, dict) else 'N/A')
        privs = getattr(agent, 'privileges', agent.get('privileges', 'N/A') if isinstance(agent, dict) else 'N/A')
        
        priv_icon = "👑" if privs == 'root' else "👤"
        
        msg = (
            f"{priv_icon} <b>Agent Connected</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: <code>{self._escape(str(agent_id))}</code>\n"
            f"🖥 Host: <code>{self._escape(str(hostname))}</code>\n"
            f"🌐 IP: <code>{self._escape(str(ip))}</code>\n"
            f"💻 OS: <code>{self._escape(str(os_name))}</code>\n"
            f"👤 User: <code>{self._escape(str(user))}</code>\n"
        )
        
        self._send(msg)
    
    def on_agent_disconnect(self, agent_id: str) -> None:
        if not self._notify_agents:
            return
        
        msg = f"❌ <b>Agent Disconnected</b>\n🆔 <code>{self._escape(str(agent_id))}</code>"
        self._send(msg, disable_notification=True)
    
    def on_error(self, error: Exception) -> None:
        if not self._notify_errors:
            return
        
        msg = f"⚠️ <b>Plugin Error</b>\n❗ <code>{self._escape(str(error))}</code>"
        self._send(msg)
    
    def get_config(self) -> Dict:
        return self.config.to_dict() if self.config else {}
    
    def set_config(self, config: Dict) -> None:
        if self.config:
            self.config.load(config)
            self._bot_token = self.config.get('bot_token', '')
            self._chat_id = self.config.get('chat_id', '')
            self._enabled = self.config.get('enabled', True)


# Export plugin instance
plugin = TelegramNotify()
