"""Tests for SC-4 User Format Profile (architecture doc §6.5-§6.6)."""

from backend.layer9_output import user_format_profile as ufp
from backend.layer9_output.schemas import LengthPreference, UserFormatProfile


# ── Defaults (§6.5) ──────────────────────────────────────────────────────────
def test_initialize_defaults():
    p = ufp.initialize_defaults("u1")
    assert p.user_id == "u1"
    assert p.preferred_length == LengthPreference.MEDIUM.value
    assert p.emoji_usage_rate == 0.0


# ── Preference shifting (§6.6) ───────────────────────────────────────────────
def test_shift_shorter_steps_down_and_floors():
    assert ufp.shift_preference_shorter(LengthPreference.LONG.value) == LengthPreference.MEDIUM.value
    assert ufp.shift_preference_shorter(LengthPreference.MEDIUM.value) == LengthPreference.SHORT.value
    assert ufp.shift_preference_shorter(LengthPreference.SHORT.value) == LengthPreference.SHORT.value


# ── Engagement signals (§6.6) ────────────────────────────────────────────────
def test_fast_reply_after_long_response_prefers_shorter():
    p = ufp.initialize_defaults("u1")  # medium
    p = ufp.update_format_profile(p, nova_response_length=500,
                                  user_response_latency_ms=1500, user_response_length=120)
    assert p.preferred_length == LengthPreference.SHORT.value


def test_tiny_reply_ratio_prefers_shorter():
    p = ufp.initialize_defaults("u1")
    p = ufp.update_format_profile(p, nova_response_length=400,
                                  user_response_latency_ms=10000, user_response_length=20)
    assert p.preferred_length == LengthPreference.SHORT.value


def test_engagement_update_bumps_version():
    p = ufp.initialize_defaults("u1")
    p = ufp.update_format_profile(p, nova_response_length=100,
                                  user_response_latency_ms=8000, user_response_length=90)
    assert p.version == 1


# ── Real emoji/slang/length signals (§6.5-§6.6, closed 2026-08-09) ──────────
# update_format_profile previously never computed these -- emoji_usage_rate/uses_slang_themselves
# stayed pinned at their 0.0/False defaults forever, silently defeating format_adapter.py's
# emoji-policy and allow_slang decisions (both read straight off this profile).
def test_avg_user_message_length_moves_toward_a_real_users_messages():
    p = ufp.initialize_defaults("u1")
    for _ in range(5):
        p = ufp.update_format_profile(p, nova_response_length=100,
                                      user_response_latency_ms=8000, user_response_length=200,
                                      user_message_text="a longer message than before")
    assert p.avg_user_message_length > 50   # moved up from the 0.0 default toward 200


def test_emoji_usage_rate_moves_toward_a_users_real_emoji_habit():
    p = ufp.initialize_defaults("u1")
    for _ in range(5):
        p = ufp.update_format_profile(p, nova_response_length=100,
                                      user_response_latency_ms=8000, user_response_length=10,
                                      user_message_text="love this so much! 😊🎉")
    assert p.emoji_usage_rate > 0.3   # moved up from the 0.0 default


def test_emoji_usage_rate_stays_low_for_a_user_who_never_uses_emoji():
    p = ufp.initialize_defaults("u1")
    for _ in range(5):
        p = ufp.update_format_profile(p, nova_response_length=100,
                                      user_response_latency_ms=8000, user_response_length=10,
                                      user_message_text="that sounds reasonable to me")
    assert p.emoji_usage_rate == 0.0


def test_uses_slang_themselves_flips_true_on_a_real_casual_message():
    p = ufp.initialize_defaults("u1")
    assert p.uses_slang_themselves is False
    p = ufp.update_format_profile(p, nova_response_length=100, user_response_latency_ms=8000,
                                  user_response_length=10, user_message_text="lol yeah gonna do that")
    assert p.uses_slang_themselves is True


def test_uses_slang_themselves_stays_false_for_a_formal_user():
    p = ufp.initialize_defaults("u1")
    p = ufp.update_format_profile(p, nova_response_length=100, user_response_latency_ms=8000,
                                  user_response_length=10,
                                  user_message_text="Regarding your point, I shall consider it.")
    assert p.uses_slang_themselves is False


# ── Explicit feedback (§6.6) ─────────────────────────────────────────────────
def test_explicit_concise_feedback_sets_always_brief():
    p = ufp.update_format_profile(ufp.initialize_defaults("u1"), nova_response_length=100,
                                  user_response_latency_ms=5000, user_response_length=90,
                                  explicit_format_feedback="can you be more concise")
    assert p.always_brief is True
    assert p.explicit_format_feedback_events  # logged


def test_explicit_bullets_feedback_sets_prefers_bullets():
    p = ufp.update_format_profile(ufp.initialize_defaults("u1"), nova_response_length=100,
                                  user_response_latency_ms=5000, user_response_length=90,
                                  explicit_format_feedback="can you list that out")
    assert p.prefers_bullets is True


def test_classify_format_feedback():
    assert ufp.classify_format_feedback("give me the short version") == "short"
    assert ufp.classify_format_feedback("can you list that out") == "bullets"
    assert ufp.classify_format_feedback("just write normally please") == "no_markdown"
    assert ufp.classify_format_feedback("tell me more, elaborate") == "long"
    assert ufp.classify_format_feedback("thanks that's great") is None


# ── Validation (§6.5) ────────────────────────────────────────────────────────
def test_emoji_usage_rate_is_clamped():
    p = ufp.normalize(UserFormatProfile(user_id="u1", emoji_usage_rate=1.8))
    assert p.emoji_usage_rate == 1.0
    p2 = ufp.normalize(UserFormatProfile(user_id="u1", emoji_usage_rate=-0.3))
    assert p2.emoji_usage_rate == 0.0
