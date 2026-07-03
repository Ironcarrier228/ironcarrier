#!/usr/bin/env python3
"""
Raw Socket Handler
Low-level socket operations for packet crafting and injection
"""

import socket
import struct
import time
import threading
from typing import Optional, Tuple, Callable
from enum import IntEnum


class Protocol(IntEnum):
    ICMP = 1
    TCP = 6
    UDP = 17
    GRE = 47
    ESP = 50
    AH = 51
    SCTP = 132


class TCPFlags(IntEnum):
    FIN = 0x01
    SYN = 0x02
    RST = 0x04
    PSH = 0x08
    ACK = 0x10
    URG = 0x20
    ECE = 0x40
    CWR = 0x80


class ICMPType(IntEnum):
    ECHO_REPLY = 0
    DEST_UNREACHABLE = 3
    SOURCE_QUENCH = 4
    REDIRECT = 5
    ECHO_REQUEST = 8
    TIME_EXCEEDED = 11
    PARAMETER_PROBLEM = 12
    TIMESTAMP_REQUEST = 13
    TIMESTAMP_REPLY = 14


class RawSocket:
    """Raw socket wrapper for packet injection and capture"""
    
    def __init__(self, protocol: Protocol = Protocol.TCP):
        self.protocol = protocol
        self._socket: Optional[socket.socket] = None
        self._recv_socket: Optional[socket.socket] = None
        self._created = False
    
    def __enter__(self):
        self.create()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def create(self) -> 'RawSocket':
        """Create raw socket with IP_HDRINCL"""
        if self._created:
            return self
        
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, int(self.protocol))
        self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65535)
        
        try:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception:
            pass
        
        self._created = True
        return self
    
    def close(self) -> None:
        """Close socket"""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
        if self._recv_socket:
            try:
                self._recv_socket.close()
            except Exception:
                pass
        self._created = False
    
    def send(self, packet: bytes, target: Tuple[str, int]) -> int:
        """Send raw packet"""
        if not self._created:
            self.create()
        return self._socket.sendto(packet, target)
    
    def send_loop(self, packet_fn: Callable[[], bytes], target: Tuple[str, int],
                  duration: float, stop_event: Optional[threading.Event] = None) -> int:
        """Send packets in a loop using packet generator function"""
        if not self._created:
            self.create()
        
        count = 0
        end_time = time.time() + duration
        
        while time.time() < end_time:
            if stop_event and stop_event.is_set():
                break
            try:
                self._socket.sendto(packet_fn(), target)
                count += 1
            except Exception:
                break
        
        return count
    
    def recv(self, bufsize: int = 65535, timeout: float = 5.0) -> Optional[bytes]:
        """Receive raw packet"""
        if not self._created:
            self.create()
        
        self._socket.settimeout(timeout)
        try:
            data, _ = self._socket.recvfrom(bufsize)
            return data
        except socket.timeout:
            return None
        except Exception:
            return None
    
    def set_tos(self, tos: int) -> None:
        """Set Type of Service field"""
        if self._socket:
            self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, tos)
    
    def set_ttl(self, ttl: int) -> None:
        """Set default TTL (for packets built without custom TTL)"""
        if self._socket:
            self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
    
    def set_broadcast(self, enabled: bool = True) -> None:
        """Enable/disable broadcast"""
        if self._socket:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1 if enabled else 0)
    
    @staticmethod
    def build_ip_header(
        src_ip: str,
        dst_ip: str,
        protocol: int,
        payload_len: int,
        ttl: int = 64,
        tos: int = 0,
        identification: int = None,
        flags: int = 0x4000,
    ) -> bytes:
        """Build IPv4 header"""
        total_length = 20 + payload_len
        if identification is None:
            identification = random.randint(0, 65535)
        
        return struct.pack(
            '!BBHHHBBH4s4s',
            0x45,                   # Version (4) + IHL (5)
            tos,                    # Type of Service
            total_length,           # Total Length
            identification,         # Identification
            flags,                  # Flags + Fragment Offset
            ttl,                    # Time to Live
            protocol,               # Protocol
            0,                      # Header Checksum (0 = let kernel handle)
            socket.inet_aton(src_ip),
            socket.inet_aton(dst_ip)
        )
    
    @staticmethod
    def build_tcp_header(
        src_port: int,
        dst_port: int,
        seq: int,
        ack: int,
        flags: int,
        window: int = 65535,
        urgent: int = 0,
        data_offset: int = 5,
    ) -> bytes:
        """Build TCP header"""
        offset_flags = (data_offset << 12) | flags
        return struct.pack(
            '!HHIIBBHHH',
            src_port,
            dst_port,
            seq,
            ack,
            offset_flags,
            window,
            0,              # Checksum
            urgent
        )
    
    @staticmethod
    def build_udp_header(
        src_port: int,
        dst_port: int,
        payload_len: int,
    ) -> bytes:
        """Build UDP header"""
        length = 8 + payload_len
        return struct.pack('!HHHH', src_port, dst_port, length, 0)
    
    @staticmethod
    def build_icmp_header(
        icmp_type: int,
        icmp_code: int,
        payload: bytes = b'',
        checksum: int = 0,
    ) -> bytes:
        """Build ICMP header"""
        header = struct.pack('!BBH', icmp_type, icmp_code, checksum)
        packet = header + payload
        
        if checksum == 0:
            checksum = RawSocket.calculate_checksum(packet)
            header = struct.pack('!BBH', icmp_type, icmp_code, checksum)
            packet = header + payload
        
        return packet
    
    @staticmethod
    def calculate_checksum(data: bytes) -> int:
        """Calculate IP/TCP/UDP/ICMP checksum"""
        if len(data) % 2:
            data += b'\x00'
        
        s = 0
        for i in range(0, len(data), 2):
            word = (data[i] << 8) + data[i + 1]
            s += word
        
        while s >> 16:
            s = (s >> 16) + (s & 0xFFFF)
        
        return ~s & 0xFFFF
    
    @staticmethod
    def calculate_tcp_checksum(
        src_ip: str,
        dst_ip: str,
        tcp_header: bytes,
        payload: bytes = b'',
    ) -> int:
        """Calculate TCP checksum with pseudo-header"""
        src = socket.inet_aton(src_ip)
        dst = socket.inet_aton(dst_ip)
        tcp_len = len(tcp_header) + len(payload)
        
        pseudo_header = struct.pack('!4s4sBBH', src, dst, 0, 6, tcp_len)
        return RawSocket.calculate_checksum(pseudo_header + tcp_header + payload)
    
    @staticmethod
    def calculate_udp_checksum(
        src_ip: str,
        dst_ip: str,
        udp_header: bytes,
        payload: bytes = b'',
    ) -> int:
        """Calculate UDP checksum with pseudo-header"""
        src = socket.inet_aton(src_ip)
        dst = socket.inet_aton(dst_ip)
        udp_len = len(udp_header) + len(payload)
        
        pseudo_header = struct.pack('!4s4sBBH', src, dst, 0, 17, udp_len)
        return RawSocket.calculate_checksum(pseudo_header + udp_header + payload)
    
    @staticmethod
    def parse_ip_header(data: bytes) -> Dict:
        """Parse IP header from raw packet"""
        if len(data) < 20:
            return {}
        
        version_ihl = data[0]
        version = (version_ihl >> 4) & 0xF
        ihl = (version_ihl & 0xF) * 4
        
        return {
            'version': version,
            'ihl': ihl,
            'tos': data[1],
            'total_length': struct.unpack('!H', data[2:4])[0],
            'identification': struct.unpack('!H', data[4:6])[0],
            'flags': (data[6] >> 13) & 0x7,
            'fragment_offset': struct.unpack('!H', data[6:8])[0] & 0x1FFF,
            'ttl': data[8],
            'protocol': data[9],
            'checksum': struct.unpack('!H', data[10:12])[0],
            'src_ip': socket.inet_ntoa(data[12:16]),
            'dst_ip': socket.inet_ntoa(data[16:20]),
            'payload_offset': ihl,
        }
    
    @staticmethod
    def parse_tcp_header(data: bytes) -> Dict:
        """Parse TCP header"""
        if len(data) < 20:
            return {}
        
        offset_flags = struct.unpack('!H', data[12:14])[0]
        data_offset = ((offset_flags >> 12) & 0xF) * 4
        flags = offset_flags & 0x3F
        
        return {
            'src_port': struct.unpack('!H', data[0:2])[0],
            'dst_port': struct.unpack('!H', data[2:4])[0],
            'seq': struct.unpack('!I', data[4:8])[0],
            'ack': struct.unpack('!I', data[8:12])[0],
            'data_offset': data_offset,
            'flags': flags,
            'flag_names': [
                name for name, val in [
                    ('FIN', 0x01), ('SYN', 0x02), ('RST', 0x04),
                    ('PSH', 0x08), ('ACK', 0x10), ('URG', 0x20),
                    ('ECE', 0x40), ('CWR', 0x80)
                ] if flags & val
            ],
            'window': struct.unpack('!H', data[14:16])[0],
            'checksum': struct.unpack('!H', data[16:18])[0],
            'urgent': struct.unpack('!H', data[18:20])[0],
            'payload_offset': data_offset,
        }
    
    @staticmethod
    def parse_udp_header(data: bytes) -> Dict:
        """Parse UDP header"""
        if len(data) < 8:
            return {}
        
        return {
            'src_port': struct.unpack('!H', data[0:2])[0],
            'dst_port': struct.unpack('!H', data[2:4])[0],
            'length': struct.unpack('!H', data[4:6])[0],
            'checksum': struct.unpack('!H', data[6:8])[0],
            'payload_offset': 8,
        }


