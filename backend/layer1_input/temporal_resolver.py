"""Layer 1 · Sub-Component 1 — Temporal Resolver (architecture doc §3).

Answers: *when is this message, relative to everything we know about this user and this
conversation?* Maps the raw timestamp to circadian band, session-gap category, behavioral
anomaly flags, and a fuzzy-label utility that downstream layers reuse.

Zero-LLM, fully deterministic. Target execution time < 5 ms (§10).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

from .config import Layer1Config
from .schemas import CircadianBand, GapCategory, UserTemporalProfile

# Every function below accepts an optional ``cfg: Layer1Config`` so production can re-tune these
# without a code change (config/layer1.yaml → Layer1Config.from_dict, wired in api/state.py).
# ``_DEFAULT`` is what each function falls back to when no ``cfg`` is supplied (every existing
# unit test) — this reproduces the values that used to be hardcoded module constants here.
_DEFAULT = Layer1Config()

_GAP_LABELS: dict[GapCategory, str] = {
    GapCategory.SAME_SESSION: "just now",
    GapCategory.SHORT_BREAK: "a little while ago",
    GapCategory.SAME_DAY: "earlier today",
    GapCategory.FEW_DAYS: "a couple of days ago",
    GapCategory.WEEK_OR_TWO: "about a week ago",
    GapCategory.LONG_ABSENCE: "a while back",
    GapCategory.VERY_LONG_ABSENCE: "it's been a long time",
}


# ── Circadian band ───────────────────────────────────────────────────────────
def map_circadian_band(local_hour: int, cfg: Optional[Layer1Config] = None) -> CircadianBand:
    """Map a local wall-clock hour (0–23) to one of six circadian bands (§3.2)."""
    h = local_hour % 24
    for name, (start, end) in (cfg or _DEFAULT).circadian_bands.items():
        if start <= end:
            if start <= h < end:
                return CircadianBand(name)
        elif h >= start or h < end:            # band wraps midnight (e.g. late_night)
            return CircadianBand(name)
    return CircadianBand.MORNING                # unreachable if bands fully partition 24h


def circadian_mood_prior(
    band: CircadianBand, profile: Optional[UserTemporalProfile] = None,
    cfg: Optional[Layer1Config] = None,
) -> float:
    """Estimated vulnerability prior in [0, 1] for the band (§3.2).

    Uses the user's personalized per-band prior once they have 20+ sessions of history;
    otherwise the population-level default.
    """
    c = cfg or _DEFAULT
    if (
        profile is not None
        and profile.total_sessions >= c.personalized_prior_min_sessions
        and band.value in profile.per_band_circadian_prior
    ):
        return profile.per_band_circadian_prior[band.value]
    return c.circadian_mood_prior[band.value]


# ── Session gap ──────────────────────────────────────────────────────────────
def classify_session_gap(gap_seconds: float, cfg: Optional[Layer1Config] = None) -> GapCategory:
    """Classify the gap since the user's last message into one of seven buckets (§3.3)."""
    c = cfg or _DEFAULT
    for name, upper_bound in sorted(c.session_gap_categories.items(), key=lambda kv: kv[1]):
        if gap_seconds < upper_bound:
            return GapCategory(name)
    return GapCategory.VERY_LONG_ABSENCE


def gap_label(category: GapCategory) -> str:
    """Human-readable, digit-free re-entry label for a gap category (§3.3)."""
    return _GAP_LABELS[category]


def is_new_session(gap_seconds: float, cfg: Optional[Layer1Config] = None) -> bool:
    """True when the gap opens a new session (30+ minutes of inactivity, §3.3)."""
    return gap_seconds >= (cfg or _DEFAULT).new_session_threshold_seconds


