"""FastAPI dependencies — resolve the booted AppState from the running app."""
from __future__ import annotations

from fastapi import Request

from api.state import AppState


def get_state(request: Request) -> AppState:
    return request.app.state.nova


def get_orchestrator(request: Request):
    return request.app.state.nova.orchestrator


def get_tool_manager(request: Request):
    return request.app.state.nova.tool_manager
