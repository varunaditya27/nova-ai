# Integration Test: Multi-Device Sync
#
# Scenario: User on device A updates memory → Device B syncs → Both consistent
#
# Tests:
#   - Device A generates encrypted delta
#   - Server receives delta (can't read plaintext)
#   - Device B pulls delta
#   - Merge happens (no conflicts in this scenario)
#   - Both devices have same state
#   - Integrity checks pass
#   - No PII leaked to server
#
# Fixtures: db_session, encryption_keys, two_devices
