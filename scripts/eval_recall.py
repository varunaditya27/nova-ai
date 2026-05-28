# Evaluate Recall Scorer
#
# Utility script: python -m scripts.eval_recall
#
# Tests recall_scorer against a labeled test set.
#
# Provides:
#   - Recall@k (did top-k results include the relevant memory?)
#   - MRR (mean reciprocal rank)
#   - NDCG (normalized discounted cumulative gain)
#   - Per-weight-set performance analysis
#
# Helps:
#   - Tune α β γ δ weights for better recall
#   - Validate that changes improve/don't regress performance
#   - Compare different softmax temperatures
#
# Usage: python -m scripts.eval_recall --test_set data/recall_test.json
