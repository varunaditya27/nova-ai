"""Pipeline — conversation wiring.

Pure orchestration: the pipeline contains zero business logic. It sequences the 13 layers and
threads data between them; every layer step is injected, so refactoring a layer never changes
pipeline code except the import. See `conversation_orchestrator.ConversationOrchestrator` for the
turn entry point and the enforced cross-layer invariants.
"""

from backend.pipeline.conversation_orchestrator import (
    ConversationOrchestrator,
    OrchestratedOutput,
    PipelineSteps,
    TurnContext,
    route_system,
    run_system1,
    run_system2,
)
from backend.pipeline.proactive_pipeline import run_proactive_check
from backend.pipeline.state_updater import run_state_update

__all__ = [
    "ConversationOrchestrator", "OrchestratedOutput", "PipelineSteps", "TurnContext",
    "route_system", "run_system1", "run_system2",
    "run_proactive_check", "run_state_update",
]
