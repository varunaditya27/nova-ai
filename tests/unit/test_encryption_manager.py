"""Tests for SC-1 Encryption Manager — key hierarchy + authenticated encryption (doc §3.2)."""

import pytest

from backend.layer12_privacy import encryption_manager as em


def _mk(passphrase="correct horse", salt=b"s" * 16, iterations=2000):
    return em.derive_master_key(passphrase, salt, iterations=iterations)


# ── Key derivation (§3.2) ────────────────────────────────────────────────────
def test_master_key_is_deterministic():
    assert _mk() == _mk()
    assert len(_mk()) == 32


def test_master_key_changes_with_passphrase():
    assert _mk("a") != _mk("b")


def test_hkdf_separates_keys_by_info():
    master = _mk()
    mem = em.hkdf(master, salt=b"x" * 16, info=b"memory_enc")
    vec = em.hkdf(master, salt=b"x" * 16, info=b"vector_enc")
    assert mem != vec and len(mem) == 32


def test_session_key_differs_per_timestamp():
    master = _mk()
    assert em.derive_session_key(master, 1000.0) != em.derive_session_key(master, 2000.0)


# ── Authenticated encryption (§3.2) ──────────────────────────────────────────
def test_encrypt_decrypt_round_trip():
    key = _mk()
    token = em.encrypt("a secret memory", key)
    assert em.decrypt(token, key).decode() == "a secret memory"


def test_ciphertext_is_randomized_per_call():
    key = _mk()
    assert em.encrypt("same", key) != em.encrypt("same", key)   # random nonce
    # but both still decrypt
    assert em.decrypt(em.encrypt("same", key), key).decode() == "same"


def test_wrong_key_fails_authentication():
    token = em.encrypt("secret", _mk("right"))
    with pytest.raises(em.DecryptionError):
        em.decrypt(token, _mk("wrong"))


def test_tampered_ciphertext_fails_authentication():
    key = _mk()
    token = em.encrypt("secret", key)
    tampered = token[:-4] + ("AAAA" if token[-4:] != "AAAA" else "BBBB")
    with pytest.raises(em.DecryptionError):
        em.decrypt(tampered, key)


# ── Key rotation (§3.2) ──────────────────────────────────────────────────────
def test_reencrypt_moves_data_to_new_key():
    old, new = _mk("old"), _mk("new")
    token = em.encrypt("data", old)
    rotated = em.reencrypt(token, old, new)
    assert em.decrypt(rotated, new).decode() == "data"
    with pytest.raises(em.DecryptionError):
        em.decrypt(rotated, old)               # old key no longer works
