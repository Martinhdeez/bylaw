"""Acceptance tests for AM1 (C7 amendment drafter, apply, amend CLI) and REQ-BT1-3 (baseline).

Written blind from docs/plan/02-amend/requirements.md and contracts.md (plus 01 C1, C2, C4, v1.1).
The hole is pre-registered goal G1 (basic economy flights changed), built by hand on τ² airline
reservation Q79V9W (ivan_kim_3844, basic_economy, one passenger, HAT265 PHX-DTW on 2024-05-28):
cabin to economy, flight to HAT073, cabin back to basic_economy.

Offline, the model is scripted: `draft(..., llm=fake)` in process, and for the CLI a runner that
replaces `bylaw.llm.structured` (the C3 v1.1 signature) before `python -m bylaw` starts.
The scripted model answers with the amendment fields; if the request schema nests them under one
property, the answer is nested the same way.
"""
import copy
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HAND = ROOT / "bylaw" / "rulesets" / "airline.json"

RES, USER, PAY = "Q79V9W", "ivan_kim_3844", "credit_card_1718968"


def flights_args(cabin, flight):
    return {"reservation_id": RES, "cabin": cabin,
            "flights": [{"flight_number": flight, "date": "2024-05-28"}], "payment_id": PAY}


CHAIN = [
    ("update_reservation_flights", flights_args("economy", "HAT265")),
    ("update_reservation_flights", flights_args("economy", "HAT073")),
    ("update_reservation_flights", flights_args("basic_economy", "HAT073")),
]

HOLE = {
    "id": "H1", "class": "A", "goal": "G1", "title": "Basic economy flights changed through a cabin round trip",
    "money_delta": 0.0,
    "chain": [{"tool": t, "args": a, "ok": True, "verdicts": []} for t, a in CHAIN],
    "diff": {}, "goal_true": True, "replays": "5/5",
}

REPORT = {
    "run": {"commit": "", "domain": "airline", "model": "", "mode": "bfs", "started": "2026-10-26T00:00:00",
            "budget": 2000, "goals_commit": ""},
    "holes": [HOLE],
    "ambiguities": [],
    "stats": {"chains_tried": 0, "tool_calls": 0, "llm_calls": 0, "tokens": 0, "seconds": 0.0},
}

# Models the hole: a basic economy reservation cannot change flights, but its cabin can change.
BASE = {
    "domain": "airline",
    "tool_rules": [{
        "id": "R-base-be", "tool": "update_reservation_flights",
        "allow_if": "res is None or res['cabin'] != 'basic_economy' or "
                    "[[f['flight_number'], f['date']] for f in res['flights']] == "
                    "[[f['flight_number'], f['date']] for f in args['flights']]",
        "policy_ref": "Basic economy flights cannot be modified.", "note": ""}],
    "forbidden_goals": [{"id": "G1", "name": "basic_economy_flights_changed",
                         "policy_ref": "Basic economy flights cannot be modified.", "description": ""}],
}

FIX_RULE = {"id": "R-TA3-downgrade", "tool": "update_reservation_flights",
            "allow_if": "not (args.get('cabin') == 'basic_economy' and res is not None "
                        "and res['cabin'] != 'basic_economy')",
            "policy_ref": "A reservation cannot be moved back to basic economy.", "note": ""}
CLOSE_ALL = {"id": "R-TA3-noflights", "tool": "update_reservation_flights", "allow_if": "False",
             "policy_ref": "Flights cannot be modified.", "note": ""}
NOOP = {"id": "R-TA3-noop", "tool": "update_reservation_flights", "allow_if": "True",
        "policy_ref": "Flights can be modified.", "note": ""}


def answer(patch, policy_text="A reservation cannot be moved back to basic economy after a cabin change.",
           rationale="The hole upgrades, changes flights, then downgrades; the downgrade is the step to refuse."):
    return {"id": "A1", "hole_id": "H1", "policy_text": policy_text, "rule_patch": [patch], "rationale": rationale}


