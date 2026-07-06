import json

from infra.llm.json_extract import extract_json


def test_plain_json_passthrough():
    assert json.loads(extract_json('{"a": 1}')) == {"a": 1}


def test_strips_json_fence():
    raw = '```json\n{"goal_detected": true, "x": 2}\n```'
    assert json.loads(extract_json(raw)) == {"goal_detected": True, "x": 2}


def test_strips_bare_fence():
    assert json.loads(extract_json('```\n{"a": 1}\n```')) == {"a": 1}


def test_extracts_from_preamble_prose():
    raw = 'Sure! Here is the classification:\n{"primary_label": "joy", "valence": 0.8} hope that helps'
    assert json.loads(extract_json(raw))["primary_label"] == "joy"


def test_handles_nested_objects():
    raw = 'noise {"new_goal": {"inferred_title": "run 5k"}, "ok": true} trailing'
    assert json.loads(extract_json(raw))["new_goal"]["inferred_title"] == "run 5k"


def test_array_payload():
    assert json.loads(extract_json('prefix [1, 2, 3] suffix')) == [1, 2, 3]


def test_empty_and_garbage_are_returned_as_is():
    assert extract_json("") == ""
    assert extract_json("no json here") == "no json here"
