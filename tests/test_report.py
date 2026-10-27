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
    # 0QOP4M: a cabin downgrade alone keeps free bags over the allowance (G5), found at depth 1.
    monkeypatch.setattr(report_mod, "search", lambda *a, **k: _only("0QOP4M", depths=(1,)))
    findings = lambda r: r["holes"] + r["contradictions"] + r["ambiguities"]  # noqa: E731
    assert "G5:0QOP4M" in {e["key"] for e in findings(audit(DOMAIN, RULES, budget=50))}
    monkeypatch.setattr(report_mod, "prove", lambda *a, **k: "4/5")
    assert findings(audit(DOMAIN, RULES, budget=50)) == []


def test_a_cancel_rebook_ambiguity_does_not_shadow_a_hole_with_the_same_key(monkeypatch):
    # 1KUOX2: basic economy booked inside 24h. cancel+rebook (C) comes first, cabin change + new date reaches G1 too.
    # With no gold task on G1, that second chain is a Class A hole and takes the key from the ambiguity.
    rid = "1KUOX2"
    monkeypatch.setattr(report_mod, "search", lambda *a, **k: _only(rid))
    monkeypatch.setattr(report_mod, "gold_goals", lambda domain: {})
    r = audit(DOMAIN, RULES, budget=20)
    assert "G1:" + rid in {e["key"] for e in r["holes"]}
    assert "G1:" + rid not in {e["key"] for e in r["ambiguities"]}


def test_a_key_is_listed_once_across_holes_contradictions_and_ambiguities(monkeypatch):
    # With G1 gold-sanctioned, the first chain to G1:1KUOX2 (the 24h cancel+rebook, Class C) keeps the key (REQ-EX1-3).
    rid = "1KUOX2"
    monkeypatch.setattr(report_mod, "search", lambda *a, **k: _only(rid))
    r = audit(DOMAIN, RULES, budget=20)
    keys = [e["key"] for e in r["holes"] + r["contradictions"] + r["ambiguities"]]
    assert len(keys) == len(set(keys))
    assert "G1:" + rid in {e["key"] for e in r["ambiguities"]}


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
    keys = lambda r: [e["key"] for e in r["holes"] + r["contradictions"] + r["ambiguities"]]  # noqa: E731
    bfs = audit(DOMAIN, RULES, budget=38)
    assert keys(muse) == keys(bfs)
    assert muse["stats"]["tool_calls"] == 2 + bfs["stats"]["tool_calls"]


ONLY_1KUOX2 = {"rationale": "cabin change, then a date change the basic-economy rule no longer sees",
               "where": "args['reservation_id'] == '1KUOX2'", "steps": [
                   {"tool": "update_reservation_flights", "args_json": json.dumps({
                       "reservation_id": "1KUOX2", "cabin": "economy", "payment_id": "credit_card_1697462",
                       "flights": [{"flight_number": "HAT036", "date": day}]})} for day in ("2024-05-22", "2024-05-21")]}


def test_found_records_the_cumulative_write_steps_at_which_each_hole_was_proved(monkeypatch):
    from tests.test_proposer import ScriptedMuse

    monkeypatch.setattr(report_mod, "gold_goals", lambda domain: {})  # every finding a Class A hole (C4 v1.7)
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


def test_a_hole_that_takes_the_key_from_an_ambiguity_is_fed_back_as_a_hit(monkeypatch):
    # C6 v1.8: hit means the chain proved a finding. The Class A chain to G1:1KUOX2 replaces the cancel+rebook
    # ambiguity under the same key: the entry count does not grow, but the chain still proved a finding.
    rid, log = "1KUOX2", []

    def search(*a, **k):
        for chain in _only(rid):
            log.append((chain, (yield chain)))

    monkeypatch.setattr(report_mod, "search", search)
    monkeypatch.setattr(report_mod, "gold_goals", lambda domain: {})
    hole = next(h for h in audit(DOMAIN, RULES, budget=20)["holes"] if h["key"] == "G1:" + rid)
    calls = [(s["tool"], s["args"]) for s in hole["chain"]]
    assert [fb[1] for chain, fb in log if chain == calls] == [True]