def shape_for(schema, payload):
    """Answer flat, or nested under the one property whose schema holds `rule_patch`."""
    props = (schema or {}).get("properties") or {}
    if not props or "rule_patch" in props:
        return payload
    for key, sub in props.items():
        if "rule_patch" in ((sub or {}).get("properties") or {}):
            return {key: payload}
    return payload


class Scripted:
    def __init__(self, payload):
        self.payload, self.calls = payload, []

    def __call__(self, messages, schema, name, effort=None, **opts):
        self.calls.append({"messages": messages, "schema": schema, "name": name})
        return copy.deepcopy(shape_for(schema, self.payload))


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


@pytest.fixture(scope="module")
def amend():
    return importlib.import_module("bylaw.amend")


@pytest.fixture(scope="module")
def rules():
    return importlib.import_module("bylaw.rules")


@pytest.fixture(scope="module")
def airline():
    return importlib.import_module("bylaw.domain").get_domain("airline")


@pytest.fixture
def no_real_llm(monkeypatch):
    llm = importlib.import_module("bylaw.llm")

    def boom(*a, **k):
        raise AssertionError("the real Muse client was called although llm= was given")
    monkeypatch.setattr(llm, "structured", boom)


def tool_names(domain):
    return {t.get("function", t)["name"] for t in domain.tools}


def run_chain(domain, rules, rs):
    """Run CHAIN on a fresh env, checking each step on the snapshot before it. Returns allowed per step."""
    env = domain.fresh_env()
    allowed = []
    for tool, args in CHAIN:
        ok = rules.allowed(rules.check(rs, domain.snapshot(env), tool, args, domain.now))
        allowed.append(ok)
        if not ok:
            break
        step = domain.call(env, tool, **copy.deepcopy(args))
        assert step.ok, (tool, step.error)
    return allowed


def assert_amendment_shape(am, rules, domain, hole_id="H1"):
    assert {"id", "hole_id", "policy_text", "rule_patch", "rationale"} <= set(am)
    assert isinstance(am["id"], str) and am["id"]
    assert am["hole_id"] == hole_id
    assert isinstance(am["rationale"], str) and am["rationale"].strip()
    assert isinstance(am["policy_text"], str) and 1 <= len(sentences(am["policy_text"])) <= 2, am["policy_text"]
    patch = am["rule_patch"]
    assert isinstance(patch, list) and patch
    for r in patch:
        for key in ("id", "tool", "allow_if", "policy_ref"):
            assert isinstance(r[key], str) and r[key], (key, r)
    assert {r["tool"] for r in patch} <= tool_names(domain)
    rules.validate({"domain": "airline", "tool_rules": patch, "forbidden_goals": []})


# ---------- fixture precondition ----------

def test_REQ_AM1_2_hand_built_hole_runs_under_the_base_ruleset(rules, airline):
    assert run_chain(airline, rules, BASE) == [True, True, True]


# ---------- REQ-AM1-1 ----------

def test_REQ_AM1_1_draft_returns_the_C7_amendment(amend, rules, airline, no_real_llm):
    llm = Scripted(answer(FIX_RULE))
    am = amend.draft(airline, copy.deepcopy(BASE), copy.deepcopy(HOLE), llm=llm)
    assert llm.calls, "draft must ask the injected llm"
    assert isinstance(llm.calls[0]["schema"], dict) and isinstance(llm.calls[0]["name"], str)
    assert_amendment_shape(am, rules, airline)
    assert [(r["tool"], r["allow_if"]) for r in am["rule_patch"]] == [(FIX_RULE["tool"], FIX_RULE["allow_if"])]
    json.dumps(am)


def test_REQ_AM1_1_hole_id_comes_from_the_hole(amend, rules, airline, no_real_llm):
    hole = dict(copy.deepcopy(HOLE), id="H7")
    am = amend.draft(airline, copy.deepcopy(BASE), hole, llm=Scripted(answer(FIX_RULE)))
    assert am["hole_id"] == "H7"


