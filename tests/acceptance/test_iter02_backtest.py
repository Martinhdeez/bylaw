"""Acceptance tests for BT1: gold-task loader and backtest (C8).

Written blind from docs/plan/02-amend/requirements.md and contracts.md.
Domain facts come from the τ² airline task file and DB in .context/tau2-bench.
REQ-BT1-3 (baseline in the amended report) is checked in test_iter02_amend.py, through the CLI.

C8 v1.1: `domain` is the C1 Domain object; `step` is the 0-based index into the task's `load_gold`
actions (null when not blocked); `unknown` is a top-level int plus a per-result bool, and an unknown
task is not blocked. Only cancel_reservation needs a conversation fact among the airline gold tools
(the reason), so only the 7 cancel tasks may be unknown.
"""
import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TASKS_FILE = ROOT / ".context" / "tau2-bench" / "data" / "tau2" / "domains" / "airline" / "tasks.json"

# The 43 airline tasks with gold actions (counted from tasks.json: 50 tasks, these have actions).
GOLD_IDS = {
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "11", "12", "13", "14", "15", "16", "17", "18",
    "19", "20", "21", "22", "23", "24", "25", "27", "29", "30", "32", "33", "35", "36", "37", "38",
    "39", "40", "41", "42", "43", "44", "45", "47", "48", "49",
}
NO_GOLD_IDS = {"0", "10", "26", "28", "31", "34", "46"}
CANCEL_TASKS = {"7", "14", "19", "23", "29", "39", "42"}
FLIGHT_UPDATE_TASKS = {"7", "11", "15", "16", "17", "18", "21", "22", "30", "32", "33", "37", "44"}
READ_RES_TASKS = {"1", "2", "3", "4", "6", "7", "8", "12", "29", "30", "32", "33", "36", "37", "38",
                  "39", "40", "41", "42", "43", "44", "45", "47", "48", "49"}


def tau2_gold() -> dict[str, list[tuple[str, dict]]]:
    tasks = json.loads(TASKS_FILE.read_text())
    return {t["id"]: [(a["name"], a["arguments"]) for a in t["evaluation_criteria"]["actions"]]
            for t in tasks if (t.get("evaluation_criteria") or {}).get("actions")}


def ruleset(*rules_):
    return {"domain": "airline",
            "tool_rules": [{"id": rid, "tool": tool, "allow_if": expr, "policy_ref": f"ref {rid}", "note": ""}
                           for rid, tool, expr in rules_],
            "forbidden_goals": []}


@pytest.fixture(scope="module")
def bt():
    return importlib.import_module("bylaw.backtest")


@pytest.fixture(scope="module")
def airline():
    return importlib.import_module("bylaw.domain").get_domain("airline")


@pytest.fixture(scope="module")
def gold(bt, airline):
    return bt.load_gold(airline)


def by_id(result):
    return {r["id"]: r for r in result["results"]}


def unknown_ids(result):
    return {r["id"] for r in result["results"] if r["unknown"] is True}


def assert_totals(result):
    assert result["tasks"] == 43
    assert len(result["results"]) == 43
    assert {r["id"] for r in result["results"]} == GOLD_IDS
    assert result["blocked"] == sum(1 for r in result["results"] if r["blocked"] is True)
    assert all(isinstance(r["unknown"], bool) for r in result["results"])
    assert isinstance(result["unknown"], int) and result["unknown"] == len(unknown_ids(result))
    assert unknown_ids(result) <= CANCEL_TASKS
    for r in result["results"]:
        if r["unknown"]:
            assert r["blocked"] is False, r
        if not r["blocked"]:
            assert r["step"] is None, r


def blocked_ids(result):
    return {r["id"] for r in result["results"] if r["blocked"] is True}


# ---------- REQ-BT1-1 ----------

def test_REQ_BT1_1_load_gold_returns_the_43_airline_tasks_with_gold_actions(gold):
    assert set(tau2_gold()) == GOLD_IDS  # the fixture itself
    assert isinstance(gold, list)
    assert len(gold) == 43
    ids = [t["id"] for t in gold]
    assert all(isinstance(i, str) for i in ids)
    assert len(set(ids)) == 43
    assert set(ids) == GOLD_IDS
    assert not set(ids) & NO_GOLD_IDS


def test_REQ_BT1_1_each_task_has_its_gold_actions_in_order(gold):
    expected = tau2_gold()
    for task in gold:
        acts = task["actions"]
        assert isinstance(acts, list) and acts, task["id"]
        assert [a["tool"] for a in acts] == [name for name, _ in expected[task["id"]]], task["id"]
        for a, (_, args) in zip(acts, expected[task["id"]]):
            assert isinstance(a["args"], dict)
            # Conversation facts (C2 v1.1) may be added as extra keys; the τ² arguments must all be there.
            for k, v in args.items():
                assert a["args"].get(k) == v, (task["id"], a["tool"], k)


