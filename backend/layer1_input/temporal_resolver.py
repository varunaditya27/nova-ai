"""Layer 1 · Sub-Component 1 — Temporal Resolver (architecture doc §3).

Answers: *when is this message, relative to everything we know about this user and this
conversation?* Maps the raw timestamp to circadian band, session-gap category, behavioral
anomaly flags, and a fuzzy-label utility that downstream layers reuse.

Zero-LLM, fully deterministic. Target execution time < 5 ms (§10).
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from .schemas import CircadianBand, GapCategory, UserTemporalProfile

# ── Constants (mirror config/layer1.yaml; code is the source of truth) ───────
# NOTE: config/layer1.yaml is loaded into the merged config dict (config/__init__.py) but no
# module in this package reads config['layer1'] — these values are still hardcoded, not
# config-driven. Re-tuning without a code change (the YAML's stated purpose) needs each
# function below to accept the relevant threshold as a parameter; documented as a follow-up.

# Population-level vulnerability priors per band (§3.2). Personalized per-user after
# 20+ sessions via UserTemporalProfile.per_band_circadian_prior (§3.4).
_CIRCADIAN_MOOD_PRIOR: dict[CircadianBand, float] = {
    CircadianBand.LATE_NIGHT: 0.75,
    CircadianBand.EARLY_MORNING: 0.80,
    CircadianBand.MORNING: 0.20,
    CircadianBand.AFTERNOON: 0.25,
    CircadianBand.EVENING: 0.40,
    CircadianBand.NIGHT: 0.55,
}

# Personalization activates only once the user has this many sessions of history (§3.4).
PERSONALIZED_PRIOR_MIN_SESSIONS = 20

# Anomaly detection is suppressed until the profile has this many sessions (§11).
ANOMALY_MIN_SESSIONS = 5

# Gap thresholds in ascending seconds: (upper_bound_exclusive, category). A gap is assigned
# to the first category whose upper bound it falls strictly below (§3.3).
_GAP_THRESHOLDS: list[tuple[int, GapCategory]] = [
    (30 * 60, GapCategory.SAME_SESSION),          # < 30 min
    (4 * 3600, GapCategory.SHORT_BREAK),          # < 4 hrs
    (24 * 3600, GapCategory.SAME_DAY),            # < 24 hrs
    (3 * 86400, GapCategory.FEW_DAYS),            # < 3 days
    (14 * 86400, GapCategory.WEEK_OR_TWO),        # < 14 days
    (90 * 86400, GapCategory.LONG_ABSENCE),       # < 90 days (~3 months)
]
# Anything >= the last threshold falls through to VERY_LONG_ABSENCE.

_GAP_LABELS: dict[GapCategory, str] = {
    GapCategory.SAME_SESSION: "just now",
    GapCategory.SHORT_BREAK: "a little while ago",
    GapCategory.SAME_DAY: "earlier today",
    GapCategory.FEW_DAYS: "a couple of days ago",
    GapCategory.WEEK_OR_TWO: "about a week ago",
    GapCategory.LONG_ABSENCE: "a while back",
    GapCategory.VERY_LONG_ABSENCE: "it's been a long time",
}

# A gap of 30+ minutes opens a new session (§3.3); same boundary as SAME_SESSION's upper edge.
NEW_SESSION_THRESHOLD_SECONDS = 30 * 60

# Atypical-band threshold: a band accounting for < 5% of history is anomalous (§3.4 cond. 1).
ATYPICAL_BAND_FREQUENCY = 0.05
# Long-gap multiplier: gap beyond avg_frequency × this is anomalous (§3.4 cond. 2).
LONG_GAP_MULTIPLIER = 2.5
# Rapid-return ratio: gap shorter than this × shortest recent gap is anomalous (§3.4 cond. 3).
RAPID_RETURN_RATIO = 0.10


# ── Circadian band ───────────────────────────────────────────────────────────
def map_circadian_band(local_hour: int) -> CircadianBand:
    """Map a local wall-clock hour (0–23) to one of six circadian bands (§3.2)."""
    h = local_hour % 24
    if h >= 23 or h < 3:
        return CircadianBand.LATE_NIGHT
    if h < 6:
        return CircadianBand.EARLY_MORNING
    if h < 12:
        return CircadianBand.MORNING
    if h < 17:
        return CircadianBand.AFTERNOON
    if h < 21:
        return CircadianBand.EVENING
    return CircadianBand.NIGHT


def circadian_mood_prior(
    band: CircadianBand, profile: Optional[UserTemporalProfile] = None
) -> float:
    """Estimated vulnerability prior in [0, 1] for the band (§3.2).

    Uses the user's personalized per-band prior once they have 20+ sessions of history;
    otherwise the population-level default.
    """
    if (
        profile is not None
        and profile.total_sessions >= PERSONALIZED_PRIOR_MIN_SESSIONS
        and band.value in profile.per_band_circadian_prior
    ):
        return profile.per_band_circadian_prior[band.value]
    return _CIRCADIAN_MOOD_PRIOR[band]


# ── Session gap ──────────────────────────────────────────────────────────────
def classify_session_gap(gap_seconds: float) -> GapCategory:
    """Classify the gap since the user's last message into one of seven buckets (§3.3)."""
    for upper_bound, category in _GAP_THRESHOLDS:
        if gap_seconds < upper_bound:
            return category
    return GapCategory.VERY_LONG_ABSENCE


