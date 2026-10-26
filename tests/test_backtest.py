from bylaw.backtest import load_gold


def test_airline_gold_tasks_are_the_43_with_actions_in_order():
    gold = load_gold("airline")
    assert len(gold) == 43
    task1 = next(t for t in gold if t["id"] == "1")
    assert task1["actions"] == [
        {"tool": "get_user_details", "args": {"user_id": "raj_sanchez_7340"}},
        {"tool": "get_reservation_details", "args": {"reservation_id": "Q69X3R"}},
    ]


def test_retail_gold_tasks_are_the_112_with_actions():
    assert len(load_gold("retail")) == 112


def _facts(task_id):
    return next(t for t in load_gold("airline") if t["id"] == task_id)["facts"]


def test_cancel_reason_inferred_from_the_user_scenario():
    assert _facts("19")["reason"] == "other"  # "cancel the trip using the travel insurance as you feel unwell"
    assert _facts("7")["reason"] == "other"  # "You are sick."
    assert _facts("14")["reason"] == "change of plan"  # "cancel the current one and book a new one"


def test_cancel_reason_is_none_when_the_scenario_gives_no_reason():
    assert _facts("39")["reason"] is None  # gives up the seat; no policy reason stated


def test_airline_cancelled_flight_reason():
    from bylaw.backtest import infer_reason

    assert infer_reason("Your flight was cancelled and you want a refund.") == "airline cancelled flight"
    assert infer_reason("You just want to cancel.") is None


# --- backtest against a minimal fake domain (C1 surface) ---
from dataclasses import dataclass

import pytest

from bylaw import backtest as bt


@dataclass
class _Step:
    tool: str
    args: dict
    ok: bool = True
    output: object = None
    error: str | None = None


class _Counter:
    """A domain whose only DB value is a counter that `inc` raises."""

    name = "fake"
    now = "2024-05-15T15:00:00"

    def fresh_env(self):
        return {"count": 0}

    def call(self, env, tool, **args):
        if tool == "inc":
            env["count"] += 1
        return _Step(tool, args)

    def snapshot(self, env):
        return dict(env)


RULES = {"domain": "fake", "tool_rules": [
    {"id": "R-once", "tool": "inc", "allow_if": "db['count'] < 1", "policy_ref": "inc at most once", "note": ""},
    {"id": "R-why", "tool": "cancel_reservation", "allow_if": "args.get('reason') == 'change of plan'", "policy_ref": "", "note": ""},
], "forbidden_goals": []}


@pytest.fixture(autouse=True)
def _c2_rules(monkeypatch):
    """Until EN1's C2 `rules.check` lands, stand in for it with plain eval of the same expressions."""
    from bylaw import rules

    if hasattr(rules, "RULESET_SCHEMA"):
        return

    @dataclass
    class Verdict:
        rule_id: str
        ok: bool
        policy_ref: str
        error: str | None = None

    def check(ruleset, snapshot, tool, args, now):
        return [Verdict(r["id"], bool(eval(r["allow_if"], {}, {"args": args, "db": snapshot, "now": now})), r["policy_ref"])
                for r in ruleset["tool_rules"] if r["tool"] == tool]

    monkeypatch.setattr(bt, "rules", type("C2", (), {"check": staticmethod(check),
                                                     "allowed": staticmethod(lambda vs: all(v.ok for v in vs))}))


def _gold(monkeypatch, tasks):
    monkeypatch.setattr(bt, "load_gold", lambda domain: tasks)


def _by_id(result):
    return {r["id"]: r for r in result["results"]}


def test_second_inc_is_blocked_by_the_snapshot_before_the_call(monkeypatch):
    _gold(monkeypatch, [{"id": "t", "actions": [{"tool": "inc", "args": {}}, {"tool": "inc", "args": {}}], "facts": {}}])
    r = bt.backtest(_Counter(), RULES)
    assert (r["tasks"], r["blocked"]) == (1, 1)
    assert _by_id(r)["t"] == {"id": "t", "blocked": True, "rule_id": "R-once", "step": 1, "unknown": False}


def test_each_task_starts_from_a_fresh_env(monkeypatch):
    one = {"actions": [{"tool": "inc", "args": {}}], "facts": {}}
    _gold(monkeypatch, [{"id": "a", **one}, {"id": "b", **one}])
    r = bt.backtest(_Counter(), RULES)
    assert r["blocked"] == 0
    assert not any(x["blocked"] for x in r["results"])


def test_inferred_reason_reaches_the_rule_and_missing_reason_is_unknown(monkeypatch):
    cancel = [{"tool": "cancel_reservation", "args": {"reservation_id": "X"}}]
    _gold(monkeypatch, [
        {"id": "plan", "actions": cancel, "facts": {"reason": "change of plan"}},
        {"id": "sick", "actions": cancel, "facts": {"reason": "other"}},
        {"id": "nobody-knows", "actions": cancel, "facts": {"reason": None}},
    ])
    r = bt.backtest(_Counter(), RULES)
    res = _by_id(r)
    assert not res["plan"]["blocked"]
    assert res["sick"]["blocked"] and res["sick"]["rule_id"] == "R-why"
    assert res["nobody-knows"]["unknown"] and not res["nobody-knows"]["blocked"]
    assert (r["tasks"], r["blocked"], r["unknown"]) == (3, 1, 1)


def test_a_block_before_the_unknown_fact_still_counts_as_blocked(monkeypatch):
    _gold(monkeypatch, [{"id": "t", "facts": {"reason": None}, "actions": [
        {"tool": "inc", "args": {}}, {"tool": "inc", "args": {}}, {"tool": "cancel_reservation", "args": {}}]}])
    res = _by_id(bt.backtest(_Counter(), RULES))["t"]
    assert res["blocked"] and not res["unknown"] and res["step"] == 1
