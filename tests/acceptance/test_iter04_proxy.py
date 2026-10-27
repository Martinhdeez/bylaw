"""Acceptance tests for PX1: the enforcement proxy (C11) over the ratified RuleSet (C10).

Written blind from docs/plan/04-proxy/requirements.md and contracts.md (v1.1; monitor per 01 v1.7), with C1, C2, C7, C10.
Fixture facts come from the τ² airline DB and tasks.json in .context/tau2-bench (see conftest for the
G1 cabin hop on T1QOBS). Every test points `BYLAW_RATIFIED_DIR` at its own tmp dir, so the default
RuleSet is the hand RuleSet plus exactly the amendments the test stores.
"""
import asyncio
import importlib
import json
import os
import re
import subprocess
import sys

import pytest

from conftest import (AMEND_RULE, HOP_CHAIN, HOP_KEY, HOP_PAY, HOP_RES, ROOT, load_ruleset,
                      report_fixture, tool_names, write_ratified)

DENY_REF = "Test policy line: no baggage changes."
DENY_BAGS = {"id": "A9-no-bags", "tool": "update_reservation_baggages", "allow_if": "False",
             "policy_ref": DENY_REF, "note": ""}
# Hand rules allow this on T1QOBS (0 bags, basic economy): adding one paid bag with a profile card.
ADD_BAG = {"reservation_id": HOP_RES, "total_baggages": 1, "nonfree_baggages": 1, "payment_id": HOP_PAY}
# Gold tasks with update_reservation_baggages (tasks.json): 12, 17, 21, 22, 33.
GOLD_BAG_TASKS = 5
# A ratified rule that allows everything: ratifying it on a G1 hole only switches the G1 monitor on.
NOOP_G1 = {"id": "A0-noop", "tool": "send_certificate", "allow_if": "True", "policy_ref": "noop", "note": ""}
CLASS_A_GOALS = ["G1", "G2", "G3", "G4", "G5", "G6"]
LINE = re.compile(r"^(\d+) (ALLOWED|BLOCKED) (\S+)(?: (.*))?$")  # 04 v1.1: <n> ALLOWED|BLOCKED <tool>[ <reason>]


@pytest.fixture
def ratified_dir(tmp_path, monkeypatch):
    d = tmp_path / "ratified"
    d.mkdir()
    monkeypatch.setenv("BYLAW_RATIFIED_DIR", str(d))
    return d


@pytest.fixture(scope="module")
def airline():
    return importlib.import_module("bylaw.domain").get_domain("airline")


def Proxy(*a, **k):
    return importlib.import_module("bylaw.proxy.core").Proxy(*a, **k)


def res(snap):
    return snap["reservations"][HOP_RES]


def assert_result_shape(out):
    assert set(out) >= {"ok", "blocked", "reason", "rule_id", "goal", "result"}
    assert isinstance(out["ok"], bool) and isinstance(out["blocked"], bool)


def cli(*args, ratified_dir, timeout=600):
    env = dict(os.environ, BYLAW_RATIFIED_DIR=str(ratified_dir))
    env.pop("MODEL_API_KEY", None)
    return subprocess.run([sys.executable, "-m", "bylaw", *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=timeout)


def step_lines(stdout):
    """(status, tool, reason) per step, after checking n runs 0, 1, 2, ..."""
    found = [m for m in (LINE.match(line.strip()) for line in stdout.splitlines()) if m]
    assert [int(m.group(1)) for m in found] == list(range(len(found))), stdout
    return [(m.group(2), m.group(3), m.group(4) or "") for m in found]


def last_line(stdout):
    return [line.strip() for line in stdout.splitlines() if line.strip()][-1]


# ---------- REQ-PX1-1 (Proxy.tools and the MCP server) ----------

def test_REQ_PX1_1_proxy_exposes_every_tau2_tool_with_its_schema(airline, ratified_dir):
    tools = Proxy(airline).tools()
    assert {t["name"] for t in tools} == tool_names(airline)
    by_name = {t["name"]: t for t in tools}
    for spec in airline.tools:
        fn = spec.get("function", spec)
        assert by_name[fn["name"]]["input_schema"] == fn["parameters"], fn["name"]
        assert isinstance(by_name[fn["name"]]["description"], str)


async def _mcp_session(ratified_dir, body):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable, args=["-m", "bylaw", "proxy", "--domain", "airline"], cwd=str(ROOT),
        env=dict(os.environ, BYLAW_RATIFIED_DIR=str(ratified_dir)))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await body(session)


def mcp_run(ratified_dir, body):
    return asyncio.run(asyncio.wait_for(_mcp_session(ratified_dir, body), timeout=180))


