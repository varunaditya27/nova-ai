"""Goals routes — read + create over the persisted Layer-7 goal store (single-user)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import GoalCreate, GoalOut
from backend.layer7_goals.schemas import Goal, GoalStatus
from infra.db.goal_store import PostgresGoalStore

router = APIRouter(prefix="/goals", tags=["goals"])

_ACTIVE = [GoalStatus.TENTATIVE.value, GoalStatus.ACTIVE.value,
           GoalStatus.ON_TRACK.value, GoalStatus.AT_RISK.value]


def _store(state):
    return PostgresGoalStore(state.session_factory, state.default_user_id)


def _out(g) -> GoalOut:
    return GoalOut(goal_id=str(g.goal_id), title=g.title, status=g.status,
                   progress_score=getattr(g, "progress_score", 0.0),
                   description=getattr(g, "description", "") or "")


@router.get("", response_model=list[GoalOut])
def list_goals(status: str | None = None, state=Depends(get_state)):
    try:
        goals = _store(state).load_by_status([status] if status else _ACTIVE)
    except Exception:
        raise HTTPException(status_code=503, detail="goals temporarily unavailable")
    return [_out(g) for g in goals]


@router.get("/{goal_id}", response_model=GoalOut)
def get_goal(goal_id: str, state=Depends(get_state)):
    g = _store(state).get(goal_id)
    if g is None:
        raise HTTPException(status_code=404, detail="goal not found")
    return _out(g)


@router.post("", response_model=GoalOut, status_code=201)
def create_goal(body: GoalCreate, state=Depends(get_state)):
    if not body.title or not body.title.strip():
        raise HTTPException(status_code=422, detail="title must not be empty")
    goal = Goal(title=body.title.strip(), description=body.description, status=GoalStatus.ACTIVE.value)
    try:
        _store(state).add_goal(goal)
    except Exception:
        raise HTTPException(status_code=503, detail="goal create failed")
    return _out(goal)
