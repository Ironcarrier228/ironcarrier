#!/usr/bin/env python3
"""
SOCKS Client
SOCKS4/5 client implementation for proxying connections
"""

import socket
import struct
import threading
from typing import Optional, Tuple


class SOCKS4Error(Exception):
    pass


class SOCKS5Error(Exception):
    pass


class SOCKS4Client:
    """SOCKS4/4a proxy client"""
    
    def __init__(self, proxy_host: str, proxy_port: int, timeout: float = 30.0):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.timeout = timeout
    
    def connect(self, target_host: str, target_port: int, userid: str = '') -> socket.socket:
        """Connect through SOCKS4 proxy"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.proxy_host, self.proxy_port))
        
        # Build request
        ip_bytes = b'\x00\x00\x00\x01'  # Invalid IP = SOCKS4a (domain)
        port_bytes = struct.pack('!H', target_port)
        user_bytes = userid.encode() + b'\x00'
        domain_bytes = target_host.encode() + b'\x00'
        
        request = b'\x04\x01' + port_bytes + ip_bytes + user_bytes + domain_bytes
        sock.sendall(request)
        
        # Read response
        response = sock.recv(8)
        if len(response) < 8:
            sock.close()
            raise SOCKS4Error("Invalid response")
        
        code = response[1]
        if code != 90:
            sock.close()
            raise SOCKS4Error(f"SOCKS4 connect failed: code {code}")
        
        return sock


class SOCKS5Client:
    """SOCKS5 proxy client"""
    
    AUTH_NONE = 0x00
    AUTH_PASSWORD = 0x02
    AUTH_NO_ACCEPTABLE = 0xFF
    
    CMD_CONNECT = 0x01
    ATYP_IPV4 = 0x01
    ATYP_DOMAIN = 0x03
    
    REP_SUCCESS = 0x00
    
    def __init__(self, proxy_host: str, proxy_port: int,
                 username: str = '', password: str = '', timeout: float = 30.0):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.username = username
        self.password = password
        self.timeout = timeout
    
    def _auth_none(self, sock: socket.socket) -> bool:
        sock.sendall(struct.pack('!BB', 0x05, 0x01, 0x00))
        resp = sock.recv(2)
        return len(resp) == 2 and resp[1] == 0x00
    
    def _auth_password(self, sock: socket.socket) -> bool:
        uname = self.username.encode()
        passwd = self.password.encode()
        
        sock.sendall(struct.pack('!BB', 0x05, 0x02))
        resp = sock.recv(2)
        if len(resp) != 2 or resp[1] != 0x02:
            return False
        
        sock.sendall(struct.pack('!BB', 0x01, len(uname)) + uname + struct.pack('!B', len(passwd)) + passwd)
        resp = sock.recv(2)
        return len(resp) == 2 and resp[0] == 0x01 and resp[1] == 0x00
    
    def connect(self, target_host: str, target_port: int) -> socket.socket:
        """Connect through SOCKS5 proxy"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.proxy_host, self.proxy_port))
        
        # Auth negotiation
        if self.username:
            methods = [self.AUTH_PASSWORD, self.AUTH_NONE]
        else:
            methods = [self.AUTH_NONE]
        
        sock.sendall(struct.pack('!BBB', 0x05, len(methods), *methods))
        resp = sock.recv(2)
        
        if len(resp) != 2:
            sock.close()
            raise SOCKS5Error("Invalid auth response")
        
        chosen = resp[1]
        if chosen == self.AUTH_NO_ACCEPTABLE:
            sock.close()
            raise SOCKS5Error("No acceptable auth method")
        
        if chosen == self.AUTH_PASSWORD:
            if not self._auth_password(sock):
                sock.close()
                raise SOCKS5Error("Auth failed")
        elif chosen == self.AUTH_NONE:
            sock.sendall(struct.pack('!BB', 0x05, 0x00))
        
        # Connect request
        try:
            target_ip = socket.inet_aton(target_host)
            req = struct.pack('!BBBB', 0x05, self.CMD_CONNECT, 0x00, self.ATYP_IPV4) + target_ip + struct.pack('!H', target_port)
        except socket.gaierror:
            domain = target_host.encode()
            req = struct.pack('!BBBBB', 0x05, self.CMD_CONNECT, 0x00, self.ATYP_DOMAIN, len(domain)) + domain + struct.pack('!H', target_port)
        
        sock.sendall(req)
        
        # Read response
        resp = sock.recv(10)
        if len(resp) < 10 or resp[1] != self.REP_SUCCESS:
            sock.close()
            raise SOCKS5Error(f"Connect failed: {resp[1] if len(resp) > 1 else 'unknown'}")
        
        return sock


def socks_connect(proxy_host: str, proxy_port: int, target_host: str, target_port: int,
                   socks_version: int = 5, username: str = '', password: str = '',
                   timeout: float = 30.0) -> socket.socket:
    """Generic SOCKS connect"""
    if socks_version == 5:
        client = SOCKS5Client(proxy_host, proxy_port, username, password, timeout)
    else:
        client = SOCKS4Client(proxy_host, proxy_port, timeout)
    
    return client.connect(target_host, target_port)


def create_socks_socket(proxy_host: str, proxy_port: int, socks_version: int = 5,
                        username: str = '', password: str = '', timeout: float = 30.0) -> socket.socket:
    """Create pre-connected SOCKS socket"""
    target_info = socket.getaddrinfo(proxy_host, proxy_port)[0]
    return socks_connect(proxy_host, proxy_port, target_info[0], target_info[1], socks_version, username, password, timeout)