class PacketBuilder:
    """Fluent packet builder"""
    
    def __init__(self):
        self._src_ip = '0.0.0.0'
        self._dst_ip = '0.0.0.0'
        self._protocol = Protocol.TCP
        self._ttl = 64
        self._tos = 0
        self._src_port = 0
        self._dst_port = 0
        self._seq = 0
        self._ack = 0
        self._tcp_flags = 0
        self._window = 65535
        self._payload = b''
    
    def src_ip(self, ip: str) -> 'PacketBuilder':
        self._src_ip = ip
        return self
    
    def dst_ip(self, ip: str) -> 'PacketBuilder':
        self._dst_ip = ip
        return self
    
    def protocol(self, proto: Protocol) -> 'PacketBuilder':
        self._protocol = proto
        return self
    
    def ttl(self, ttl: int) -> 'PacketBuilder':
        self._ttl = ttl
        return self
    
    def tos(self, tos: int) -> 'PacketBuilder':
        self._tos = tos
        return self
    
    def src_port(self, port: int) -> 'PacketBuilder':
        self._src_port = port
        return self
    
    def dst_port(self, port: int) -> 'PacketBuilder':
        self._dst_port = port
        return self
    
    def seq(self, seq: int) -> 'PacketBuilder':
        self._seq = seq
        return self
    
    def ack(self, ack: int) -> 'PacketBuilder':
        self._ack = ack
        return self
    
    def flags(self, flags: int) -> 'PacketBuilder':
        self._tcp_flags = flags
        return self
    
    def window(self, window: int) -> 'PacketBuilder':
        self._window = window
        return self
    
    def payload(self, data: bytes) -> 'PacketBuilder':
        self._payload = data
        return self
    
    def build(self) -> bytes:
        """Build complete packet"""
        if self._protocol == Protocol.TCP:
            tcp_header = RawSocket.build_tcp_header(
                self._src_port, self._dst_port,
                self._seq, self._ack,
                self._tcp_flags, self._window
            )
            ip_header = RawSocket.build_ip_header(
                self._src_ip, self._dst_ip,
                Protocol.TCP, len(tcp_header) + len(self._payload),
                self._ttl, self._tos
            )
            return ip_header + tcp_header + self._payload
        
        elif self._protocol == Protocol.UDP:
            udp_header = RawSocket.build_udp_header(
                self._src_port, self._dst_port,
                len(self._payload)
            )
            ip_header = RawSocket.build_ip_header(
                self._src_ip, self._dst_ip,
                Protocol.UDP, len(udp_header) + len(self._payload),
                self._ttl, self._tos
            )
            return ip_header + udp_header + self._payload
        
        elif self._protocol == Protocol.ICMP:
            icmp_header = RawSocket.build_icmp_header(
                self._seq, self._ack, self._payload
            )
            ip_header = RawSocket.build_ip_header(
                self._src_ip, self._dst_ip,
                Protocol.ICMP, len(icmp_header),
                self._ttl, self._tos
            )
            return ip_header + icmp_header
        
        return b''
