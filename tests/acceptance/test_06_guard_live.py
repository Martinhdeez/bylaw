"""Acceptance tests for CS3: the agents guard (CS-C2), the live runner and its event file (CS-C3), the live API.

Written blind from docs/plan/06-showcase/00-plan.md (REQ-CS3-1..3) and contracts.md v1.0 (CS-C0..CS-C3), with
C2 (rules), C4 (diff) and C10 (ratified store, BYLAW_RATIFIED_DIR). Fixture facts come from the vendored demo
(targets/cs_demo/airline: tools.py, demo_data.py, agents.py).

Offline throughout. The guard is driven by the Agents SDK's own `agents.testing.ScriptedModel` over the demo's real
FunctionTools. The live runner is driven through its CLI with MODEL_BASE_URL pointing at a local fake chat
completions server that plays a fixed script; no key, no network beyond 127.0.0.1.
"""
import asyncio
import copy
import importlib
import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from conftest import ROOT, write_ratified

# ---------- demo fixture facts (targets/cs_demo/airline/demo_data.py) ----------
VOUCHERS = [
    "Overnight hotel covered up to $180 near JFK Terminal 5 partner hotel",
    "$60 meal credit for the delay",
    "$40 ground transport credit to the hotel",
]
DEMO_AGENTS = {"Seat and Special Services Agent", "Flight Information Agent", "Booking and Cancellation Agent",
               "Refunds and Compensation Agent", "FAQ Agent", "Triage Agent"}
PARIS = "My trip is Paris to New York to Austin."
ON_TIME = "What is the status of my commuter flight FLT-123?"
COMP_ARGS = {"reason": "Delay causing missed connection"}

# ---------- tiny custom RuleSets (C2) ----------
REF = "Test policy line: compensation only on a disrupted trip."
NO_COMP_ON_TIME = {"id": "T1-comp-disrupted", "tool": "issue_compensation",
                   "allow_if": "db['context']['session'].get('scenario') == 'disrupted'",
                   "policy_ref": REF, "note": ""}
RS_SCENARIO = {"domain": "csdemo", "tool_rules": [NO_COMP_ON_TIME], "forbidden_goals": []}

REF_D4 = "Test policy line: no compensation after the passenger cancels."
NO_COMP_AFTER_CANCEL = {"id": "T2-no-comp-after-cancel", "tool": "issue_compensation",
                        "allow_if": "not any(db['trace'][k]['tool'] == 'cancel_flight' for k in db['trace'])",
                        "policy_ref": REF_D4, "note": ""}
RS_TRACE = {"domain": "csdemo", "tool_rules": [NO_COMP_AFTER_CANCEL], "forbidden_goals": []}

REF_ALL = "Test policy line: no compensation at all."
DENY_COMP = {"id": "T9-no-comp", "tool": "issue_compensation", "allow_if": "False", "policy_ref": REF_ALL, "note": ""}


def blocked(tool, rule_id, policy_ref):
    return f"Bylaw: blocked {tool}: {rule_id} {policy_ref}"


@pytest.fixture
def ratified_dir(tmp_path, monkeypatch):
    d = tmp_path / "ratified"
    d.mkdir()
    monkeypatch.setenv("BYLAW_RATIFIED_DIR", str(d))
    return d


def guard():
    return importlib.import_module("bylaw.proxy.agents_guard")


def demo(name):
    return importlib.import_module(f"targets.cs_demo.airline.{name}")


class Ctx:
    """Run context the demo tools read: `.state` (AirlineAgentContext) and an awaitable `.stream(event)`."""

    def __init__(self):
        self.state = demo("context").AirlineAgentContext()

    async def stream(self, event):
        return None


def fresh_tool(name):
    """A private copy of the demo's FunctionTool, so guards installed by one test never leak into another."""
    t = copy.copy(getattr(demo("tools"), name))
    t.tool_input_guardrails = list(t.tool_input_guardrails or [])
    return t


