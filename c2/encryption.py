#!/usr/bin/env python3
"""
C2 Encryption
E2E encryption using AES-256-GCM + RSA for key exchange
"""

import os
import json
import hashlib
import hmac
import struct
import base64
from typing import Tuple, Optional
from dataclasses import dataclass

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


@dataclass
class EncryptedMessage:
    nonce: bytes
    ciphertext: bytes
    tag: bytes


class KeyPair:
    """RSA key pair for asymmetric encryption"""
    
    def __init__(self, key_size: int = 4096):
        if not HAS_CRYPTO:
            raise ImportError("cryptography library required")
        
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        self.key_size = key_size
    
    def get_public_pem(self) -> bytes:
        """Export public key as PEM"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def get_private_pem(self, password: bytes = None) -> bytes:
        """Export private key as PEM"""
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption()
        )
    
    @staticmethod
    def load_public_pem(pem_data: bytes) -> 'KeyPair':
        """Load public key from PEM"""
        kp = KeyPair.__new__(KeyPair)
        kp.public_key = serialization.load_pem_public_key(pem_data, backend=default_backend())
        kp.private_key = None
        kp.key_size = kp.public_key.key_size
        return kp
    
    @staticmethod
    def load_private_pem(pem_data: bytes, password: bytes = None) -> 'KeyPair':
        """Load private key from PEM"""
        kp = KeyPair.__new__(KeyPair)
        kp.private_key = serialization.load_pem_private_key(
            pem_data, password=password, backend=default_backend()
        )
        kp.public_key = kp.private_key.public_key()
        kp.key_size = kp.private_key.key_size
        return kp


class SymmetricCrypto:
    """AES-256-GCM symmetric encryption"""
    
    KEY_SIZE = 32  # 256 bits
    NONCE_SIZE = 12  # 96 bits for GCM
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate random 256-bit key"""
        return os.urandom(SymmetricCrypto.KEY_SIZE)
    
    @staticmethod
    def generate_nonce() -> bytes:
        """Generate random 96-bit nonce"""
        return os.urandom(SymmetricCrypto.NONCE_SIZE)
    
    @staticmethod
    def encrypt(plaintext: bytes, key: bytes, nonce: bytes = None, aad: bytes = None) -> EncryptedMessage:
        """Encrypt with AES-256-GCM"""
        if nonce is None:
            nonce = SymmetricCrypto.generate_nonce()
        
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, plaintext, aad)
        
        # GCM appends 16-byte tag to ciphertext
        ciphertext = ct[:-16]
        tag = ct[-16:]
        
        return EncryptedMessage(nonce=nonce, ciphertext=ciphertext, tag=tag)
    
    @staticmethod
    def decrypt(enc: EncryptedMessage, key: bytes, aad: bytes = None) -> bytes:
        """Decrypt AES-256-GCM"""
        aesgcm = AESGCM(key)
        ct_with_tag = enc.ciphertext + enc.tag
        return aesgcm.decrypt(enc.nonce, ct_with_tag, aad)
    
    @staticmethod
    def encrypt_raw(plaintext: bytes, key: bytes, nonce: bytes = None, aad: bytes = None) -> bytes:
        """Encrypt and return concatenated nonce + ciphertext + tag"""
        enc = SymmetricCrypto.encrypt(plaintext, key, nonce, aad)
        return enc.nonce + enc.ciphertext + enc.tag
    
    @staticmethod
    def decrypt_raw(data: bytes, key: bytes, aad: bytes = None) -> bytes:
        """Decrypt from concatenated format"""
        nonce = data[:SymmetricCrypto.NONCE_SIZE]
        tag = data[-16:]
        ciphertext = data[SymmetricCrypto.NONCE_SIZE:-16]
        enc = EncryptedMessage(nonce=nonce, ciphertext=ciphertext, tag=tag)
        return SymmetricCrypto.decrypt(enc, key, aad)


class AsymmetricCrypto:
    """RSA encryption/decryption and signing"""
    
    MAX_ENCRYPT_SIZE = 446  # For 4096-bit key with OAEP
    
    @staticmethod
    def encrypt(plaintext: bytes, public_key) -> bytes:
        """Encrypt with RSA-OAEP"""
        return public_key.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    @staticmethod
    def decrypt(ciphertext: bytes, private_key) -> bytes:
        """Decrypt RSA-OAEP"""
        return private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    @staticmethod
    def sign(data: bytes, private_key) -> bytes:
        """Sign data with RSA-PSS"""
        return private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    
    @staticmethod
    def verify(data: bytes, signature: bytes, public_key) -> bool:
        """Verify RSA-PSS signature"""
        try:
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False


