"""Tools routes — Layer 8 confirmation flow + action history (single-user).

The ToolManager is a process singleton on AppState, so a confirmation the /chat pipeline issued in
one turn is confirmable here on a later request. Execution uses local/offline plugin backends; every
action is durably audited to `tool_action` via PostgresActionRecorder.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state, get_tool_manager
from api.schemas import ToolActionOut, ToolConfirmationOut, ToolResultOut

router = APIRouter(prefix="/tools", tags=["tools"])


def _action_out(r) -> ToolActionOut:
    return ToolActionOut(
        action_id=r.action_id, tool_name=r.tool_name, operation=r.operation,
        action_type=r.action_type, outcome=r.outcome,
        result_summary=getattr(r, "result_summary", "") or "",
        undone=getattr(r, "undone", False))


def _pending_views(tm):
    """ConfirmationRequest views rebuilt from the manager's bound pending tokens."""
    from backend.layer8_tools.schemas import ConfirmationRequest
    views = []
    for rid, p in getattr(tm, "_pending", {}).items():
        views.append(ConfirmationRequest(
            tool_name=p.tool_name, action_type=p.action_type,
            action_description=f"{p.tool_name}.{p.operation}",
            tier=getattr(p, "tier", "soft"), reversible=getattr(p, "reversible", True),
            parameters=dict(p.parameters or {}), request_id=rid))
    return views


@router.get("/pending", response_model=list[ToolConfirmationOut])
def pending_confirmations(tm=Depends(get_tool_manager)):
    if tm is None:
        return []
    return [ToolConfirmationOut(
        request_id=v.request_id, tool_name=v.tool_name, action_type=v.action_type,
        action_description=v.action_description, tier=v.tier,
        reversible=getattr(v, "reversible", True)) for v in _pending_views(tm)]


@router.post("/confirm/{request_id}", response_model=ToolResultOut)
def confirm_action(request_id: str, state=Depends(get_state), tm=Depends(get_tool_manager)):
    if tm is None:
        raise HTTPException(status_code=404, detail="no tool manager")
    out = tm.confirm_action(request_id, user_id=state.default_user_id)
    result = getattr(out, "result", None)
    if result is None:
        raise HTTPException(status_code=404, detail="no pending action for that id")
    from backend.layer8_tools.schemas import ToolOutcome
    return ToolResultOut(
        ok=result.outcome == ToolOutcome.SUCCESS.value, tool_name=result.tool_name,
        operation=result.operation, outcome=result.outcome,
        result_summary=getattr(result, "result_summary", "") or "",
        error_message=getattr(result, "error_message", None))


@router.post("/deny/{request_id}")
def deny_action(request_id: str, tm=Depends(get_tool_manager)):
    pending = getattr(tm, "_pending", {}) if tm is not None else {}
    if request_id not in pending:
        raise HTTPException(status_code=404, detail="no pending action for that id")
    del pending[request_id]
    return {"denied": request_id}


@router.post("/undo/{action_id}")
def undo_action(action_id: str, state=Depends(get_state), tm=Depends(get_tool_manager)):
    if tm is None:
        return {"undone": False}
    undone = tm.undo_action(action_id, user_id=state.default_user_id)
    return {"undone": undone}


@router.get("/history", response_model=list[ToolActionOut])
def action_history(state=Depends(get_state), tm=Depends(get_tool_manager)):
    if tm is None:
        return []
    return [_action_out(r) for r in tm.recorder.get_action_history(state.default_user_id)]
