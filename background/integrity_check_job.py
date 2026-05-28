# Integrity Check Job
#
# Responsibility: Verify data integrity across all stores.
#
# Trigger: Daily (configurable time, typically 3 AM)
#
# Executes:
#   - layer12_privacy.integrity_verifier.verify_all_stores()
#   - Computes Merkle hashes
#   - Reports tampering detection
#   - Alerts user if corruption found
#
# Performance: Typically 30 sec - 2 min depending on data volume
