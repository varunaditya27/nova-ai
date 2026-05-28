# Sync Routes
#
# Responsibility: Cross-device encrypted data synchronization.
#
# Endpoints:
#   - POST /sync/push: Upload encrypted deltas from this device
#   - GET /sync/pull: Download encrypted deltas for this device
#   - GET /sync/status: Current sync status
#
# All data is encrypted end-to-end (user controls the key).
# Server never sees plaintext.
#
# Driven by Layer 12 sync_coordinator.