class KeyExchange:
    """Key exchange protocol using RSA + HKDF"""
    
    @staticmethod
    def derive_session_key(pre_shared_secret: bytes, context: bytes = None) -> bytes:
        """Derive session key using HKDF-SHA256"""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=context or b'ironcarrier-c2-session',
            backend=default_backend()
        )
        return hkdf.derive(pre_shared_secret)
    
    @staticmethod
    def server_handshake(server_keypair: KeyPair, client_public_pem: bytes) -> Tuple[bytes, bytes]:
        """
        Server side of key exchange
        Returns (session_key, response_data)
        """
        client_public = KeyPair.load_public_pem(client_public_pem)
        
        # Generate session secret
        session_secret = os.urandom(64)
        
        # Encrypt session secret with client's public key
        encrypted_secret = AsymmetricCrypto.encrypt(session_secret, client_public.public_key)
        
        # Sign the encrypted secret
        signature = AsymmetricCrypto.sign(encrypted_secret, server_keypair.private_key)
        
        # Derive session key
        session_key = KeyExchange.derive_session_key(session_secret)
        
        # Build response: server_pubkey + encrypted_secret + signature
        response = (
            len(server_keypair.get_public_pem()).to_bytes(4, 'big') +
            server_keypair.get_public_pem() +
            len(encrypted_secret).to_bytes(4, 'big') +
            encrypted_secret +
            len(signature).to_bytes(4, 'big') +
            signature
        )
        
        return session_key, response
    
    @staticmethod
    def client_handshake(client_keypair: KeyPair, server_response: bytes) -> Tuple[bytes, 'KeyPair']:
        """
        Client side of key exchange
        Returns (session_key, server_public_key)
        """
        offset = 0
        
        # Parse server public key
        pubkey_len = int.from_bytes(server_response[offset:offset + 4], 'big')
        offset += 4
        server_pub_pem = server_response[offset:offset + pubkey_len]
        offset += pubkey_len
        server_public = KeyPair.load_public_pem(server_pub_pem)
        
        # Parse encrypted secret
        enc_len = int.from_bytes(server_response[offset:offset + 4], 'big')
        offset += 4
        encrypted_secret = server_response[offset:offset + enc_len]
        offset += enc_len
        
        # Parse signature
        sig_len = int.from_bytes(server_response[offset:offset + 4], 'big')
        offset += 4
        signature = server_response[offset:offset + sig_len]
        
        # Verify signature
        if not AsymmetricCrypto.verify(encrypted_secret, signature, server_public.public_key):
            raise ValueError("Server signature verification failed")
        
        # Decrypt session secret
        session_secret = AsymmetricCrypto.decrypt(encrypted_secret, client_keypair.private_key)
        
        # Derive session key
        session_key = KeyExchange.derive_session_key(session_secret)
        
        return session_key, server_public


class C2Encryption:
    """High-level C2 encryption manager"""
    
    def __init__(self, keypair: KeyPair = None):
        self.keypair = keypair or KeyPair()
        self.session_key: Optional[bytes] = None
        self.peer_public: Optional[KeyPair] = None
        self._symmetric = SymmetricCrypto()
        self._asymmetric = AsymmetricCrypto()
    
    def init_server(self) -> bytes:
        """Initialize server side, return public key PEM"""
        return self.keypair.get_public_pem()
    
    def server_handshake(self, client_public_pem: bytes) -> bytes:
        """Complete server handshake"""
        self.session_key, response = KeyExchange.server_handshake(self.keypair, client_public_pem)
        return response
    
    def client_handshake(self, server_public_pem: bytes, server_response: bytes) -> bytes:
        """Complete client handshake"""
        client_kp = KeyPair()
        self.session_key, self.peer_public = KeyExchange.client_handshake(client_kp, server_response)
        return client_kp.get_public_pem()
    
    def encrypt_message(self, plaintext: bytes) -> bytes:
        """Encrypt message with session key"""
        if not self.session_key:
            raise ValueError("No session key established")
        return SymmetricCrypto.encrypt_raw(plaintext, self.session_key)
    
    def decrypt_message(self, data: bytes) -> bytes:
        """Decrypt message with session key"""
        if not self.session_key:
            raise ValueError("No session key established")
        return SymmetricCrypto.decrypt_raw(data, self.session_key)
    
    def encrypt_json(self, obj: dict) -> bytes:
        """Encrypt JSON object"""
        return self.encrypt_message(json.dumps(obj).encode())
    
    def decrypt_json(self, data: bytes) -> dict:
        """Decrypt to JSON object"""
        return json.loads(self.decrypt_message(data).decode())
    
    @property
    def is_established(self) -> bool:
        return self.session_key is not None
