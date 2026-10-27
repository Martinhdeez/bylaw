"""EX1/GA1: report JSON (C4 v1.7) — schema, classes A/B/C with gold adjudication, every entry proven (REQ-EX1-1..3)."""
import copy
import json

import jsonschema
import pytest

from bylaw.domain import get_domain
from bylaw.env.tau2_airline import RULESET
from bylaw import report as report_mod
from bylaw.report import REPORT_SCHEMA, audit, classify

DOMAIN = get_domain("airline")
RULES = json.loads(RULESET.read_text())


@pytest.fixture(scope="module")
def report():
    return audit(DOMAIN, RULES, budget=40)


def test_small_audit_validates_and_every_hole_is_proven(report):
    jsonschema.validate(report, REPORT_SCHEMA)
    assert report["run"]["mode"] == "bfs" and report["run"]["budget"] == 40
    assert 0 < report["stats"]["tool_calls"] <= 40
    for h in report["holes"] + report["contradictions"] + report["ambiguities"]:
        assert h["replays"] == "5/5" and h["goal_true"]
        assert h["gold"]["sanctioned"] == bool(h["gold"]["tasks"])
        assert all(s["ok"] and all(v["ok"] for v in s["verdicts"]) for s in h["chain"])
        assert h["key"].startswith(h["goal"] + ":")


def test_schema_rejects_a_hole_without_its_proof(report):
    bad = copy.deepcopy(report)
    bad["holes"] = [{"id": "H1", "class": "A", "goal": "G1"}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, REPORT_SCHEMA)


def test_cancel_then_rebook_for_the_same_user_is_an_ambiguity():
    chain = [{"tool": "cancel_reservation", "args": {"reservation_id": "T1QOBS"}},
             {"tool": "book_reservation", "args": {"user_id": "harper_lopez_1489"}}]
    db = DOMAIN.snapshot(DOMAIN.fresh_env())
    assert classify(DOMAIN, db, "G3", chain) == "C"
    assert classify(DOMAIN, db, "G3", chain[:1]) == "A"
    assert classify(DOMAIN, db, "G3", chain[::-1]) == "A"  # a booking before the cancel is not a rebook
    assert classify(DOMAIN, db, "G7", chain[:1]) == "C"  # pre-registered Class C goal


def test_a_gold_sanctioned_goal_is_a_contradiction_not_a_hole(report):
    chain = [{"tool": "update_reservation_flights", "args": {"reservation_id": "T1QOBS"}}]
    db = DOMAIN.snapshot(DOMAIN.fresh_env())
    assert classify(DOMAIN, db, "G2", chain) == "B"  # task 7 does upgrade-then-cancel
    assert classify(DOMAIN, db, "G3", chain) == "A"  # no gold task adds insurance after booking
    assert all(e["class"] == "B" and e["gold"]["sanctioned"] for e in report["contradictions"])
    assert all(e["class"] == "A" and not e["gold"]["sanctioned"] for e in report["holes"])
    assert report["contradictions"], "the G5 downgrade found at depth 1 must be listed as a contradiction"


def test_schema_requires_the_contradictions_list_and_the_gold_block(report):
    no_list = copy.deepcopy(report)
    del no_list["contradictions"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(no_list, REPORT_SCHEMA)
    no_gold = copy.deepcopy(report)
    del no_gold["contradictions"][0]["gold"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(no_gold, REPORT_SCHEMA)


def test_an_entry_that_does_not_replay_5_of_5_is_dropped(monkeypatch):
    monkeypatch.setattr(report_mod, "prove", lambda *a, **k: "4/5")
    r = audit(DOMAIN, RULES, budget=10)
    assert r["holes"] == r["contradictions"] == r["ambiguities"] == []


def test_a_cancel_rebook_ambiguity_does_not_shadow_a_finding_with_the_same_key(monkeypatch):
    # 1KUOX2: basic economy booked inside 24h. cancel+rebook (C) and cabin change + new date (B) both reach G1.
    rid = "1KUOX2"
    monkeypatch.setattr(report_mod, "search", lambda *a, **k: _only(rid))
    r = audit(DOMAIN, RULES, budget=20)
    assert "G1:" + rid in {e["key"] for e in r["contradictions"]}
    assert "G1:" + rid in {e["key"] for e in r["ambiguities"]}


def test_a_longer_chain_is_not_listed_again_for_an_outcome_its_prefix_already_reached(monkeypatch):
    # 0QOP4M: a downgrade alone keeps free bags over the allowance (G5); downgrade + cancel + rebook adds nothing.
    monkeypatch.setattr(report_mod, "search", lambda *a, **k: _only("0QOP4M", depths=(1, 2, 3)))
    r = audit(DOMAIN, RULES, budget=10**4)
    found = r["holes"] + r["contradictions"] + r["ambiguities"]
    for e in found:
        for other in found:
            shorter = [(s["tool"], s["args"]) for s in other["chain"]]
            assert other is e or other["key"] != e["key"] or [(s["tool"], s["args"]) for s in e["chain"][:len(shorter)]] != shorter, e["id"]


def _only(rid, depths=(1, 2)):
    from bylaw import proposer
    db = DOMAIN.snapshot(DOMAIN.fresh_env())
    for depth in depths:
        yield from proposer._chains(db, rid, proposer._state(db, rid), depth, None)


def test_run_block_names_the_commit_and_the_goals_commit(report):
    import re
    import subprocess

    def git(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout.strip()

    run = report["run"]
    assert re.fullmatch(r"[0-9a-f]{7,}(-dirty)?", run["commit"]), run["commit"]
    assert run["commit"].split("-")[0] == git("rev-parse", "--short", "HEAD")
    assert run["commit"].endswith("-dirty") == bool(git("status", "--porcelain", "--untracked-files=no"))
    assert run["goals_commit"] == git("log", "-1", "--format=%h", "--", "bylaw/goals.py") != ""
