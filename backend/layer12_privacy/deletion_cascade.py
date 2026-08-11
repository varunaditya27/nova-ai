"""SC-2 cascade dry-run computation + redaction (architecture doc §4.4).

Split out of ``selective_deletion.py``.
"""

from __future__ import annotations

from backend.layer12_privacy.deletion_scope import resolve_scope
from backend.layer12_privacy.schemas import CascadeImpactReport, DeletionRequest


def dry_run_deletion(
    request: DeletionRequest,
    memory_store,
    semantic_store=None,
    personality_store=None,
    longitudinal_store=None,
) -> CascadeImpactReport:
    """Compute the full cascade WITHOUT executing anything (architecture doc §4.4)."""
    target = set(resolve_scope(request.scope, request.deletion_type, memory_store))

    # target holds whatever resolve_scope returned for this deletion type -- a mix of plain
    # strings (the live SINGLE_MEMORY route path, "str(memory_id)") and UUID objects (e.g.
    # FULL_WIPE's memory_store.all()). Compare on string form so both agree with a real
    # SemanticMemory's supporting_episode_ids (a list[UUID] after deserialization).
    target_str = {str(t) for t in target}

    affected_facts = []
    if semantic_store is not None:
        for fact in semantic_store.all():
            # Layer 2's real SemanticMemory field is supporting_episode_ids/memory_id/statement --
            # this previously read derived_from_episodes/fact_id/fact_text, none of which exist on
            # the real schema (would have raised AttributeError the first time a real
            # semantic_store was ever passed in; see docs/POLISH_BACKLOG.md).
            supporting = list(getattr(fact, "supporting_episode_ids", []) or [])
            cited = [e for e in supporting if str(e) in target_str]
            if not cited:
                continue
            remaining = [e for e in supporting if str(e) not in target_str]
            if len(remaining) == 0:
                impact = "will_be_deleted"
            elif len(remaining) < 2:
                impact = "will_be_updated"
            else:
                impact = "will_be_flagged_for_review"
            affected_facts.append((fact.memory_id, fact.statement, impact))

    pv_will_change, pv_params = False, []
    if personality_store is not None:
        impact = personality_store.simulate_removal_impact(list(target))
        pv_will_change = getattr(impact, "max_delta", 0.0) > 0.05
        pv_params = getattr(impact, "affected_params", [])

    longitudinal_refs = []
    if longitudinal_store is not None:
        for s in longitudinal_store.all_weekly_summaries():
            # Layer 10's real WeeklySummary has no backing_episode_ids field at all (that field
            # only exists on RetrospectivePacket) -- this would have raised AttributeError the
            # first time a real longitudinal_store was passed in. The real per-summary episode
            # anchor is its significant moment's episode_ids.
            moment = getattr(s, "most_emotionally_significant_moment", None)
            episode_ids = list(getattr(moment, "episode_ids", []) or []) if moment else []
            refs = [e for e in episode_ids if str(e) in target_str]
            if refs:
                longitudinal_refs.append((s.summary_id, f"{len(refs)} reference(s) would be removed"))

    del_count = sum(1 for _, _, t in affected_facts if t == "will_be_deleted")
    no_stores_checked = semantic_store is None and personality_store is None and longitudinal_store is None
    if no_stores_checked:
        # Don't claim a cascade was computed when every cascade store was left unwired — an
        # unqualified "will also:" header with zero bullets reads as "nothing else affected"
        # when the truth is "nothing else was checked".
        summary = [f"Deleting {len(target)} memory/memories. (Cascade impact on facts, "
                   f"personality, and weekly summaries was not computed — no linked stores "
                   f"were provided for this check.)"]
    else:
        summary = [f"Deleting {len(target)} memory/memories will also:"]
        if del_count:
            summary.append(f"  • Remove {del_count} inferred fact(s) derived exclusively from these")
        if pv_will_change:
            summary.append("  • Recalculate your personality profile")
        if longitudinal_refs:
            summary.append(f"  • Update {len(longitudinal_refs)} weekly summary/summaries")
        if not (del_count or pv_will_change or longitudinal_refs):
            summary.append("  • Nothing else — no other data references these memories")

    request.affected_memory_ids = sorted(target)
    request.cascade_impacts = CascadeImpactReport(
        memories_deleted=len(target), semantic_facts_affected=affected_facts,
        personality_vector_will_change=pv_will_change, personality_params_affected=pv_params,
        longitudinal_references_to_update=longitudinal_refs,
        summary_human_readable="\n".join(summary))
    request.dry_run_completed = True
    return request.cascade_impacts


def redact_cascade(
    report: CascadeImpactReport,
    deleted_ids: list,
    semantic_store=None,
    longitudinal_store=None,
) -> dict:
    """Mutate the referencing artifacts a dry run reported, instead of only reporting them
    (architecture doc §4.4). References to the deleted memories are stripped from each affected
    semantic fact's ``supporting_episode_ids``; a fact left with none is deprecated and its
    statement cleared (derived exclusively from what's now gone). Weekly summaries whose
    significant-moment episodes were all deleted have that moment cleared. Rows are kept, redacted
    in place — the same "logical deletion, row retained for proof" invariant Layer-12 already uses
    for the memories themselves, not a hard delete."""
    target_str = {str(t) for t in deleted_ids}
    redacted_facts = redacted_summaries = 0

    if semantic_store is not None:
        for fact_id, _statement, _impact in report.semantic_facts_affected:
            fact = semantic_store.get(fact_id)
            if fact is None:
                continue
            remaining = [e for e in getattr(fact, "supporting_episode_ids", [])
                        if str(e) not in target_str]
            fields = {"supporting_episode_ids": remaining}
            if not remaining:
                fields["is_deprecated"] = True
                fields["statement"] = ""
            semantic_store.update(fact_id, fields)
            redacted_facts += 1

    if longitudinal_store is not None:
        for summary_id, _desc in report.longitudinal_references_to_update:
            summary = longitudinal_store.get(summary_id)
            moment = getattr(summary, "most_emotionally_significant_moment", None) if summary else None
            if summary is None or moment is None:
                continue
            remaining = [e for e in getattr(moment, "episode_ids", []) if str(e) not in target_str]
            summary.most_emotionally_significant_moment = moment if remaining else None
            if remaining:
                moment.episode_ids = remaining
            longitudinal_store.update(summary)
            redacted_summaries += 1

    return {"redacted_facts": redacted_facts, "redacted_summaries": redacted_summaries}
