"""SC-3 clustering + trend-statistics helpers (architecture doc §5.4).

Split out of ``pattern_recognizer.py``: pure math, distinct from the pattern-scope
detection logic that calls into it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from backend.layer5_relationship.schemas import SocialEvent

_CLUSTER_THRESHOLD = 0.72


def _tokens(text: str) -> set:
    return {t.strip(".,!?'\"").lower() for t in text.split() if t.strip(".,!?'\"")}


def _token_overlap(a: str, b: str) -> float:
    """Overlap coefficient |A∩B| / min(|A|,|B|) — lenient default for short topic phrases."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def cluster_by_semantic_similarity(
    summaries: list[str],
    threshold: float = _CLUSTER_THRESHOLD,
    similarity_fn: Optional[Callable[[str, str], float]] = None,
) -> list[list[int]]:
    """Greedy single-link clustering of summaries; returns clusters of indices (§5.4)."""
    sim = similarity_fn or _token_overlap
    clusters: list[list[int]] = []
    for i, summary in enumerate(summaries):
        placed = False
        for cluster in clusters:
            if any(sim(summary, summaries[j]) >= threshold for j in cluster):
                cluster.append(i)
                placed = True
                break
        if not placed:
            clusters.append([i])
    return clusters


def compute_mention_counts_by_window(
    events: list[SocialEvent], window_days: int = 30, now: Optional[datetime] = None
) -> list[int]:
    """Event counts per ``window_days`` bucket, oldest window first (architecture doc §5.4)."""
    now = now or datetime.utcnow()
    timed = [e for e in events if e.reported_timestamp is not None]
    if not timed:
        return []
    max_idx = max((now - e.reported_timestamp).days // window_days for e in timed)
    counts = [0] * (max_idx + 1)
    for e in timed:
        idx = (now - e.reported_timestamp).days // window_days
        counts[idx] += 1
    counts.reverse()   # oldest → most recent
    return counts


def _slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(values) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((xs[i] - mx) * (values[i] - my) for i in range(n)) / denom


def is_declining_trend(counts: list[int], min_windows: int = 3) -> bool:
    """True if there are enough windows and the chronological counts decline (§5.4)."""
    if len(counts) < min_windows:
        return False
    return _slope([float(c) for c in counts]) < 0 and counts[-1] < counts[0]


def span_days(events: list[SocialEvent]) -> int:
    if len(events) < 2:
        return 0
    return (events[-1].reported_timestamp - events[0].reported_timestamp).days