def gap_label(category: GapCategory) -> str:
    """Human-readable, digit-free re-entry label for a gap category (§3.3)."""
    return _GAP_LABELS[category]


def is_new_session(gap_seconds: float) -> bool:
    """True when the gap opens a new session (30+ minutes of inactivity, §3.3)."""
    return gap_seconds >= NEW_SESSION_THRESHOLD_SECONDS


# ── Anomaly detection ────────────────────────────────────────────────────────
def detect_temporal_anomaly(
    band: CircadianBand,
    gap_seconds: float,
    profile: UserTemporalProfile,
    shortest_recent_gap_seconds: Optional[float] = None,
) -> tuple[bool, Optional[str]]:
    """Detect a behavioral timing anomaly and produce a plain-language context note (§3.4).

    Emits a *signal flag*, never a conclusion about emotional state. Suppressed for
    cold-start profiles (< 5 sessions, §11).
    """
    if profile.total_sessions < ANOMALY_MIN_SESSIONS:
        return False, None

    notes: list[str] = []

    # Condition 2 — gap far beyond the user's baseline cadence.
    if profile.average_session_frequency_days > 0:
        threshold_seconds = profile.average_session_frequency_days * 86400 * LONG_GAP_MULTIPLIER
        if gap_seconds > threshold_seconds:
            gap_days = round(gap_seconds / 86400, 1)
            baseline = round(profile.average_session_frequency_days, 1)
            notes.append(
                f"First contact in {gap_days} days — baseline is every {baseline} days"
            )

    # Condition 1 — message falls in an atypical band for this user.
    if profile.typical_bands.get(band.value, 0.0) < ATYPICAL_BAND_FREQUENCY:
        notes.append(f"Messaging during {band.value} — atypical for this user")

    # Condition 3 — unusually rapid return relative to recent cadence.
    if (
        shortest_recent_gap_seconds is not None
        and shortest_recent_gap_seconds > 0
        and gap_seconds < RAPID_RETURN_RATIO * shortest_recent_gap_seconds
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
def make_fuzzy_labeler(now: datetime) -> Callable[[datetime], str]:
    """Return a closure that converts absolute timestamps to fuzzy labels (§3.6).

    The LLM never sees raw timestamps — this utility is the only path by which temporal
    information enters the response pipeline. The closure captures ``now`` so a single
    reference instant is used for the whole turn.
    """

    def label(ts: datetime) -> str:
        delta = now - ts
        secs = delta.total_seconds()
        if secs < 1800:                      # future or < 30 min
            return "a moment ago"
        if secs < 4 * 3600:                  # < 4 hrs
            return "earlier today"
        if secs < 24 * 3600:                 # < 24 hrs — disambiguate by calendar date
            return "earlier today" if now.date() == ts.date() else "yesterday"
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
