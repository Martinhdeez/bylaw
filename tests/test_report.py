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


def test_muse_audit_proves_what_its_templates_find_and_counts_its_calls(report):
    from tests.test_proposer import G7_TWICE, ScriptedMuse

    muse = audit(DOMAIN, RULES, budget=40, use_llm=True, llm=ScriptedMuse({"G7": [G7_TWICE]}))
    jsonschema.validate(muse, REPORT_SCHEMA)
    assert muse["run"]["mode"] == "muse"
    assert muse["stats"]["llm_calls"] == len(DOMAIN.goals) and muse["stats"]["tool_calls"] <= 40
    g7 = [e for e in muse["ambiguities"] if e["goal"] == "G7"]
    assert g7 and all(e["replays"] == "5/5" and [s["tool"] for s in e["chain"]] == ["send_certificate"] * 2 for e in g7)
    assert not any(e["goal"] == "G7" for e in report["ambiguities"])  # blind BFS never sends certificates


def test_a_muse_template_that_finds_nothing_hands_its_budget_back_to_the_bfs():
    from tests.test_proposer import G7_TWICE, ScriptedMuse, _cert

    dud = {**G7_TWICE, "steps": [_cert(), _cert("lost luggage")]}  # the rules block step 2: never a hole
    muse = audit(DOMAIN, RULES, budget=40, use_llm=True, llm=ScriptedMuse({"G7": [dud]}))
    # two misses drop the template; each executed 1 write step (C6 v1.8 charges executed steps), so the BFS gets 38
    keys = lambda r: [e["key"] for e in r["holes"] + r["ambiguities"]]
    bfs = audit(DOMAIN, RULES, budget=38)
    assert keys(muse) == keys(bfs)
    assert muse["stats"]["tool_calls"] == 2 + bfs["stats"]["tool_calls"]


ONLY_1KUOX2 = {"rationale": "cabin change, then a date change the basic-economy rule no longer sees",
               "where": "args['reservation_id'] == '1KUOX2'", "steps": [
                   {"tool": "update_reservation_flights", "args_json": json.dumps({
                       "reservation_id": "1KUOX2", "cabin": "economy", "payment_id": "credit_card_1697462",
                       "flights": [{"flight_number": "HAT036", "date": day}]})} for day in ("2024-05-22", "2024-05-21")]}


def test_found_records_the_cumulative_write_steps_at_which_each_hole_was_proved():
    from tests.test_proposer import ScriptedMuse

    r = audit(DOMAIN, RULES, budget=30, use_llm=True, llm=ScriptedMuse({"G1": [ONLY_1KUOX2]}))
    found = r["stats"]["found"]
    assert found[0]["key"] == "G1:1KUOX2" and found[0]["tool_calls"] == 2  # the first chain, 2 steps executed
    bfs = audit(DOMAIN, RULES, budget=28)  # what the BFS does with the rest, from its own start
    assert [f["tool_calls"] - 2 for f in found[1:]] == [f["tool_calls"] for f in bfs["stats"]["found"]]
    assert [f["key"] for f in found] == [h["key"] for h in r["holes"]]


def test_a_failed_muse_call_is_counted_and_never_aborts_the_audit():
    from tests.test_proposer import G7_TWICE, ScriptedMuse

    ok = ScriptedMuse({"G7": [G7_TWICE]})

    def flaky(messages, schema, name, **kw):
        if json.loads(messages[-1]["content"])["goal"]["id"] in ("G1", "G2"):
            raise RuntimeError("empty reply")
        return ok(messages, schema, name, **kw)

    r = audit(DOMAIN, RULES, budget=30, use_llm=True, llm=flaky)
    assert r["stats"]["llm_errors"] == 2 and r["stats"]["llm_calls"] == len(DOMAIN.goals)
    assert any(e["goal"] == "G7" for e in r["ambiguities"])