def text_of(result):
    return "".join(c.text for c in result.content if getattr(c, "type", None) == "text")


def test_REQ_PX1_1_mcp_server_lists_every_tool_with_its_schema(airline, ratified_dir):
    async def body(session):
        return (await session.list_tools()).tools

    tools = mcp_run(ratified_dir, body)
    assert {t.name for t in tools} == tool_names(airline)
    by_name = {t.name: t for t in tools}
    for spec in airline.tools:
        fn = spec.get("function", spec)
        assert by_name[fn["name"]].input_schema == fn["parameters"], fn["name"]  # mcp 2.x field name


# ---------- REQ-PX1-2 ----------

def test_REQ_PX1_2_rule_deny_is_blocked_with_rule_id_and_db_unchanged(airline, ratified_dir):
    ruleset = {"domain": "airline", "forbidden_goals": [], "tool_rules": [DENY_BAGS]}
    p = Proxy(airline, ruleset=ruleset)
    before = p.snapshot()
    assert before == airline.snapshot(airline.fresh_env())
    out = p.call("update_reservation_baggages", dict(ADD_BAG))
    assert_result_shape(out)
    assert out["blocked"] is True and out["ok"] is False
    assert out["rule_id"] == "A9-no-bags" and out["goal"] is None
    assert out["reason"] == f"BLOCKED A9-no-bags: {DENY_REF}"
    assert p.snapshot() == before


def test_REQ_PX1_2_hand_rule_of_the_default_ruleset_denies(airline, ratified_dir):
    # T1QOBS was booked 2024-05-09 (> 24 h before now), basic economy, no insurance:
    # a change-of-plan cancel is refused by R-cancel-ground alone.
    p = Proxy(airline)
    before = p.snapshot()
    out = p.call("cancel_reservation", {"reservation_id": HOP_RES, "reason": "change of plan"})
    assert out["blocked"] is True and out["ok"] is False and out["rule_id"] == "R-cancel-ground"
    ground = next(r for r in load_ruleset("airline")["tool_rules"] if r["id"] == "R-cancel-ground")
    assert out["reason"] == f"BLOCKED R-cancel-ground: {ground['policy_ref']}"
    assert p.snapshot() == before
    assert res(p.snapshot())["status"] != "cancelled"


def test_REQ_PX1_2_default_ruleset_enforces_ratified_amendments(airline, ratified_dir):
    p = Proxy(airline)
    out = p.call("update_reservation_baggages", dict(ADD_BAG))
    assert out["blocked"] is False and out["ok"] is True  # hand rules allow it
    write_ratified(ratified_dir, "airline", DENY_BAGS)
    p = Proxy(airline)
    before = p.snapshot()
    out = p.call("update_reservation_baggages", dict(ADD_BAG))
    assert out["blocked"] is True and out["rule_id"] == "A9-no-bags"
    assert p.snapshot() == before


def test_REQ_PX1_2_allowed_write_is_applied_and_facts_are_stripped(airline, ratified_dir):
    # `reason` is a conversation fact, not a τ² argument: the rule reads it, the tool never sees it.
    ruleset = {"domain": "airline", "forbidden_goals": [], "tool_rules": [
        {"id": "T-reason", "tool": "cancel_reservation", "allow_if": "args.get('reason') == 'change of plan'",
         "policy_ref": "ref", "note": ""}]}
    p = Proxy(airline, ruleset=ruleset, monitor=False)
    out = p.call("cancel_reservation", {"reservation_id": HOP_RES, "reason": "change of plan"})
    assert_result_shape(out)
    assert out["ok"] is True and out["blocked"] is False and out["rule_id"] is None
    assert res(p.snapshot())["status"] == "cancelled"
    out = Proxy(airline, ruleset=ruleset, monitor=False).call("cancel_reservation", {"reservation_id": HOP_RES})
    assert out["blocked"] is True and out["rule_id"] == "T-reason"


def test_REQ_PX1_2_each_proxy_is_a_fresh_session(airline, ratified_dir):
    p = Proxy(airline, monitor=False)
    p.call("update_reservation_baggages", dict(ADD_BAG))
    assert res(p.snapshot())["total_baggages"] == 1
    assert res(Proxy(airline).snapshot())["total_baggages"] == 0


def test_REQ_PX1_2_mcp_blocked_call_names_rule_and_policy_line(ratified_dir):
    write_ratified(ratified_dir, "airline", DENY_BAGS)

    async def body(session):
        before = text_of(await session.call_tool("get_reservation_details", {"reservation_id": HOP_RES}))
        blocked = text_of(await session.call_tool("update_reservation_baggages", dict(ADD_BAG)))
        after = text_of(await session.call_tool("get_reservation_details", {"reservation_id": HOP_RES}))
        return before, blocked, after

    before, blocked, after = mcp_run(ratified_dir, body)
    assert blocked == f"BLOCKED A9-no-bags: {DENY_REF}", blocked
    assert HOP_RES in before
    assert after == before


