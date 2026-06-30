"""SC-1 — Encryption Manager: key hierarchy + authenticated encryption (architecture doc §3.2).

The production spec uses AES-256-GCM via SQLCipher with keys in the Secure Enclave and Argon2id
for the sync key. The test runtime is stdlib-only, so this module implements a *real* authenticated
encryption construction from stdlib primitives — PBKDF2-HMAC-SHA256 key derivation, RFC-5869 HKDF
for the derived key hierarchy, a SHA-256 counter-mode keystream, and HMAC-SHA256 encrypt-then-MAC
with constant-time verification. It genuinely round-trips, detects tampering, and rejects wrong
keys. **In production the cipher is swapped for AES-256-GCM** (the key derivation + hierarchy carry
over unchanged); see the as-built note in the architecture doc.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct

_KEY_LEN = 32
_NONCE_LEN = 16
_TAG_LEN = 32
# Production: PBKDF2 iterations = 600_000 (architecture doc §3.2). Callers may lower for tests.
DEFAULT_PBKDF2_ITERATIONS = 600_000


class DecryptionError(Exception):
    """Raised when authentication fails (wrong key or tampered ciphertext)."""


# ── Key derivation (§3.2) ────────────────────────────────────────────────────
def derive_master_key(passphrase: str, salt: bytes, iterations: int = DEFAULT_PBKDF2_ITERATIONS) -> bytes:
    """Derive the master key from passphrase + device salt (PBKDF2-HMAC-SHA256)."""
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, iterations, _KEY_LEN)


def hkdf(key: bytes, salt: bytes, info: bytes, length: int = _KEY_LEN) -> bytes:
    """RFC-5869 HKDF (extract + expand) over HMAC-SHA256."""
    prk = hmac.new(salt, key, hashlib.sha256).digest()           # extract
    okm, block, counter = b"", b"", 1                            # expand
    while len(okm) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        okm += block
        counter += 1
    return okm[:length]


def derive_session_key(master_key: bytes, session_start_timestamp: float) -> bytes:
    """Ephemeral per-session key; derived fresh from the session start time."""
    return hkdf(master_key, salt=struct.pack(">d", session_start_timestamp), info=b"session_enc")


# ── Authenticated encryption (stdlib stand-in for AES-256-GCM) ───────────────
def _subkeys(key: bytes, nonce: bytes) -> tuple[bytes, bytes]:
    enc = hkdf(key, salt=nonce, info=b"enc")
    mac = hkdf(key, salt=nonce, info=b"mac")
    return enc, mac


def _keystream(enc_key: bytes, nonce: bytes, n: int) -> bytes:
    out, counter = b"", 0
    while len(out) < n:
        out += hashlib.sha256(enc_key + nonce + struct.pack(">Q", counter)).digest()
        counter += 1
    return out[:n]


def _xor(data: bytes, stream: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(data, stream))


def encrypt(plaintext, key: bytes) -> str:
    """Encrypt-then-MAC; returns a base64 token (nonce || ciphertext || tag)."""
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    nonce = os.urandom(_NONCE_LEN)
    enc_key, mac_key = _subkeys(key, nonce)
    ciphertext = _xor(plaintext, _keystream(enc_key, nonce, len(plaintext)))
    tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    return base64.b64encode(nonce + ciphertext + tag).decode("ascii")


def decrypt(token: str, key: bytes) -> bytes:
    """Verify the tag (constant-time) and decrypt; raise DecryptionError on any failure."""
    try:
        raw = base64.b64decode(token.encode("ascii"))
    except Exception as exc:
        raise DecryptionError("malformed token") from exc
    if len(raw) < _NONCE_LEN + _TAG_LEN:
        raise DecryptionError("token too short")
    nonce, ciphertext, tag = raw[:_NONCE_LEN], raw[_NONCE_LEN:-_TAG_LEN], raw[-_TAG_LEN:]
    enc_key, mac_key = _subkeys(key, nonce)
    expected = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, tag):
        raise DecryptionError("authentication failed")
    return _xor(ciphertext, _keystream(enc_key, nonce, len(ciphertext)))


def reencrypt(token: str, old_key: bytes, new_key: bytes) -> str:
    """Re-encrypt a token under a new key (used by key rotation, §3.2)."""
    return encrypt(decrypt(token, old_key), new_key)