def test_REQ_AM1_1_draft_does_not_return_an_invalid_rule_patch(amend, rules, airline, no_real_llm):
    bad = dict(FIX_RULE, allow_if="__import__('os').system('true')")
    try:
        am = amend.draft(airline, copy.deepcopy(BASE), copy.deepcopy(HOLE), llm=Scripted(answer(bad)))
    except Exception:
        return
    rules.validate({"domain": "airline", "tool_rules": am["rule_patch"], "forbidden_goals": []})


def test_REQ_AM1_1_draft_does_not_return_a_long_policy_text(amend, rules, airline, no_real_llm):
    long_text = "One. Two sentences here. Three of them now. And a fourth one."
    try:
        am = amend.draft(airline, copy.deepcopy(BASE), copy.deepcopy(HOLE),
                         llm=Scripted(answer(FIX_RULE, policy_text=long_text)))
    except Exception:
        return
    assert 1 <= len(sentences(am["policy_text"])) <= 2, am["policy_text"]


@pytest.mark.live
def test_REQ_AM1_1_live_draft_returns_a_valid_amendment(amend, rules, airline):
    am = amend.draft(airline, copy.deepcopy(BASE), copy.deepcopy(HOLE))
    assert_amendment_shape(am, rules, airline)
    assert False in run_chain(airline, rules, amend.apply(copy.deepcopy(BASE), am))


# ---------- REQ-AM1-2 ----------

def test_REQ_AM1_2_apply_appends_the_patch_and_is_pure(amend, rules):
    base = copy.deepcopy(BASE)
    am = answer(FIX_RULE)
    out = amend.apply(base, am)
    assert base == BASE, "apply must not modify its input"
    assert am == answer(FIX_RULE)
    assert out is not base
    assert out["tool_rules"] == BASE["tool_rules"] + [FIX_RULE]
    assert out["domain"] == "airline"
    assert out["forbidden_goals"] == BASE["forbidden_goals"]
    rules.validate(out)
    assert amend.apply(copy.deepcopy(BASE), answer(FIX_RULE)) == out


def test_REQ_AM1_2_patched_ruleset_blocks_a_step_of_the_hole(amend, rules, airline):
    allowed = run_chain(airline, rules, amend.apply(copy.deepcopy(BASE), answer(FIX_RULE)))
    assert False in allowed
    assert allowed == [True, True, False]  # the downgrade back to basic_economy


def test_REQ_AM1_2_drafted_amendment_applied_blocks_the_hole(amend, rules, airline, no_real_llm):
    am = amend.draft(airline, copy.deepcopy(BASE), copy.deepcopy(HOLE), llm=Scripted(answer(FIX_RULE)))
    assert False in run_chain(airline, rules, amend.apply(copy.deepcopy(BASE), am))


def test_REQ_AM1_2_colliding_rule_ids_never_reach_the_ruleset(amend):
    clash = dict(FIX_RULE, id="R-base-be")
    try:
        out = amend.apply(copy.deepcopy(BASE), answer(clash))
    except Exception:
        return
    ids = [r["id"] for r in out["tool_rules"]]
    assert len(ids) == len(set(ids)), ids


# ---------- REQ-AM1-3 and REQ-BT1-3: the amend CLI ----------

RUNNER = '''
import copy, json, runpy, sys
import bylaw.llm

payload = json.load(open(sys.argv[1]))
log = sys.argv[2]

def shape_for(schema, payload):
    props = (schema or {}).get("properties") or {}
    if not props or "rule_patch" in props:
        return payload
    for key, sub in props.items():
        if "rule_patch" in ((sub or {}).get("properties") or {}):
            return {key: payload}
    return payload

def fake(messages, schema, name, effort=None, **opts):
    with open(log, "a") as f:
        f.write(json.dumps({"name": name}) + "\\n")
    return copy.deepcopy(shape_for(schema, payload))

bylaw.llm.structured = fake
sys.argv = ["bylaw"] + sys.argv[3:]
runpy.run_module("bylaw", run_name="__main__", alter_sys=True)
'''


