"""SC-5 · User World Model — real merge logic (architecture doc §7).

Turns one turn's extracted signals (profile facts, people mentioned, active life situations and
stressors, and — as of 2026-08-09 — psychological signals) into an updated ``UserWorldModel``,
creating the user's first row if none exists yet. Pure and LLM-free: a caller extracts signals
with an LLM elsewhere (e.g. ``api/state.py``) and passes the resulting dict here. Scoped to
profile + relationship_graph + life_context + psychological_model — communication_model remains
deliberately excluded: ``backend/layer4_persona/style_learning.py`` is the live, EMA-updated owner
of communication style, and duplicating it here would fork that logic (see docs/POLISH_BACKLOG.md
and CLAUDE.md's "three divergent reimplementation pairs" note). psychological_model is on-device
only like the rest of the UWM — ``backend/layer12_privacy/sync_coordinator.py`` has no knowledge
of this store at all, so it structurally cannot leave the device.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from .schemas import LifeSituation, PersonNode, Stressor, TriggerPattern, UserWorldModel

_PROFILE_FIELDS = (
    "preferred_name", "inferred_age_range", "pronouns", "location_context",
    "current_life_stage", "field_of_study_or_work", "institution_or_employer",
    "current_academic_year", "career_goals_summary", "likely_living_situation",
)


def _merge_profile(uwm: UserWorldModel, profile_delta: dict) -> None:
    for field in _PROFILE_FIELDS:
        value = profile_delta.get(field)
        if value:
            setattr(uwm.profile, field, value)
            uwm.confidence_by_field[f"profile.{field}"] = 0.6


def _merge_people(uwm: UserWorldModel, people_delta: list, now: datetime) -> None:
    by_name = {p.name.lower(): p for p in uwm.relationship_graph.people if p.name}
    for entry in people_delta:
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        existing = by_name.get(name.lower())
        if existing is not None:
            existing.mention_count += 1
            existing.last_mentioned_at = now
            for trait in entry.get("traits") or []:
                if trait not in existing.inferred_traits:
                    existing.inferred_traits.append(trait)
        else:
            node = PersonNode(
                name=name, relationship_tier=str(entry.get("relationship_tier") or "unclear"),
                first_mentioned_at=now, last_mentioned_at=now, mention_count=1,
                inferred_traits=list(entry.get("traits") or []))
            uwm.relationship_graph.people.append(node)
            by_name[name.lower()] = node
    uwm.relationship_graph.last_updated = now


def _merge_situations(uwm: UserWorldModel, situations_delta: list, now: datetime) -> None:
    existing = {s.description.lower() for s in uwm.life_context.active_situations}
    for entry in situations_delta:
        desc = str(entry.get("description", "")).strip()
        if not desc or desc.lower() in existing:
            continue
        uwm.life_context.active_situations.append(LifeSituation(
            description=desc, category=str(entry.get("category") or "other"),
            started_at=now, emotional_weight=float(entry.get("emotional_weight") or 0.0)))
        existing.add(desc.lower())


def _merge_stressors(uwm: UserWorldModel, stressors_delta: list) -> None:
    existing = {s.description.lower() for s in uwm.life_context.active_stressors}
    for entry in stressors_delta:
        desc = str(entry.get("description", "")).strip()
        if not desc or desc.lower() in existing:
            continue
        uwm.life_context.active_stressors.append(Stressor(
            description=desc, category=str(entry.get("category") or ""),
            intensity=float(entry.get("intensity") or 0.0)))
        existing.add(desc.lower())


def _merge_psychological(uwm: UserWorldModel, delta: dict, now: datetime) -> None:
    psych = uwm.psychological_model
    for field in ("attachment_signals", "self_efficacy_signals", "identity_conflict_signals"):
        for item in delta.get(field) or []:
            text = str(item).strip()
            if text and text not in getattr(psych, field):
                getattr(psych, field).append(text)

    style = delta.get("emotional_regulation_style")
    if style:
        psych.emotional_regulation_style = str(style).strip()
    support = delta.get("preferred_support_style")
    if support:
        psych.preferred_support_style = str(support).strip()

    existing = {t.description.lower() for t in psych.known_triggers}
    for entry in delta.get("triggers") or []:
        desc = str(entry.get("description", "")).strip()
        if not desc or desc.lower() in existing:
            continue
        psych.known_triggers.append(TriggerPattern(
            description=desc, response_type=str(entry.get("response_type") or ""),
            evidence_count=1, last_observed_at=now))
        existing.add(desc.lower())

    psych.derived_from_episode_count += 1
    psych.last_updated = now
    psych.model_confidence = min(1.0, psych.derived_from_episode_count / 10.0)


def merge_uwm_update(uwm: Optional[UserWorldModel], user_id: UUID, extracted: dict,
                     now: datetime) -> Optional[UserWorldModel]:
    """Fold one turn's extracted signals into the User World Model.

    Creates the first row for this user if none exists yet — closing the gap where nothing ever
    called ``UserWorldModel(...)`` for a real user. Returns ``None`` whenever there is nothing to
    persist — an empty ``extracted`` this turn, whether or not a UWM already exists — so silent
    turns neither create an empty row nor write a no-op version bump + audit entry on every
    single turn forever (state_updater's step 3 saves + audits whatever this returns).
    """
    if not extracted:
        return None
    if uwm is None:
        uwm = UserWorldModel(user_id=user_id, created_at=now)

    _merge_profile(uwm, extracted.get("profile") or {})
    _merge_people(uwm, extracted.get("people") or [], now)
    _merge_situations(uwm, extracted.get("situations") or [], now)
    _merge_stressors(uwm, extracted.get("stressors") or [])
    if extracted.get("psychological"):
        _merge_psychological(uwm, extracted["psychological"], now)

    uwm.update_version += 1
    uwm.last_updated_at = now
    if "api.uwm_updater" not in uwm.data_sources:
        uwm.data_sources.append("api.uwm_updater")
    return uwm