# ---------- REQ-PX1-3 ----------

def test_REQ_PX1_3_fixture_every_hop_step_is_allowed_and_reaches_G1(airline, ratified_dir):
    # Without the monitor the hand RuleSet lets the whole hop through and G1 is reached.
    p = Proxy(airline, ruleset=load_ruleset("airline"), monitor=False)
    start = p.snapshot()
    for step in HOP_CHAIN:
        out = p.call(step["tool"], dict(step["args"]))
        assert out["ok"] is True and out["blocked"] is False, out
    end = res(p.snapshot())
    assert res(start)["cabin"] == "basic_economy"
    assert [(f["flight_number"], f["date"]) for f in end["flights"]] == [("HAT060", "2024-05-18")]


def test_REQ_PX1_3_goal_monitor_blocks_the_hop_from_session_start(airline, ratified_dir):
    p = Proxy(airline, ruleset=load_ruleset("airline"), monitor_goals=["G1"])
    first = p.call(HOP_CHAIN[0]["tool"], dict(HOP_CHAIN[0]["args"]))
    assert first["ok"] is True and first["blocked"] is False  # the cabin upgrade alone is no goal
    after_first = p.snapshot()
    assert res(after_first)["cabin"] == "economy"
    out = p.call(HOP_CHAIN[1]["tool"], dict(HOP_CHAIN[1]["args"]))
    assert_result_shape(out)
    assert out["blocked"] is True and out["ok"] is False
    assert out["goal"] == "G1" and out["rule_id"] is None
    assert out["reason"].startswith("BLOCKED G1: ")
    assert p.snapshot() == after_first  # not applied
    assert [(f["flight_number"], f["date"]) for f in res(p.snapshot())["flights"]] == [("HAT060", "2024-05-26")]


def test_REQ_PX1_3_monitor_does_not_block_a_write_that_reaches_no_goal(airline, ratified_dir):
    p = Proxy(airline, ruleset=load_ruleset("airline"), monitor_goals=CLASS_A_GOALS)
    out = p.call("update_reservation_baggages", dict(ADD_BAG))
    assert out["ok"] is True and out["blocked"] is False and out["goal"] is None


def run_hop(p):
    return [p.call(s["tool"], dict(s["args"])) for s in HOP_CHAIN]


def test_REQ_PX1_3_with_nothing_ratified_the_default_monitor_blocks_nothing(airline, ratified_dir):
    # 01 v1.7: monitor_goals=None means the goals of ratified amendments; there are none.
    outs = run_hop(Proxy(airline))
    assert [(o["ok"], o["blocked"]) for o in outs] == [(True, False), (True, False)], outs


def test_REQ_PX1_3_monitor_only_enforces_the_listed_goals(airline, ratified_dir):
    outs = run_hop(Proxy(airline, monitor_goals=["G2", "G5"]))
    assert [o["blocked"] for o in outs] == [False, False], outs


def test_REQ_PX1_3_default_monitor_enforces_the_goal_of_a_ratified_amendment(airline, ratified_dir):
    write_ratified(ratified_dir, "airline", NOOP_G1, goal="G1")
    first, second = run_hop(Proxy(airline))
    assert first["blocked"] is False
    assert second["blocked"] is True and second["goal"] == "G1" and second["rule_id"] is None


def ratify_on(ratified_dir, hole_key):
    (ratified_dir / "airline.json").write_text(json.dumps({"domain": "airline", "amendments": [
        {"id": "A1", "hole_key": hole_key, "policy_text": "t.", "rule_patch": [NOOP_G1], "rationale": "",
         "ratified_at": "2026-10-27T00:00:00+00:00"}]}))


def test_REQ_GA1_3_ratified_goal_is_the_hole_key_prefix(airline, ratified_dir):
    ratify_on(ratified_dir, "G1:T1QOBS")
    assert [o["blocked"] for o in run_hop(Proxy(airline))] == [False, True]
    assert run_hop(Proxy(airline))[1]["goal"] == "G1"


def test_REQ_GA1_3_another_goal_prefix_does_not_monitor_G1(airline, ratified_dir):
    ratify_on(ratified_dir, "G2:T1QOBS")  # same target, other goal: G1 stays unmonitored
    assert [o["blocked"] for o in run_hop(Proxy(airline))] == [False, False]