def run_amend(tmp, patch):
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "runner.py").write_text(RUNNER)
    (tmp / "answer.json").write_text(json.dumps(answer(patch)))
    (tmp / "report.json").write_text(json.dumps(REPORT))
    out, log = tmp / "amended.json", tmp / "llm.log"
    env = {**__import__("os").environ, "MODEL_API_KEY": ""}
    proc = subprocess.run(
        [sys.executable, str(tmp / "runner.py"), str(tmp / "answer.json"), str(log),
         "amend", str(tmp / "report.json"), "-o", str(out)],
        cwd=ROOT, capture_output=True, text=True, timeout=1800, env=env,
    )
    assert proc.returncode == 0, proc.stderr[-4000:]
    assert log.exists() and log.read_text().strip(), "the amend CLI never asked the (scripted) model"
    return json.loads(out.read_text())


@pytest.fixture(scope="module")
def amended_closing(tmp_path_factory):
    return run_amend(tmp_path_factory.mktemp("close"), CLOSE_ALL)


@pytest.fixture(scope="module")
def amended_noop(tmp_path_factory):
    return run_amend(tmp_path_factory.mktemp("noop"), NOOP)


@pytest.fixture(scope="module")
def baseline(airline):
    """The hand RuleSet's own backtest, through the C8 API."""
    bt = importlib.import_module("bylaw.backtest")
    return bt.backtest(airline, json.loads(HAND.read_text()))


def only_hole(report):
    assert [h["id"] for h in report["holes"]] == ["H1"]
    return report["holes"][0]


def test_REQ_AM1_3_amend_cli_adds_amendment_closes_and_backtest(amended_closing, rules, airline):
    hole = only_hole(amended_closing)
    for key in ("class", "goal", "chain", "goal_true", "replays"):
        assert hole[key] == HOLE[key], key
    assert_amendment_shape(hole["amendment"], rules, airline)
    assert [(r["tool"], r["allow_if"]) for r in hole["amendment"]["rule_patch"]] == \
        [(CLOSE_ALL["tool"], CLOSE_ALL["allow_if"])]
    assert isinstance(hole["closes"], bool)
    b = hole["backtest"]
    assert b["tasks"] == 43
    assert isinstance(b["blocked"], int) and isinstance(b["baseline_blocked"], int)
    assert isinstance(b["blocked_tasks"], list)
    assert amended_closing["run"]["domain"] == "airline"


def test_REQ_AM1_3_closes_true_when_the_reaudit_finds_no_hole(amended_closing):
    # No flight update at all: G1 cannot be reached.
    assert only_hole(amended_closing)["closes"] is True


def test_REQ_AM1_3_closes_false_when_the_amendment_changes_nothing(amended_noop):
    # A rule that is always true leaves the hand RuleSet's G1 hole (spike H1) open.
    assert only_hole(amended_noop)["closes"] is False


def test_REQ_BT1_3_baseline_is_the_unpatched_hand_ruleset(amended_closing, amended_noop, baseline):
    assert baseline["tasks"] == 43
    assert only_hole(amended_closing)["backtest"]["baseline_blocked"] == baseline["blocked"]
    assert only_hole(amended_noop)["backtest"]["baseline_blocked"] == baseline["blocked"]


def test_REQ_BT1_3_a_no_op_amendment_costs_nothing(amended_noop, baseline):
    b = only_hole(amended_noop)["backtest"]
    assert b["blocked"] == b["baseline_blocked"] == baseline["blocked"]


def test_REQ_BT1_3_cost_is_counted_against_the_baseline(amended_closing, baseline):
    # Blocking every flight update also blocks the 12 non-cancel gold tasks that update flights,
    # on top of what the hand RuleSet already blocks. Task 7 (a cancel task) may count as unknown.
    flight_tasks = {"11", "15", "16", "17", "18", "21", "22", "30", "32", "33", "37", "44"}
    base_ids = {r["id"] for r in baseline["results"] if r["blocked"]}
    b = only_hole(amended_closing)["backtest"]
    expected = len(base_ids | flight_tasks)
    assert b["blocked"] in (expected, len(base_ids | flight_tasks | {"7"}))
    assert b["blocked"] - b["baseline_blocked"] >= len(flight_tasks - base_ids)
    assert flight_tasks - base_ids <= set(b["blocked_tasks"])
