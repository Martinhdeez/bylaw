"""AP1 / C10: the ratified store appends a hole's amendment once and yields base + patches as the effective RuleSet."""
import json
import threading

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
    assert (a["id"], a["hole_key"], a["policy_text"]) == ("A1", "G1:T1QOBS", "No cancels.")
    assert a["rule_patch"] == [dict(PATCH, id="G1:T1QOBS/R-test-amend-1")]  # 03 v1.3: <hole_key>/<rule_id>
    assert a["ratified_at"].startswith("20")


def test_ratifying_the_same_hole_twice_stores_it_once():
    ratified.ratify("airline", HOLE)
    ratified.ratify("airline", HOLE)
    assert len(ratified.load("airline")["amendments"]) == 1


def test_effective_ruleset_is_the_hand_ruleset_plus_the_patch():
    ratified.ratify("airline", HOLE)
    eff = ratified.effective_ruleset("airline")
    validate(eff)
    assert eff["tool_rules"] == HAND["tool_rules"] + [dict(PATCH, id="G1:T1QOBS/R-test-amend-1")]


def test_two_amendments_reusing_a_rule_id_both_apply():
    """03 v1.3: Muse reuses rule ids across holes; namespacing by hole key keeps them apart."""
    other = {**HOLE, "key": "G5:00GMVN"}
    ratified.ratify("airline", HOLE)
    ratified.ratify("airline", other)
    eff = ratified.effective_ruleset("airline")
    validate(eff)
    assert [r["id"] for r in eff["tool_rules"][-2:]] == ["G1:T1QOBS/R-test-amend-1", "G5:00GMVN/R-test-amend-1"]


def test_a_patch_with_a_duplicate_rule_id_is_refused_and_not_stored():
    bad = {**HOLE, "amendment": {**HOLE["amendment"], "rule_patch": [PATCH, PATCH]}}
    with pytest.raises(ValueError):
        ratified.ratify("airline", bad)
    assert ratified.load("airline")["amendments"] == []


def test_concurrent_ratifies_of_different_holes_all_land():
    holes = [{**HOLE, "key": f"G1:R{i}", "amendment": {**HOLE["amendment"], "id": f"A{i}",
                                                       "rule_patch": [dict(PATCH, id=f"R-test-amend-{i}")]}}
             for i in range(16)]
    barrier = threading.Barrier(len(holes))

    def go(h):
        barrier.wait()
        ratified.ratify("airline", h)

    threads = [threading.Thread(target=go, args=(h,)) for h in holes]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(a["hole_key"] for a in ratified.load("airline")["amendments"]) == sorted(h["key"] for h in holes)