def run_calls(calls, ruleset=None, log=None, tools=None, install_times=1):
    """One agent with the named demo tools; a scripted model emits `calls` one per turn, then a message.

    Returns (tool outputs in order, the run context, the agent)."""
    from agents import Agent, RunConfig, Runner
    from agents.testing import ScriptedModel, assistant_message, function_call

    names = tools or sorted({c[0] for c in calls})
    steps = [[function_call(tool, args, call_id=f"call-{i}")] for i, (tool, args) in enumerate(calls)]
    model = ScriptedModel([*steps, [assistant_message("done")]])
    agent = Agent(name="Test Agent", instructions="test", model=model, tools=[fresh_tool(n) for n in names])
    for _ in range(install_times):
        guard().install([agent], domain_name="csdemo", ruleset=ruleset, log=log)
    ctx = Ctx()
    result = asyncio.run(Runner.run(agent, "go", context=ctx, run_config=RunConfig(tracing_disabled=True)))
    outputs = [item.output for item in result.new_items if item.type == "tool_call_output_item"]
    return outputs, ctx, agent


def state_after(calls):
    """The demo state after running `calls` directly, with no guard: the expected 'unchanged' state."""
    from agents import Agent, RunConfig, Runner
    from agents.testing import ScriptedModel, assistant_message, function_call

    steps = [[function_call(tool, args, call_id=f"call-{i}")] for i, (tool, args) in enumerate(calls)]
    agent = Agent(name="Plain", instructions="test", model=ScriptedModel([*steps, [assistant_message("done")]]),
                  tools=[fresh_tool(n) for n in sorted({c[0] for c in calls})])
    ctx = Ctx()
    asyncio.run(Runner.run(agent, "go", context=ctx, run_config=RunConfig(tracing_disabled=True)))
    return ctx.state.model_dump(mode="json")


# ---------- REQ-CS3-1 the guard ----------

def test_REQ_CS3_1_forbidden_call_is_not_executed_and_returns_the_reject_text():
    log = []
    outputs, ctx, _ = run_calls([("issue_compensation", COMP_ARGS)], ruleset=RS_SCENARIO, log=log)
    assert outputs == [blocked("issue_compensation", "T1-comp-disrupted", REF)]
    fresh = demo("context").AirlineAgentContext().model_dump(mode="json")
    assert ctx.state.model_dump(mode="json") == fresh  # the tool did not run: no case, no vouchers, no scenario
    assert log == [{"tool": "issue_compensation", "args": COMP_ARGS, "allowed": False,
                    "rule_id": "T1-comp-disrupted", "policy_ref": REF}]


def test_REQ_CS3_1_check_reads_the_live_state_left_by_earlier_tools():
    """get_trip_details on the Paris trip sets scenario 'disrupted': the same rule now allows compensation."""
    log = []
    calls = [("get_trip_details", {"message": PARIS}), ("issue_compensation", COMP_ARGS)]
    outputs, ctx, _ = run_calls(calls, ruleset=RS_SCENARIO, log=log)
    assert outputs[0].startswith("Hydrated disrupted itinerary: flight PA441, confirmation IR-D204")
    assert outputs[1].startswith("Opened compensation case CMP-")
    assert ctx.state.vouchers == VOUCHERS
    assert log[0] == {"tool": "get_trip_details", "args": {"message": PARIS}, "allowed": True,
                      "rule_id": None, "policy_ref": None}  # no rule on that tool
    assert len(log) == 2
    assert {k: log[1][k] for k in ("tool", "args", "allowed")} == {"tool": "issue_compensation", "args": COMP_ARGS,
                                                                  "allowed": True}


def test_REQ_CS3_1_blocked_after_an_allowed_call_leaves_that_calls_state_unchanged():
    """On the on-time trip the rule denies: the state is exactly what get_trip_details alone left."""
    log = []
    calls = [("get_trip_details", {"message": ON_TIME}), ("issue_compensation", COMP_ARGS)]
    outputs, ctx, _ = run_calls(calls, ruleset=RS_SCENARIO, log=log)
    assert outputs[0].startswith("Hydrated on_time itinerary: flight FLT-123, confirmation LL0EZ6")
    assert outputs[1] == blocked("issue_compensation", "T1-comp-disrupted", REF)
    assert ctx.state.model_dump(mode="json") == state_after(calls[:1])
    assert ctx.state.vouchers is None and ctx.state.compensation_case_id is None
    assert [(e["tool"], e["allowed"]) for e in log] == [("get_trip_details", True), ("issue_compensation", False)]


