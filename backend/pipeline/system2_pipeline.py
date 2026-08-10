"""System 2 pipeline — full path for complex/emotional turns (<30s target).

Persona resolution + Agent 4a (Semantic Planner) + Agent 4b (Emotion Refiner). In production the
injected steps wrap the local Ollama "main" tier model (config/defaults.yaml `llm.system2`) for
both agents, and the empathy hypothesis from Layer 3 shapes the 4b refinement. Thin re-export of
the orchestrator's `run_system2`.
"""

from __future__ import annotations

from backend.pipeline.conversation_orchestrator import PipelineSteps, TurnContext, run_system2


def run(ctx: TurnContext, steps: PipelineSteps) -> TurnContext:
    """Run the System 2 generation path over the turn context (mutates and returns it)."""
    run_system2(ctx, steps)
    return ctx