def test_REQ_PX1_3_monitor_off_ignores_ratified_goals(airline, ratified_dir):
    write_ratified(ratified_dir, "airline", NOOP_G1, goal="G1")
    assert [o["blocked"] for o in run_hop(Proxy(airline, monitor=False))] == [False, False]


def test_REQ_PX1_3_mcp_goal_block_names_the_goal(ratified_dir):
    write_ratified(ratified_dir, "airline", NOOP_G1, goal="G1")

    async def body(session):
        texts = [text_of(await session.call_tool(s["tool"], dict(s["args"]))) for s in HOP_CHAIN]
        texts.append(text_of(await session.call_tool("get_reservation_details", {"reservation_id": HOP_RES})))
        return texts

    first, second, details = mcp_run(ratified_dir, body)
    assert not first.startswith("BLOCKED"), first
    assert second.startswith("BLOCKED G1: "), second
    assert "2024-05-26" in details and "2024-05-18" not in details


# ---------- REQ-PX1-4 ----------

@pytest.fixture
def report_path(tmp_path):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report_fixture()))
    return path


def test_REQ_PX1_4_replay_hole_prints_one_line_per_step_and_nothing_ratified_blocks_nothing(
        report_path, ratified_dir):
    r = cli("replay", "--domain", "airline", "--hole", HOP_KEY, "--report", str(report_path),
            ratified_dir=ratified_dir)
    assert r.returncode == 0, r.stderr
    lines = step_lines(r.stdout)
    assert [tool for _, tool, _ in lines] == [s["tool"] for s in HOP_CHAIN], r.stdout
    assert [status for status, _, _ in lines] == ["ALLOWED", "ALLOWED"], r.stdout


def test_REQ_PX1_4_replay_hole_with_ratified_goal_is_blocked_at_the_goal_step(report_path, ratified_dir):
    write_ratified(ratified_dir, "airline", NOOP_G1, goal="G1")
    r = cli("replay", "--domain", "airline", "--hole", HOP_KEY, "--report", str(report_path),
            ratified_dir=ratified_dir)
    assert r.returncode == 0, r.stderr
    lines = step_lines(r.stdout)
    assert [tool for _, tool, _ in lines] == [s["tool"] for s in HOP_CHAIN], r.stdout
    assert [status for status, _, _ in lines] == ["ALLOWED", "BLOCKED"], r.stdout
    assert lines[1][2].startswith("BLOCKED G1: "), r.stdout


def test_REQ_PX1_4_replay_with_ratified_amendment_blocks_before_the_goal_step(report_path, ratified_dir):
    write_ratified(ratified_dir, "airline", AMEND_RULE, goal="G1")
    r = cli("replay", "--domain", "airline", "--hole", HOP_KEY, "--report", str(report_path),
            ratified_dir=ratified_dir)
    assert r.returncode == 0, r.stderr
    lines = step_lines(r.stdout)
    assert len(lines) == len(HOP_CHAIN), r.stdout
    # The amendment refuses the cabin upgrade itself: step 0, before the goal step.
    # Only the ratified rule can refuse step 0: the hand rules allow it and no goal is true yet.
    assert lines[0][0] == "BLOCKED", r.stdout
    assert lines[0][2] == f"BLOCKED {AMEND_RULE['id']}: {AMEND_RULE['policy_ref']}", r.stdout


def test_REQ_PX1_4_replay_gold_blocks_none_of_43(ratified_dir):
    r = cli("replay", "--domain", "airline", "--gold", ratified_dir=ratified_dir)
    assert r.returncode == 0, r.stderr
    assert last_line(r.stdout) == "blocked: 0/43", r.stdout


def test_REQ_PX1_4_replay_gold_counts_tasks_a_ratified_rule_blocks(ratified_dir):
    write_ratified(ratified_dir, "airline", DENY_BAGS)
    r = cli("replay", "--domain", "airline", "--gold", ratified_dir=ratified_dir)
    assert r.returncode == 0, r.stderr
    assert last_line(r.stdout) == f"blocked: {GOLD_BAG_TASKS}/43", r.stdout


def test_REQ_PX1_4_replay_gold_with_a_ratified_G1_goal_blocks_task_32_only(ratified_dir):
    # 01 v1.7: gold task 32 (upgrade basic economy, then change flights) is the only gold task reaching G1.
    write_ratified(ratified_dir, "airline", NOOP_G1, goal="G1")
    r = cli("replay", "--domain", "airline", "--gold", ratified_dir=ratified_dir)
    assert r.returncode == 0, r.stderr
    assert last_line(r.stdout) == "blocked: 1/43", r.stdout