def test_REQ_CS3_1_snapshot_trace_holds_the_guards_earlier_calls():
    """CS-C2: the snapshot's trace is the guard's own trace (CS-C1 shape), so a D4-style chain rule fires."""
    calls = [("get_trip_details", {"message": PARIS}), ("cancel_flight", {}), ("issue_compensation", COMP_ARGS)]
    outputs, ctx, _ = run_calls(calls, ruleset=RS_TRACE, log=[])
    assert outputs[1].startswith("Flight PA441 successfully cancelled for confirmation IR-D204")
    assert outputs[2] == blocked("issue_compensation", "T2-no-comp-after-cancel", REF_D4)
    assert ctx.state.vouchers is None
    # without the cancellation the same rule allows it
    outputs, ctx, _ = run_calls([calls[0], calls[2]], ruleset=RS_TRACE)
    assert outputs[1].startswith("Opened compensation case CMP-") and ctx.state.vouchers == VOUCHERS


def test_REQ_CS3_1_default_ruleset_is_the_effective_one_with_ratified_rules(ratified_dir):
    """ruleset=None: the guard checks default_ruleset('csdemo'), the hand RuleSet plus the ratified store (C10)."""
    write_ratified(ratified_dir, "csdemo", DENY_COMP, goal="D1")
    log = []
    outputs, ctx, _ = run_calls([("get_trip_details", {"message": PARIS}), ("issue_compensation", COMP_ARGS)], log=log)
    assert outputs[1] == blocked("issue_compensation", "T9-no-comp", REF_ALL)
    assert ctx.state.vouchers is None
    assert log[-1] == {"tool": "issue_compensation", "args": COMP_ARGS, "allowed": False,
                       "rule_id": "T9-no-comp", "policy_ref": REF_ALL}


def test_REQ_CS3_1_install_is_idempotent():
    log = []
    outputs, ctx, agent = run_calls([("issue_compensation", COMP_ARGS)], ruleset=RS_SCENARIO, log=log,
                                    tools=["issue_compensation", "get_trip_details"], install_times=2)
    assert outputs == [blocked("issue_compensation", "T1-comp-disrupted", REF)]
    assert len(log) == 1  # one check per call, not one per install
    counts = [len(t.tool_input_guardrails or []) for t in agent.tools]
    guard().install([agent], domain_name="csdemo", ruleset=RS_SCENARIO, log=log)
    assert [len(t.tool_input_guardrails or []) for t in agent.tools] == counts


def test_REQ_CS3_1_install_guards_every_function_tool_of_every_demo_agent():
    from agents import Agent, FunctionTool

    mod = demo("agents")
    originals = [v for v in vars(mod).values() if isinstance(v, Agent)]
    assert {a.name for a in originals} >= DEMO_AGENTS
    agents_ = []
    for a in originals:
        tools = []
        for t in a.tools:
            t = copy.copy(t)
            if isinstance(t, FunctionTool):
                t.tool_input_guardrails = list(t.tool_input_guardrails or [])
            tools.append(t)
        agents_.append(a.clone(tools=tools))
    before = {(a.name, t.name): len(t.tool_input_guardrails or [])
              for a in agents_ for t in a.tools if isinstance(t, FunctionTool)}
    assert len(before) >= 10
    guard().install(agents_, domain_name="csdemo", ruleset=RS_SCENARIO)
    after = {(a.name, t.name): len(t.tool_input_guardrails or [])
             for a in agents_ for t in a.tools if isinstance(t, FunctionTool)}
    assert after == {k: n + 1 for k, n in before.items()}


# ---------- REQ-CS3-2 the live runner (fake chat completions server) ----------

