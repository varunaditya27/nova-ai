# Configuration Files
#
# All tunable parameters for Nova AI live here in YAML format.
# Configuration is environment-aware: production.yaml overrides defaults.yaml
#
# Files:
#   - defaults.yaml: Global fallback values (loaded first)
#   - layer1.yaml through layer13.yaml: Per-layer configuration
#   - production.yaml: Production overrides (if deployed)
#
# Philosophy:
#   - Zero secrets in config/ (use .env or environment variables for API keys)
#   - Every threshold, weight, rate, duration lives here
#   - Changing config never requires a code change
#   - Config is read at startup, cached in memory
