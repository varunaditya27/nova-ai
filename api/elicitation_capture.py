"""Layer-13 answer capture: learn what the user said to the onboarding question Nova just asked.

Active elicitation surfaces a question and never repeats it — but without this, the answer was
never read, so ``primary_reason`` (no passive extractor exists for it) stayed unknown forever and
graduation could only ever fire on the bare session-count fallback.
"""
from __future__ import annotations

import json
import logging
from typing import Callable

from backend.layer13_onboarding.active_elicitation_queue import INITIAL_ELICITATION_ITEMS
from infra.db.initial_state_store import PostgresInitialStateStore
from infra.db.onboarding_store import PostgresOnboardingStore
from infra.llm.json_extract import extract_json

logger = logging.getLogger("nova.api")

_QUESTIONS = {i.inference_target: i.question for i in INITIAL_ELICITATION_ITEMS if i.question}
_PROMPT = ('Nova, an AI companion, asked the user: "{question}"\nThe user then wrote: "{reply}"\n'
           'Did the user answer it? Return ONLY JSON: {{"answer": "<their answer in 2-6 words>"}} — '
           'or {{"answer": null}} if they did not answer or changed the subject.')


def _apply(state, target: str, answer: str) -> bool:
    if target == "primary_goal_area":
        state.primary_topic_areas = list({*state.primary_topic_areas, answer})
    elif target in ("user_handle", "life_phase", "primary_reason") and not getattr(state, target):
        setattr(state, target, answer)
    else:
        return False
    return True


def make_elicitation_answer_writer(session_factory, llm, graduation_sessions: int) -> Callable:
    def _write(ctx) -> None:
        try:
            message = getattr(ctx, "message", "") or ""
            onboarding = PostgresOnboardingStore(session_factory, ctx.user_id, graduation_sessions)
            target = onboarding.take_pending_answer(message)
            if target is None or target not in _QUESTIONS:
                return
            raw = json.loads(extract_json(llm.complete(
                _PROMPT.format(question=_QUESTIONS[target], reply=message[:1000]))))
            answer = str(raw.get("answer") or "").strip()[:80]
            if not answer:
                return
            store = PostgresInitialStateStore(session_factory, ctx.user_id)
            state = store.load()
            if _apply(state, target, answer):
                store.save(state)
        except Exception:
            logger.exception("elicitation answer capture failed; turn already delivered")
    return _write