def test_REQ_BT1_1_a_long_task_keeps_all_19_actions(gold):
    t44 = next(t for t in gold if t["id"] == "44")
    tools = [a["tool"] for a in t44["actions"]]
    assert len(tools) == 19
    assert tools[:6] == ["get_user_details"] + ["get_reservation_details"] * 5
    assert tools[6:16] == ["search_direct_flight"] * 10
    assert [a["args"]["reservation_id"] for a in t44["actions"][16:]] == ["NM1VX1", "H8Q05L", "KC18K6"]


# ---------- REQ-BT1-2 ----------

def test_REQ_BT1_2_no_rules_blocks_nothing(bt, airline):
    result = bt.backtest(airline, ruleset())
    assert_totals(result)
    assert result["blocked"] == 0
    assert all(r["blocked"] is False for r in result["results"])


def test_REQ_BT1_2_read_actions_are_checked_too(bt, airline):
    result = bt.backtest(airline, ruleset(("T-no-read", "get_reservation_details", "False")))
    assert_totals(result)
    assert blocked_ids(result) == READ_RES_TASKS - unknown_ids(result)
    rows = by_id(result)
    for tid in READ_RES_TASKS - unknown_ids(result):
        assert rows[tid]["rule_id"] == "T-no-read", tid
    for tid in GOLD_IDS - READ_RES_TASKS:
        assert rows[tid]["blocked"] is False, tid


def test_REQ_BT1_2_first_blocking_rule_is_reported(bt, airline):
    rs = ruleset(("T-flights", "update_reservation_flights", "False"),
                 ("T-kc", "get_reservation_details", "args['reservation_id'] != 'KC18K6'"))
    result = bt.backtest(airline, rs)
    assert_totals(result)
    assert blocked_ids(result) == (FLIGHT_UPDATE_TASKS | {"4", "44"}) - unknown_ids(result)
    rows = by_id(result)
    # 4 and 44 read KC18K6 at action 2; 44 updates flights only at action 16.
    assert rows["4"]["rule_id"] == "T-kc"
    assert rows["44"]["rule_id"] == "T-kc"
    for tid in FLIGHT_UPDATE_TASKS - unknown_ids(result) - {"44"}:
        assert rows[tid]["rule_id"] == "T-flights", tid


# update_reservation_flights is allowed only while the reservation still has its τ² DB cabin.
# OWZ4XL basic_economy: task 32 updates it twice -> only the 2nd call sees the 1st one's write.
# FQ8APE basic_economy: tasks 17 and 22 each update it once. M05KNL business: tasks 15 and 16, once each.
CABIN_RULE = ("T-cabin", "update_reservation_flights",
              "res['cabin'] == {'OWZ4XL': 'basic_economy', 'FQ8APE': 'basic_economy', 'M05KNL': 'business'}"
              ".get(args['reservation_id'], res['cabin'])")


def test_REQ_BT1_2_actions_execute_in_order_checked_on_the_snapshot_before_each_call(bt, airline):
    result = bt.backtest(airline, ruleset(CABIN_RULE))
    assert_totals(result)
    # Executed in order: 32's 2nd update sees cabin economy. Snapshot before the call: 32's 1st update,
    # 17 and 22 are allowed.
    assert blocked_ids(result) == {"32"}
    assert by_id(result)["32"]["rule_id"] == "T-cabin"


def test_REQ_BT1_2_each_task_runs_on_a_fresh_env(bt, airline):
    result = bt.backtest(airline, ruleset(CABIN_RULE))
    rows = by_id(result)
    # A shared env would show 16 and 22 the cabin already changed by 15 and 17.
    for tid in ("15", "16", "17", "22"):
        assert rows[tid]["blocked"] is False, tid


def test_REQ_BT1_2_backtest_leaves_a_fresh_env_untouched(bt, airline):
    before = airline.snapshot(airline.fresh_env())
    bt.backtest(airline, ruleset())
    assert airline.snapshot(airline.fresh_env()) == before


def test_REQ_BT1_2_step_is_the_index_of_the_blocking_action(bt, airline):
    result = bt.backtest(airline, ruleset(CABIN_RULE))
    rows = by_id(result)
    assert rows["32"]["step"] == 4
    assert rows["17"]["step"] is None
    result = bt.backtest(airline, ruleset(("T-flights", "update_reservation_flights", "False")))
    assert_totals(result)
    rows = by_id(result)
    assert rows["44"]["step"] == 16
    assert rows["11"]["step"] == 0
    assert rows["30"]["step"] == 2
    assert rows["32"]["step"] == 3
    if not rows["7"]["unknown"]:
        assert rows["7"]["step"] == 2


def test_REQ_BT1_2_unknown_tasks_are_counted_not_blocked(bt, airline):
    # Every cancel task is blocked by this rule unless its reason could not be inferred.
    result = bt.backtest(airline, ruleset(("T-no-cancel", "cancel_reservation", "False")))
    assert_totals(result)
    assert blocked_ids(result) == CANCEL_TASKS - unknown_ids(result)
    assert result["blocked"] + result["unknown"] == 7
