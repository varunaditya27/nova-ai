# Calibrate Recall Weights
#
# Utility script: python -m scripts.calibrate_weights (interactive)
#
# Interactive tuning of recall scorer weights.
#
# Workflow:
#   1. Display current weights (α, β, γ, δ) and softmax temperature τ
#   2. Show example recalls with current weights
#   3. Ask user: "Are these recalls good?"
#   4. If yes, suggest slight adjustments in human-direction
#   5. Re-run eval_recall and show improvement
#   6. Repeat until satisfied
#   7. Write new weights to config/layer2.yaml
#
# Usage: python -m scripts.calibrate_weights
