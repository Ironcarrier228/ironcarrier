#!/usr/bin/env python3
"""
Mini TCP Stack
Lightweight TCP state machine for SYN flood handling
"""

import socket
import struct
import time
import random
import threading
from typing import Dict, Optional, Tuple
from enum import IntEnum
from collections import OrderedDict


class TCPState(IntEnum):
    CLOSED = 0
    SYN_SENT = 1
    SYN_RECEIVED = 2
    ESTABLISHED = 3
    FIN_WAIT_1 = 4
    FIN_WAIT_2 = 5
    CLOSE_WAIT = 6
    CLOSING = 7
    LAST_ACK = 8
    TIME_WAIT = 9
    LISTEN = 10


class TCPConnection:
    """Single TCP connection state tracker"""
    
    def __init__(self, src_ip: str, src_port: int, dst_ip: str, dst_port: int):
        self.src_ip = src_ip
        self.src_port = src_port
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.state = TCPState.CLOSED
        self.local_seq = random.randint(100000, 999999)
        self.remote_seq = 0
        self.local_window = 65535
        self.remote_window = 0
        self.created_at = time.time()
        self.last_activity = time.time()
        self.packets_sent = 0
        self.packets_recv = 0
        self.bytes_sent = 0
        self.bytes_recv = 0
        self.retransmits = 0
    
    @property
    def key(self) -> Tuple[str, int, str, int]:
        return (self.src_ip, self.src_port, self.dst_ip, self.dst_port)
    
    @property
    def idle_time(self) -> float:
        return time.time() - self.last_activity
    
    @property
    def age(self) -> float:
        return time.time() - self.created_at
    
    def update_activity(self) -> None:
        self.last_activity = time.time()
    
    def transition(self, new_state: TCPState) -> None:
        self.state = new_state
        self.update_activity()
    
    def to_dict(self) -> Dict:
        return {
            'src': f"{self.src_ip}:{self.src_port}",
            'dst': f"{self.dst_ip}:{self.dst_port}",
            'state': self.state.name,
            'local_seq': self.local_seq,
            'remote_seq': self.remote_seq,
            'local_window': self.local_window,
            'remote_window': self.remote_window,
            'age': round(self.age, 2),
            'idle': round(self.idle_time, 2),
            'pkts_sent': self.packets_sent,
            'pkts_recv': self.packets_recv,
            'bytes_sent': self.bytes_sent,
            'bytes_recv': self.bytes_recv,
        }


