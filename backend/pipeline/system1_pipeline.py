"""System 1 pipeline — fast path for casual/simple turns (<2s target).

Persona resolution + Agent 4a (Semantic Planner) only; the Emotion Refiner (Agent 4b) is skipped.
In production the injected steps wrap Ollama + qwen2.5:7b. This module is a thin re-export of the
orchestrator's `run_system1` so the two generation paths live behind one import surface.
"""

from __future__ import annotations

from backend.pipeline.conversation_orchestrator import PipelineSteps, TurnContext, run_system1


def run(ctx: TurnContext, steps: PipelineSteps) -> TurnContext:
    """Run the System 1 generation path over the turn context (mutates and returns it)."""
    run_system1(ctx, steps)
    return ctx