# ── Anomaly detection ────────────────────────────────────────────────────────
def detect_temporal_anomaly(
    band: CircadianBand,
    gap_seconds: float,
    profile: UserTemporalProfile,
    shortest_recent_gap_seconds: Optional[float] = None,
    cfg: Optional[Layer1Config] = None,
) -> tuple[bool, Optional[str]]:
    """Detect a behavioral timing anomaly and produce a plain-language context note (§3.4).

    Emits a *signal flag*, never a conclusion about emotional state. Suppressed for
    cold-start profiles (< 5 sessions, §11).
    """
    c = cfg or _DEFAULT
    if profile.total_sessions < c.anomaly_min_sessions:
        return False, None

    notes: list[str] = []

    # Condition 2 — gap far beyond the user's baseline cadence. Suppressed when the gap still
    # falls within this user's own historical range (§3.4) — a long-but-seen-before gap isn't
    # a real anomaly for a user with naturally bursty engagement.
    if profile.average_session_frequency_days > 0:
        threshold_seconds = profile.average_session_frequency_days * 86400 * c.long_gap_multiplier
        within_own_history = (
            profile.longest_historical_gap_days > 0
            and gap_seconds <= profile.longest_historical_gap_days * 86400
        )
        if gap_seconds > threshold_seconds and not within_own_history:
            gap_days = round(gap_seconds / 86400, 1)
            baseline = round(profile.average_session_frequency_days, 1)
            notes.append(
                f"First contact in {gap_days} days — baseline is every {baseline} days"
            )

    # Condition 1 — message falls in an atypical band for this user.
    if profile.typical_bands.get(band.value, 0.0) < c.atypical_band_frequency:
        notes.append(f"Messaging during {band.value} — atypical for this user")

    # Condition 3 — unusually rapid return relative to recent cadence.
    if (
        shortest_recent_gap_seconds is not None
        and shortest_recent_gap_seconds > 0
        and gap_seconds < c.rapid_return_ratio * shortest_recent_gap_seconds
    ):
        notes.append("Unusually rapid return — much sooner than usual")

    if not notes:
        return False, None
    return True, "; ".join(notes)


def gap_vs_baseline_ratio(gap_seconds: float, profile: UserTemporalProfile) -> float:
    """Current gap as a multiple of the user's average cadence (§7.3). 1.0 if no baseline."""
    if profile.average_session_frequency_days <= 0:
        return 1.0
    return (gap_seconds / 86400) / profile.average_session_frequency_days


# ── Fuzzy temporal labeling ──────────────────────────────────────────────────
def make_fuzzy_labeler(
    now: datetime, timezone_offset_hours: float = 0.0
) -> Callable[[datetime], str]:
    """Return a closure that converts absolute timestamps to fuzzy labels (§3.6).

    The LLM never sees raw timestamps — this utility is the only path by which temporal
    information enters the response pipeline. The closure captures ``now`` so a single
    reference instant is used for the whole turn. The same-day/yesterday distinction is a *local*
    calendar-date question, so it applies ``timezone_offset_hours`` (see §17 in
    docs/layer-1-architecture.md — both ``now`` and ``ts`` are stored/passed as UTC).
    """
    offset = timedelta(hours=timezone_offset_hours)

    def label(ts: datetime) -> str:
        delta = now - ts
        secs = delta.total_seconds()
        if secs < 1800:                      # future or < 30 min
            return "a moment ago"
        if secs < 4 * 3600:                  # < 4 hrs
            return "earlier today"
        if secs < 24 * 3600:                 # < 24 hrs — disambiguate by local calendar date
            same_day = (now + offset).date() == (ts + offset).date()
            return "earlier today" if same_day else "yesterday"
        days = secs / 86400
        if days < 3:
            return "a couple of days ago"
        if days < 7:
            return "earlier this week"
        if days < 14:
            return "about a week ago"
        if days < 30:
            return "a few weeks ago"
        if days < 60:
            return "last month"
        if days < 120:
            return "a couple of months ago"
        if days < 240:
            return "a while back"
        if days < 420:
            return f"back in {ts.strftime('%B')}"
        if days < 730:
            return "about a year ago"
        return f"back in {ts.year}"

    return label