class MiniTCPStack:
    """Minimal TCP protocol stack for raw socket operations"""
    
    # Valid state transitions per RFC 793
    TRANSITIONS = {
        TCPState.CLOSED: [TCPState.SYN_SENT, TCPState.LISTEN],
        TCPState.LISTEN: [TCPState.SYN_RECEIVED, TCPState.CLOSED],
        TCPState.SYN_SENT: [TCPState.ESTABLISHED, TCPState.SYN_RECEIVED, TCPState.CLOSED],
        TCPState.SYN_RECEIVED: [TCPState.ESTABLISHED, TCPState.FIN_WAIT_1, TCPState.CLOSED],
        TCPState.ESTABLISHED: [TCPState.FIN_WAIT_1, TCPState.CLOSE_WAIT, TCPState.CLOSED],
        TCPState.FIN_WAIT_1: [TCPState.FIN_WAIT_2, TCPState.CLOSING, TCPState.TIME_WAIT, TCPState.CLOSED],
        TCPState.FIN_WAIT_2: [TCPState.TIME_WAIT, TCPState.CLOSED],
        TCPState.CLOSE_WAIT: [TCPState.LAST_ACK, TCPState.CLOSED],
        TCPState.CLOSING: [TCPState.TIME_WAIT, TCPState.CLOSED],
        TCPState.LAST_ACK: [TCPState.CLOSED],
        TCPState.TIME_WAIT: [TCPState.CLOSED],
    }
    
    def __init__(self, max_connections: int = 100000, timeout: float = 300.0):
        self.max_connections = max_connections
        self.timeout = timeout
        self._connections: OrderedDict[Tuple, TCPConnection] = OrderedDict()
        self._lock = threading.Lock()
        self._stats = {
            'connections_opened': 0,
            'connections_closed': 0,
            'connections_timedout': 0,
            'invalid_transitions': 0,
            'packets_processed': 0,
        }
    
    def _can_transition(self, current: TCPState, new_state: TCPState) -> bool:
        """Check if state transition is valid"""
        return new_state in self.TRANSITIONS.get(current, [])
    
    def create_connection(self, src_ip: str, src_port: int,
                          dst_ip: str, dst_port: int,
                          initial_state: TCPState = TCPState.SYN_SENT) -> Optional[TCPConnection]:
        """Create and track a new TCP connection"""
        with self._lock:
            if len(self._connections) >= self.max_connections:
                self._evict_oldest()
            
            conn = TCPConnection(src_ip, src_port, dst_ip, dst_port)
            if self._can_transition(TCPState.CLOSED, initial_state):
                conn.transition(initial_state)
            else:
                self._stats['invalid_transitions'] += 1
                return None
            
            self._connections[conn.key] = conn
            self._stats['connections_opened'] += 1
            return conn
    
    def get_connection(self, src_ip: str, src_port: int,
                       dst_ip: str, dst_port: int) -> Optional[TCPConnection]:
        """Get existing connection"""
        key = (src_ip, src_port, dst_ip, dst_port)
        return self._connections.get(key)
    
    def update_state(self, conn: TCPConnection, new_state: TCPState) -> bool:
        """Update connection state"""
        with self._lock:
            if self._can_transition(conn.state, new_state):
                conn.transition(new_state)
                if new_state == TCPState.CLOSED:
                    self._remove_connection(conn)
                return True
            else:
                self._stats['invalid_transitions'] += 1
                return False
    
    def _remove_connection(self, conn: TCPConnection) -> None:
        """Remove connection from tracking"""
        key = conn.key
        if key in self._connections:
            del self._connections[key]
            self._stats['connections_closed'] += 1
    
    def _evict_oldest(self) -> None:
        """Remove oldest idle connection"""
        if self._connections:
            _, oldest = self._connections.popitem(last=False)
            self._stats['connections_timedout'] += 1
    
    def cleanup_timeout(self) -> int:
        """Remove timed out connections"""
        count = 0
        with self._lock:
            expired = [
                key for key, conn in self._connections.items()
                if conn.idle_time > self.timeout
            ]
            for key in expired:
                del self._connections[key]
                self._stats['connections_timedout'] += 1
                count += 1
        return count
    
    def get_connections_by_state(self, state: TCPState) -> list:
        """Get all connections in specific state"""
        with self._lock:
            return [conn for conn in self._connections.values() if conn.state == state]
    
    def get_stats(self) -> Dict:
        """Get stack statistics"""
        with self._lock:
            state_counts = {}
            for conn in self._connections.values():
                name = conn.state.name
                state_counts[name] = state_counts.get(name, 0) + 1
            
            return {
                'active_connections': len(self._connections),
                'max_connections': self.max_connections,
                'state_distribution': state_counts,
                **self._stats,
            }
    
    def build_syn(self, conn: TCPConnection, ttl: int = 64) -> bytes:
        """Build SYN packet for connection"""
        ip_header = struct.pack(
            '!BBHHHBBH4s4s',
            0x45, 0, 40,
            random.randint(0, 65535), 0x4000, ttl, 6, 0,
            socket.inet_aton(conn.src_ip),
            socket.inet_aton(conn.dst_ip)
        )
        
        tcp_header = struct.pack(
            '!HHIIBBHHH',
            conn.src_port, conn.dst_port,
            conn.local_seq, 0,
            (5 << 4), 0x02, conn.local_window, 0, 0
        )
        
        conn.packets_sent += 1
        conn.bytes_sent += 40
        return ip_header + tcp_header
    
    def build_syn_ack(self, conn: TCPConnection, ttl: int = 64) -> bytes:
        """Build SYN-ACK packet"""
        conn.local_seq += 1
        
        ip_header = struct.pack(
            '!BBHHHBBH4s4s',
            0x45, 0, 40,
            random.randint(0, 65535), 0x4000, ttl, 6, 0,
            socket.inet_aton(conn.src_ip),
            socket.inet_aton(conn.dst_ip)
        )
        
        tcp_header = struct.pack(
            '!HHIIBBHHH',
            conn.src_port, conn.dst_port,
            conn.local_seq, conn.remote_seq + 1,
            (5 << 4), 0x12, conn.local_window, 0, 0
        )
        
        conn.packets_sent += 1
        conn.bytes_sent += 40
        return ip_header + tcp_header
    
    def build_ack(self, conn: TCPConnection, ttl: int = 64) -> bytes:
        """Build ACK packet"""
        ip_header = struct.pack(
            '!BBHHHBBH4s4s',
            0x45, 0, 40,
            random.randint(0, 65535), 0x4000, ttl, 6, 0,
            socket.inet_aton(conn.src_ip),
            socket.inet_aton(conn.dst_ip)
        )
        
        tcp_header = struct.pack(
            '!HHIIBBHHH',
            conn.src_port, conn.dst_port,
            conn.local_seq, conn.remote_seq + 1,
            (5 << 4), 0x10, conn.local_window, 0, 0
        )
        
        conn.packets_sent += 1
        conn.bytes_sent += 40
        return ip_header + tcp_header
    
    def build_rst(self, conn: TCPConnection, ttl: int = 64) -> bytes:
        """Build RST packet"""
        ip_header = struct.pack(
            '!BBHHHBBH4s4s',
            0x45, 0, 40,
            random.randint(0, 65535), 0x4000, ttl, 6, 0,
            socket.inet_aton(conn.src_ip),
            socket.inet_aton(conn.dst_ip)
        )
        
        tcp_header = struct.pack(
            '!HHIIBBHHH',
            conn.src_port, conn.dst_port,
            conn.local_seq, 0,
            (5 << 4), 0x04, 0, 0, 0
        )
        
        conn.packets_sent += 1
        conn.bytes_sent += 40
        return ip_header + tcp_header
    
    def build_data(self, conn: TCPConnection, payload: bytes, ttl: int = 64) -> bytes:
        """Build TCP data packet with PSH+ACK"""
        tcp_header = struct.pack(
            '!HHIIBBHHH',
            conn.src_port, conn.dst_port,
            conn.local_seq, conn.remote_seq + 1,
            (5 << 4), 0x18, conn.local_window, 0, 0
        )
        
        ip_header = struct.pack(
            '!BBHHHBBH4s4s',
            0x45, 0, 20 + len(tcp_header) + len(payload),
            random.randint(0, 65535), 0x4000, ttl, 6, 0,
            socket.inet_aton(conn.src_ip),
            socket.inet_aton(conn.dst_ip)
        )
        
        conn.local_seq += len(payload)
        conn.packets_sent += 1
        conn.bytes_sent += len(ip_header) + len(tcp_header) + len(payload)
        return ip_header + tcp_header + payload
    
    def process_incoming(self, data: bytes) -> Optional[TCPConnection]:
        """Process incoming TCP packet and update state"""
        if len(data) < 40:
            return None
        
        ip_header = data[20:40]
        src_port = struct.unpack('!H', ip_header[0:2])[0]
        dst_port = struct.unpack('!H', ip_header[2:4])[0]
        seq = struct.unpack('!I', ip_header[4:8])[0]
        ack = struct.unpack('!I', ip_header[8:12])[0]
        offset_flags = struct.unpack('!H', ip_header[12:14])[0]
        flags = offset_flags & 0x3F
        window = struct.unpack('!H', ip_header[14:16])[0]
        
        # Try to find connection (reverse direction)
        conn = self.get_connection(
            src_ip='', src_port=dst_port,
            dst_ip='', dst_port=src_port
        )
        
        if conn:
            conn.remote_seq = seq
            conn.remote_window = window
            conn.packets_recv += 1
            conn.update_activity()
            self._stats['packets_processed'] += 1
            
            if flags & 0x02 and flags & 0x10:  # SYN-ACK
                self.update_state(conn, TCPState.ESTABLISHED)
            elif flags & 0x01 and flags & 0x10:  # FIN-ACK
                if conn.state == TCPState.ESTABLISHED:
                    self.update_state(conn, TCPState.CLOSE_WAIT)
            elif flags & 0x04:  # RST
                self.update_state(conn, TCPState.CLOSED)
            elif flags & 0x10:  # ACK
                if conn.state == TCPState.SYN_RECEIVED:
                    self.update_state(conn, TCPState.ESTABLISHED)
        
        return conn
