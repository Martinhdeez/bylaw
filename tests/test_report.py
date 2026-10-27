"""EX1: report JSON (C4) — schema, Class C for cancel+rebook, every listed hole proven (REQ-EX1-1..3)."""
import copy
import json

import jsonschema
import pytest

from bylaw.domain import get_domain
from bylaw.env.tau2_airline import RULESET
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
    for h in report["holes"] + report["ambiguities"]:
        assert h["replays"] == "5/5" and h["goal_true"]
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
    assert classify(DOMAIN, db, "G1", chain) == "C"
    assert classify(DOMAIN, db, "G1", chain[:1]) == "A"
    assert classify(DOMAIN, db, "G1", chain[::-1]) == "A"  # a booking before the cancel is not a rebook
    assert classify(DOMAIN, db, "G7", chain[:1]) == "C"  # pre-registered Class C goal
