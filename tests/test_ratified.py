"""AP1 / C10: the ratified store appends a hole's amendment once and yields base + patches as the effective RuleSet."""
import json

import pytest

from bylaw import ratified
from bylaw.env.tau2_airline import RULESET
from bylaw.rules import validate

HAND = json.loads(RULESET.read_text())
PATCH = {"id": "R-test-amend-1", "tool": "cancel_reservation", "allow_if": "False", "policy_ref": "test", "note": ""}
HOLE = {"key": "G1:T1QOBS", "amendment": {"id": "A1", "hole_id": "H1", "policy_text": "No cancels.",
                                          "rule_patch": [PATCH], "rationale": "test"}}


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("BYLAW_RATIFIED_DIR", str(tmp_path))
    return tmp_path


def test_missing_store_loads_as_no_amendments():
    assert ratified.load("airline") == {"domain": "airline", "amendments": []}
    assert ratified.effective_ruleset("airline") == HAND


def test_ratify_writes_the_c10_file_under_the_env_dir(store):
    ratified.ratify("airline", HOLE)
    data = json.loads((store / "airline.json").read_text())
    (a,) = data["amendments"]
    assert data["domain"] == "airline"
    assert (a["id"], a["hole_key"], a["rule_patch"], a["policy_text"]) == ("A1", "G1:T1QOBS", [PATCH], "No cancels.")
    assert a["ratified_at"].startswith("20")


def test_ratifying_the_same_hole_twice_stores_it_once():
    ratified.ratify("airline", HOLE)
    ratified.ratify("airline", HOLE)
    assert len(ratified.load("airline")["amendments"]) == 1


def test_effective_ruleset_is_the_hand_ruleset_plus_the_patch():
    ratified.ratify("airline", HOLE)
    eff = ratified.effective_ruleset("airline")
    validate(eff)
    assert eff["tool_rules"] == HAND["tool_rules"] + [PATCH]


def test_a_patch_whose_rule_id_collides_is_refused_and_not_stored():
    bad = {**HOLE, "key": "G2:X", "amendment": {**HOLE["amendment"], "rule_patch": [dict(PATCH, id=HAND["tool_rules"][0]["id"])]}}
    with pytest.raises(ValueError):
        ratified.ratify("airline", bad)
    assert ratified.load("airline")["amendments"] == []
