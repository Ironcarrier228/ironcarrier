#!/usr/bin/env python3
"""
Payload Fragmentation
Split payloads for IDS/IPS evasion
"""

import random
import struct
from typing import List, Optional


class Fragmenter:
    """Payload fragmentation for evasion"""
    
    @staticmethod
    def random_size(payload: bytes, min_size: int = 8, max_size: int = 64) -> List[bytes]:
        """Fragment payload into random-sized chunks"""
        fragments = []
        offset = 0
        
        while offset < len(payload):
            size = random.randint(min_size, max_size)
            chunk = payload[offset:offset + size]
            fragments.append(chunk)
            offset += size
        
        return fragments
    
    @staticmethod
    def fixed_size(payload: bytes, size: int) -> List[bytes]:
        """Fragment payload into fixed-size chunks"""
        return [payload[i:i+size] for i in range(0, len(payload), size)]
    
    @staticmethod
    def overlap_fragments(payload: bytes, chunk_size: int = 64, overlap: int = 8) -> List[bytes]:
        """Create overlapping fragments for reassembly confusion"""
        fragments = []
        offset = 0
        
        while offset < len(payload):
            end = min(offset + chunk_size, len(payload))
            fragments.append(payload[offset:end])
            offset += chunk_size - overlap
        
        return fragments
    
    @staticmethod
    def scatter_order(fragments: List[bytes]) -> List[bytes]:
        """Randomize fragment order"""
        indices = list(range(len(fragments)))
        random.shuffle(indices)
        return [fragments[i] for i in indices]
    
    @staticmethod
    def add_padding(fragments: List[bytes], pad_size: int = 16, pad_byte: int = 0x00) -> List[bytes]:
        """Add padding to fragments"""
        padded = []
        for frag in fragments:
            pad_len = (pad_size - (len(frag) % pad_size)) % pad_size
            padded.append(frag + bytes([pad_byte] * pad_len))
        return padded
    
    @staticmethod
    def build_ip_fragments(payload: bytes, src_ip: str, dst_ip: str, dst_port: int,
                             protocol: int, frag_size: int = 8, offset: int = 0) -> List[bytes]:
        """Build IP fragments with headers"""
        import socket
        
        total_size = len(payload)
        mtu = 1500
        max_payload = mtu - 20  # IP header
        
        fragments = []
        current_offset = offset
        more_fragments = True
        
        while more_fragments:
            chunk_end = min(current_offset + frag_size, total_size)
            chunk = payload[current_offset:chunk_end]
            is_last = chunk_end >= total_size
            
            flags = 0x2000  # More Fragments
            if is_last:
                flags = 0x0000
            
            ip_header = struct.pack(
                '!BBHHHBBH4s4s',
                0x45, 0, 20 + len(chunk),
                random.randint(0, 65535), flags,
                64, protocol, 0,
                socket.inet_aton(src_ip),
                socket.inet_aton(dst_ip)
            )
            
            fragments.append(ip_header + chunk)
            current_offset = chunk_end
            
            if is_last:
                more_fragments = False
        
        return fragments
