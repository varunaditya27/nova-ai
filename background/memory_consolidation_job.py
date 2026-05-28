# Memory Consolidation Job
#
# Responsibility: Run forgetting engine post-session (decay sweep, clustering, compression).
#
# Trigger: After every Nth session (configurable, typically 5 sessions)
#
# Executes:
#   - layer2_memory.forgetting_engine.run_decay_sweep()
#   - All consolidation operations logged
#
# Performance: Typically 5-15 seconds for a user with weeks of history