END = None  # plan marker: the model answers with text, ending the turn
MODEL = "fake-muse"
TURNS = [PARIS, "I missed my connection. I need hotel and meal vouchers."]
PLAN = [("get_trip_details", {"message": PARIS}), END,
        ("transfer_to_refunds", {}), ("issue_compensation", COMP_ARGS), END]
TURN_TEXT = "Turn done."


class FakeMuse:
    """OpenAI chat completions on 127.0.0.1. Requests with a response_format (the demo's guardrail agents) get a
    schema-filled answer (booleans true). Agent requests follow PLAN: the next tool call if the agent offers a tool
    whose name starts with it, else a text answer (an END marker is consumed by that answer)."""

    def __init__(self, plan):
        self.plan = list(plan)
        self.requests = []
        self.lock = threading.Lock()
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
                with fake.lock:
                    fake.requests.append(body)
                    msg = fake.answer(body)
                self.reply(body, msg)

            def reply(self, body, msg):
                finish = "tool_calls" if msg.get("tool_calls") else "stop"
                base = {"id": "chatcmpl-fake", "created": 0, "model": body.get("model", MODEL)}
                usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
                if body.get("stream"):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.end_headers()
                    delta = {"role": "assistant", "content": msg.get("content")}
                    if msg.get("tool_calls"):
                        delta["tool_calls"] = [dict(tc, index=i) for i, tc in enumerate(msg["tool_calls"])]
                    chunks = [{"choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
                              {"choices": [{"index": 0, "delta": {}, "finish_reason": finish}]},
                              {"choices": [], "usage": usage}]
                    for c in chunks:
                        data = json.dumps(dict(base, object="chat.completion.chunk", **c))
                        self.wfile.write(f"data: {data}\n\n".encode())
                    self.wfile.write(b"data: [DONE]\n\n")
                    return
                out = json.dumps(dict(base, object="chat.completion", usage=usage,
                                      choices=[{"index": 0, "message": msg, "finish_reason": finish}])).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def answer(self, body):
        fmt = body.get("response_format")
        if fmt:
            props = (fmt.get("json_schema") or {}).get("schema", {}).get("properties", {})
            fill = {k: True if v.get("type") == "boolean" else "ok" for k, v in props.items()}
            return {"role": "assistant", "content": json.dumps(fill)}
        offered = [t["function"]["name"] for t in body.get("tools") or []]
        if self.plan and self.plan[0] is not END:
            want, args = self.plan[0]
            name = next((n for n in offered if n.startswith(want)), None)
            if name:
                self.plan.pop(0)
                return {"role": "assistant", "content": None, "tool_calls": [
                    {"id": f"call-{uuid.uuid4().hex[:8]}", "type": "function",
                     "function": {"name": name, "arguments": json.dumps(args)}}]}
        if self.plan and self.plan[0] is END:
            self.plan.pop(0)
        return {"role": "assistant", "content": TURN_TEXT}

    def close(self):
        self.server.shutdown()


@pytest.fixture
def muse():
    m = FakeMuse(PLAN)
    yield m
    m.close()


def live(tmp_path, muse, ratified_dir, guard_on):
    script = tmp_path / "script.json"
    script.write_text(json.dumps({"name": "t-paris", "turns": TURNS}))
    out = tmp_path / "out.json"
    env = dict(os.environ, MODEL_BASE_URL=muse.url, MODEL=MODEL, MODEL_API_KEY="test-not-a-key",
               OPENAI_BASE_URL=muse.url, OPENAI_API_KEY="test-not-a-key", BYLAW_RATIFIED_DIR=str(ratified_dir))
    env.pop("BASE_URL", None)
    args = [sys.executable, "-m", "bylaw", "live", "--domain", "csdemo", "--script", str(script),
            *(["--guard"] if guard_on else []), "-o", str(out)]
    p = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert p.returncode == 0, p.stdout + p.stderr
    return json.loads(out.read_text())


def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        obj = list(obj.values())
    if isinstance(obj, list):
        for v in obj:
            found = find_key(v, key)
            if found is not None:
                return found
    return None


TYPES = {"user", "agent_message", "handoff", "tool_call", "bylaw_check", "tool_output", "state"}


def assert_event_file(doc, guard_on):
    assert set(doc) >= {"name", "guard", "model", "started", "events", "final_state"}
    assert doc["name"] == "t-paris" and doc["guard"] is guard_on and doc["model"] == MODEL
    datetime.fromisoformat(doc["started"])
    ev = doc["events"]
    assert ev and {e["type"] for e in ev} <= TYPES
    ts = [e["t"] for e in ev]
    assert all(isinstance(t, (int, float)) for t in ts) and ts[0] >= 0 and ts == sorted(ts)
    assert [e["text"] for e in ev if e["type"] == "user"] == TURNS
    for e in ev:
        need = {"handoff": {"from", "to"}, "tool_call": {"agent", "tool", "args"},
                "bylaw_check": {"tool", "allowed", "rule_id", "policy_ref"}, "tool_output": {"tool", "output"},
                "state": {"diff"}, "agent_message": {"agent", "text"}}.get(e["type"], set())
        assert set(e) >= need, e
    calls = [e for e in ev if e["type"] == "tool_call"]
    assert [(e["agent"], e["tool"], e["args"]) for e in calls] == [
        ("Triage Agent", "get_trip_details", {"message": PARIS}),
        ("Refunds and Compensation Agent", "issue_compensation", COMP_ARGS)]
    # every tool call has its bylaw_check, between the call and its output
    flow = [(e["type"], e["tool"]) for e in ev if e["type"] in ("tool_call", "bylaw_check", "tool_output")]
    assert flow == [(k, t) for t in ("get_trip_details", "issue_compensation")
                    for k in ("tool_call", "bylaw_check", "tool_output")]
    assert [(e["from"], e["to"]) for e in ev if e["type"] == "handoff"] == [
        ("Triage Agent", "Refunds and Compensation Agent")]
    msgs = [(e["agent"], e["text"]) for e in ev if e["type"] == "agent_message"]
    assert msgs == [("Triage Agent", TURN_TEXT), ("Refunds and Compensation Agent", TURN_TEXT)]
    first_state = next(e for e in ev if e["type"] == "state")
    assert first_state["diff"]["context"]["session"]["after"]["confirmation_number"] == "IR-D204"
    return {e["tool"]: e for e in ev if e["type"] == "bylaw_check"}, \
        {e["tool"]: e for e in ev if e["type"] == "tool_output"}


def test_REQ_CS3_2_unguarded_event_file_computes_checks_but_does_not_enforce(tmp_path, muse, ratified_dir):
    write_ratified(ratified_dir, "csdemo", DENY_COMP, goal="D1")
    doc = live(tmp_path, muse, ratified_dir, guard_on=False)
    checks, outputs = assert_event_file(doc, guard_on=False)
    assert all(e["enforced"] is False for e in doc["events"] if e["type"] == "bylaw_check")
    assert checks["get_trip_details"]["allowed"] is True
    assert {k: checks["issue_compensation"][k] for k in ("allowed", "rule_id", "policy_ref")} == {
        "allowed": False, "rule_id": "T9-no-comp", "policy_ref": REF_ALL}
    assert outputs["issue_compensation"]["output"].startswith("Opened compensation case CMP-")
    comp_state = [e for e in doc["events"] if e["type"] == "state"][-1]
    assert comp_state["diff"]["context"]["session"]["after"]["vouchers"] == VOUCHERS
    assert find_key(doc["final_state"], "vouchers") == VOUCHERS
    assert muse.requests and {r.get("model") for r in muse.requests} == {MODEL}  # nothing for gpt-* models


def test_REQ_CS3_2_guarded_event_file_blocks_the_forbidden_call(tmp_path, muse, ratified_dir):
    write_ratified(ratified_dir, "csdemo", DENY_COMP, goal="D1")
    doc = live(tmp_path, muse, ratified_dir, guard_on=True)
    checks, outputs = assert_event_file(doc, guard_on=True)
    assert {k: checks["issue_compensation"][k] for k in ("allowed", "rule_id", "policy_ref")} == {
        "allowed": False, "rule_id": "T9-no-comp", "policy_ref": REF_ALL}
    assert outputs["issue_compensation"]["output"] == blocked("issue_compensation", "T9-no-comp", REF_ALL)
    assert find_key(doc["final_state"], "vouchers") is None
    assert find_key(doc["final_state"], "confirmation_number") == "IR-D204"
    assert {r.get("model") for r in muse.requests} == {MODEL}


def test_REQ_CS3_2_d1_script_is_committed():
    s = json.loads((ROOT / "scripts" / "live" / "csdemo-d1.json").read_text())
    assert isinstance(s["name"], str) and s["name"]
    assert len(s["turns"]) == 2 and all(isinstance(t, str) for t in s["turns"])
    assert "FLT-123" in s["turns"][0] and "paris" in s["turns"][1].lower()


@pytest.mark.live
def test_REQ_CS3_2_live_muse_run_of_the_d1_script(tmp_path):
    out = tmp_path / "d1.json"
    p = subprocess.run([sys.executable, "-m", "bylaw", "live", "--domain", "csdemo", "--script",
                        str(ROOT / "scripts" / "live" / "csdemo-d1.json"), "-o", str(out)],
                       cwd=ROOT, capture_output=True, text=True, timeout=900)
    assert p.returncode == 0, p.stdout + p.stderr
    doc = json.loads(out.read_text())
    assert doc["guard"] is False and doc["events"] and {e["type"] for e in doc["events"]} <= TYPES
    ts = [e["t"] for e in doc["events"]]
    assert ts == sorted(ts)
    calls = [e["tool"] for e in doc["events"] if e["type"] == "tool_call"]
    checks = [e for e in doc["events"] if e["type"] == "bylaw_check"]
    assert calls and sorted(calls) == sorted(e["tool"] for e in checks)
    assert all(e["enforced"] is False for e in checks)


# ---------- REQ-CS3-3 the live API ----------

@pytest.fixture
def live_file(monkeypatch):
    """A fixture event file in the real reports/live/ (CS-C3 names that dir), removed afterwards."""
    monkeypatch.delenv("BYLAW_REPORTS_DIR", raising=False)
    d = ROOT / "reports" / "live"
    made = not d.exists()
    d.mkdir(parents=True, exist_ok=True)
    stem = f"zz-acceptance-{uuid.uuid4().hex[:8]}"
    doc = {"name": stem, "guard": True, "model": MODEL, "started": "2026-10-28T00:00:00",
           "events": [{"t": 0.0, "type": "user", "text": "hi"}], "final_state": {}}
    f = d / f"{stem}.json"
    f.write_text(json.dumps(doc))
    other = d / f"{stem}.txt"
    other.write_text("not an event file")
    yield stem, doc
    f.unlink(missing_ok=True)
    other.unlink(missing_ok=True)
    if made and not any(d.iterdir()):
        d.rmdir()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    with TestClient(importlib.import_module("bylaw.api").app) as c:
        yield c


def test_REQ_CS3_3_list_and_get_live_event_files(live_file, client):
    stem, doc = live_file
    r = client.get("/api/live")
    assert r.status_code == 200
    mine = [e for e in r.json() if e["name"] == stem]
    assert len(mine) == 1 and mine[0]["guard"] is True and isinstance(mine[0]["file"], str)
    assert not any(e["file"].endswith(".txt") for e in r.json())
    got = client.get(f"/api/live/{mine[0]['file']}")
    assert got.status_code == 200 and got.json() == doc


def test_REQ_CS3_3_absent_live_file_is_404(live_file, client):
    stem, _ = live_file
    entry = next(e for e in client.get("/api/live").json() if e["name"] == stem)
    assert client.get(f"/api/live/{entry['file']}").status_code == 200  # the route exists; only the name is absent
    assert client.get("/api/live/no-such-run-0000.json").status_code == 404
    assert client.get("/api/live/no-such-run-0000").status_code == 404
