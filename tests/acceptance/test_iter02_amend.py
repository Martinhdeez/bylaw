"""Acceptance tests for AM1 (C7 amendment drafter, apply, amend CLI) and REQ-BT1-3 (baseline).

Written blind from docs/plan/02-amend/requirements.md and contracts.md (plus 01 C1, C2, C4, v1.1).
The hole is pre-registered goal G1 (basic economy flights changed), built by hand on τ² airline
reservation Q79V9W (ivan_kim_3844, basic_economy, one passenger, HAT265 PHX-DTW on 2024-05-28):
cabin to economy, flight to HAT073, cabin back to basic_economy.

Offline, the model is scripted (C7 v1.1): `draft(..., llm=fake)` or a replaced
`bylaw.llm.structured` in process, and for the CLI a runner that replaces `bylaw.llm.structured`
before `python -m bylaw` starts. The model answers `{policy_text, rule_patch, rationale}`;
`draft` adds `id` and `hole_id`, validates, retries once, then raises ValueError.
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
    "diff": {}, "goal_true": True, "replays": "5/5", "key": f"G1:{RES}",
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


POLICY = "A reservation cannot be moved back to basic economy after a cabin change."


def answer(patch, policy_text=POLICY,
           rationale="The hole upgrades, changes flights, then downgrades; the downgrade is the step to refuse."):
    """What the model returns to draft (C7 v1.1)."""
    return {"policy_text": policy_text, "rule_patch": [patch], "rationale": rationale}


def amendment(patch):
    """A full C7 amendment, as apply receives it."""
    return {"id": "A1", "hole_id": "H1", **answer(patch)}


class Scripted:
    """Answers each call with the next payload; the last one repeats."""
    def __init__(self, *payloads):
        self.payloads, self.calls = list(payloads), []

    def __call__(self, messages, schema, name, effort=None, **opts):
        self.calls.append({"messages": messages, "schema": schema, "name": name, "effort": effort})
        return copy.deepcopy(self.payloads[min(len(self.calls), len(self.payloads)) - 1])


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


# ---------- REQ-AM1-1 ----------

def test_REQ_AM1_1_draft_returns_the_C7_amendment(amend, rules, airline, no_real_llm):
    llm = Scripted(answer(FIX_RULE))
    am = amend.draft(airline, copy.deepcopy(BASE), copy.deepcopy(HOLE), llm=llm)
    assert len(llm.calls) == 1, "a valid first answer needs no retry"
    assert isinstance(llm.calls[0]["schema"], dict) and isinstance(llm.calls[0]["name"], str)
    assert llm.calls[0]["effort"] == "high"
    assert_amendment_shape(am, rules, airline)
    assert am["policy_text"] == POLICY
    assert [(r["tool"], r["allow_if"]) for r in am["rule_patch"]] == [(FIX_RULE["tool"], FIX_RULE["allow_if"])]
    json.dumps(am)


def test_REQ_AM1_1_hole_id_comes_from_the_hole(amend, rules, airline, no_real_llm):
    hole = dict(copy.deepcopy(HOLE), id="H7")
    am = amend.draft(airline, copy.deepcopy(BASE), hole, llm=Scripted(answer(FIX_RULE)))
    assert am["hole_id"] == "H7"


BAD_RULE = dict(FIX_RULE, allow_if="__import__('os').system('true')")
LONG_TEXT = "One. Two sentences here. Three of them now. And a fourth one."


def test_REQ_AM1_1_draft_raises_after_two_invalid_rule_patches(amend, airline, no_real_llm):
    llm = Scripted(answer(BAD_RULE))
    with pytest.raises(ValueError):
        amend.draft(airline, copy.deepcopy(BASE), copy.deepcopy(HOLE), llm=llm)
    assert len(llm.calls) == 2


def test_REQ_AM1_1_draft_raises_after_two_long_policy_texts(amend, airline, no_real_llm):
    llm = Scripted(answer(FIX_RULE, policy_text=LONG_TEXT))
    with pytest.raises(ValueError):
        amend.draft(airline, copy.deepcopy(BASE), copy.deepcopy(HOLE), llm=llm)
    assert len(llm.calls) == 2


@pytest.mark.parametrize("first", [answer(BAD_RULE), answer(FIX_RULE, policy_text=LONG_TEXT)],
                         ids=["invalid_patch", "long_text"])
def test_REQ_AM1_1_draft_retries_once_and_returns_the_valid_answer(amend, rules, airline, no_real_llm, first):
    llm = Scripted(first, answer(FIX_RULE))
    am = amend.draft(airline, copy.deepcopy(BASE), copy.deepcopy(HOLE), llm=llm)
    assert len(llm.calls) == 2
    assert_amendment_shape(am, rules, airline)
    assert am["policy_text"] == POLICY
    assert [r["allow_if"] for r in am["rule_patch"]] == [FIX_RULE["allow_if"]]


def test_REQ_AM1_1_draft_uses_bylaw_llm_structured_when_no_llm_is_given(amend, rules, airline, monkeypatch):
    llm = Scripted(answer(FIX_RULE))
    monkeypatch.setattr(importlib.import_module("bylaw.llm"), "structured", llm)
    am = amend.draft(airline, copy.deepcopy(BASE), copy.deepcopy(HOLE))
    assert len(llm.calls) == 1
    assert_amendment_shape(am, rules, airline)


@pytest.mark.live
def test_REQ_AM1_1_live_draft_returns_a_valid_amendment(amend, rules, airline):
    am = amend.draft(airline, copy.deepcopy(BASE), copy.deepcopy(HOLE))
    assert_amendment_shape(am, rules, airline)
    assert False in run_chain(airline, rules, amend.apply(copy.deepcopy(BASE), am))


# ---------- REQ-AM1-2 ----------

def test_REQ_AM1_2_apply_appends_the_patch_and_is_pure(amend, rules):
    base = copy.deepcopy(BASE)
    am = amendment(FIX_RULE)
    out = amend.apply(base, am)
    assert base == BASE, "apply must not modify its input"
    assert am == amendment(FIX_RULE)
    assert out is not base
    assert out["tool_rules"] == BASE["tool_rules"] + [FIX_RULE]
    assert out["domain"] == "airline"
    assert out["forbidden_goals"] == BASE["forbidden_goals"]
    rules.validate(out)
    assert amend.apply(copy.deepcopy(BASE), amendment(FIX_RULE)) == out


def test_REQ_AM1_2_patched_ruleset_blocks_a_step_of_the_hole(amend, rules, airline):
    assert run_chain(airline, rules, BASE) == [True, True, True], "fixture: the hole runs under BASE"
    allowed = run_chain(airline, rules, amend.apply(copy.deepcopy(BASE), amendment(FIX_RULE)))
    assert False in allowed
    assert allowed == [True, True, False]  # the downgrade back to basic_economy


def test_REQ_AM1_2_drafted_amendment_applied_blocks_the_hole(amend, rules, airline, no_real_llm):
    am = amend.draft(airline, copy.deepcopy(BASE), copy.deepcopy(HOLE), llm=Scripted(answer(FIX_RULE)))
    assert False in run_chain(airline, rules, amend.apply(copy.deepcopy(BASE), am))


def test_REQ_AM1_2_apply_refuses_a_colliding_rule_id(amend):
    base = copy.deepcopy(BASE)
    with pytest.raises(ValueError):
        amend.apply(base, amendment(dict(FIX_RULE, id="R-base-be")))
    assert base == BASE


def test_REQ_AM1_2_patched_hand_ruleset_blocks_the_hole(amend, rules, airline):
    # Also the precondition of the CLI tests: the hand RuleSet leaves this G1 hole open.
    hand = json.loads(HAND.read_text())
    assert run_chain(airline, rules, hand) == [True, True, True], "fixture: the hole runs under the hand RuleSet"
    patched = amend.apply(json.loads(HAND.read_text()), amendment(FIX_RULE))
    assert run_chain(airline, rules, patched) == [True, True, False]


# ---------- REQ-AM1-3 and REQ-BT1-3: the amend CLI ----------

RUNNER = '''
import copy, json, runpy, sys
import bylaw.llm

payload = json.load(open(sys.argv[1]))
log = sys.argv[2]

def fake(messages, schema, name, effort=None, **opts):
    with open(log, "a") as f:
        f.write(json.dumps({"name": name}) + "\\n")
    return copy.deepcopy(payload)

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
    # Blocking every flight update blocks the 13 gold tasks that update flights, on top of what the
    # hand RuleSet already blocks; unknown tasks (no inferable reason) stay unblocked.
    flight_tasks = {"7", "11", "15", "16", "17", "18", "21", "22", "30", "32", "33", "37", "44"}
    base_ids = {r["id"] for r in baseline["results"] if r["blocked"]}
    unknown = {r["id"] for r in baseline["results"] if r["unknown"]}
    b = only_hole(amended_closing)["backtest"]
    expected = (base_ids | flight_tasks) - unknown
    assert set(b["blocked_tasks"]) == expected
    assert len(b["blocked_tasks"]) == b["blocked"] == len(expected)
    assert b["blocked"] - b["baseline_blocked"] == len(flight_tasks - base_ids - unknown)


def test_REQ_BT1_3_blocked_tasks_lists_every_blocked_task(amended_noop, baseline):
    b = only_hole(amended_noop)["backtest"]
    assert set(b["blocked_tasks"]) == {r["id"] for r in baseline["results"] if r["blocked"]}
    assert len(b["blocked_tasks"]) == b["blocked"]
