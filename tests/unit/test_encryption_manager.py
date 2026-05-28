# Test: Encryption Manager
#
# Tests:
#   - Generate and rotate keys (masterKey, memoryKey, sessionKey)
#   - Encrypt/decrypt data (AES-256-GCM)
#   - Validate authentication tag (detect tampering)
#   - Scrypt password derivation
#   - TLS 1.3 enforcement for transport
#
# Fixtures: encryption_keys
