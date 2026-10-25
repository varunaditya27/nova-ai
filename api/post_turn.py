"""Runs the post-turn writers off the response path.

The post-turn chain makes four to six extra LLM calls (summary, UWM, social, goals, identity,
threads) on a local model — seconds each. Running them before the HTTP response returns put all of
that on the user's critical path. Instead a single worker runs them in turn order, and the *next*
turn drains it right after the crisis scan (safety is never blocked) and before recall, so every
turn still reads the previous turn's writes. ``background=False`` runs inline (tests, scripts).
"""
from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable, Optional

logger = logging.getLogger("nova.api")


class PostTurnRunner:
    def __init__(self, writer: Callable, background: bool) -> None:
        self._writer = writer
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="post-turn") \
            if background else None
        self._pending: Optional[Future] = None

    def submit(self, ctx) -> None:
        if self._executor is None:
            self._writer(ctx)
        else:
            self._pending = self._executor.submit(self._writer, ctx)

    def drain(self) -> None:
        """Block until the previous turn's writes have landed."""
        pending, self._pending = self._pending, None
        if pending is not None:
            try:
                pending.result()
            except Exception:
                logger.exception("deferred post-turn writers failed")

    def shutdown(self) -> None:
        self.drain()
        if self._executor is not None:
            self._executor.shutdown(wait=True)
