"""api/routes/continuity.py::_greeting must use local time, not raw UTC.

A UTC-only greeting is wrong the moment a real (non-zero) timezone_offset_hours is configured
(docs/layer-1-architecture.md §17) -- e.g. 10:00 UTC is 15:30 IST, "Good morning" read as raw
UTC but "Good afternoon" is what's actually true where the user is.
"""
from datetime import datetime, timezone

from api.routes.continuity import _greeting


def test_greeting_uses_utc_when_no_offset_configured():
    now = datetime(2026, 1, 5, 20, 0, tzinfo=timezone.utc)   # 20:00 UTC
    assert _greeting(now) == "Good evening"


def test_greeting_applies_configured_timezone_offset():
    # 10:00 UTC == 15:30 IST -- "Good morning" read as raw UTC, "Good afternoon" local.
    now = datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc)
    assert _greeting(now) == "Good morning"
    assert _greeting(now, timezone_offset_hours=5.5) == "Good afternoon"
