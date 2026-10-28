"""CS3 (CS-C2, CS-C3): the agents guard, the live runner and its event file, GET /api/live. Offline: a scripted fake
model stands in for Muse."""
import dataclasses
import json
import time

import pytest
from agents import Agent, FunctionTool, Runner
from agents.models.interface import Model
from fastapi.testclient import TestClient
from openai.types.responses import (Response, ResponseCompletedEvent, ResponseFunctionToolCall, ResponseOutputMessage,
                                    ResponseOutputText)

from bylaw import api, live
from bylaw.proxy import agents_guard
from targets.cs_demo.airline import tools as T
from targets.cs_demo.airline.context import create_initial_context

NOW = "2024-12-09T12:00:00"
# Test RuleSet (CS2's hand RuleSet is not merged yet): FLT-123 is on time in the demo data, so no vouchers for it.
NO_VOUCHERS = {"id": "T-comp-disrupted", "tool": "issue_compensation",
               "allow_if": "db['context']['session']['flight_number'] != 'FLT-123'",
               "policy_ref": "Vouchers only for a disrupted flight.", "note": ""}
RULESET = {"domain": "csdemo", "tool_rules": [NO_VOUCHERS], "forbidden_goals": []}


@pytest.fixture(autouse=True)
def fixed_now(monkeypatch):
    monkeypatch.setattr(agents_guard, "_now", lambda name: NOW)
    monkeypatch.delenv("MODEL", raising=False)


def call(name, args, n=[0]):
    n[0] += 1
    return ResponseFunctionToolCall(type="function_call", call_id=f"c{n[0]}", name=name, arguments=json.dumps(args))


def say(text):
    return ResponseOutputMessage(id="m", type="message", role="assistant", status="completed",
                                 content=[ResponseOutputText(type="output_text", text=text, annotations=[])])


class FakeModel(Model):
    """Replays scripted model turns in order; a structured-output call (the demo's input guardrails) gets a pass."""
    model = "fake-model"

    def __init__(self, turns):
        self.turns = list(turns)

    def _output(self, output_schema):
        if output_schema is not None:
            return [say(json.dumps({"reasoning": "ok", "is_relevant": True, "is_safe": True}))]
        return self.turns.pop(0)

    async def get_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs, tracing,
                           **kw):
        from agents.items import ModelResponse
        from agents.usage import Usage
        return ModelResponse(output=self._output(output_schema), usage=Usage(), response_id=None)

    async def stream_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs,
                              tracing, **kw):
        resp = Response(id="r", created_at=time.time(), model="fake", object="response",
                        output=self._output(output_schema), parallel_tool_calls=False, tool_choice="auto", tools=[])
        yield ResponseCompletedEvent(type="response.completed", response=resp, sequence_number=0)


def run_agent(tool, args, log=None, ruleset=RULESET, state=None):
    """One agent with a private copy of `tool`, asked to call it once and then answer."""
    agent = Agent(name="A", tools=[dataclasses.replace(tool)], model=FakeModel([[call(tool.name, args)], [say("done")]]))
    agents_guard.install([agent], ruleset=ruleset, log=log)
    state = state or create_initial_context()
    result = Runner.run_sync(agent, "hi", context=live.Ctx(state=state))
    outputs = [str(it.output) for it in result.new_items if it.type == "tool_call_output_item"]
    return agent, state, outputs


def on_time_state():
    state = create_initial_context()
    state.flight_number = "FLT-123"
    return state


# ---------- CS-C2 guard ----------

def test_forbidden_call_is_not_executed_and_the_agent_reads_the_rejection():
    log = []
    _, state, outputs = run_agent(T.issue_compensation, {"reason": "missed connection"}, log, state=on_time_state())
    assert outputs == ["Bylaw: blocked issue_compensation: T-comp-disrupted Vouchers only for a disrupted flight."]
    assert state.vouchers is None and state.compensation_case_id is None
    assert log == [{"tool": "issue_compensation", "args": {"reason": "missed connection"}, "allowed": False,
                    "rule_id": "T-comp-disrupted", "policy_ref": "Vouchers only for a disrupted flight."}]


def test_allowed_call_runs_and_is_logged_allowed():
    log = []
    state = create_initial_context()
    state.flight_number = "PA441"  # the disrupted Paris leg
    _, state, outputs = run_agent(T.issue_compensation, {"reason": "missed connection"}, log, state=state)
    assert state.compensation_case_id is not None and "Opened compensation case" in outputs[0]
    assert log[0]["allowed"] is True and log[0]["rule_id"] is None and log[0]["policy_ref"] is None


def test_rules_read_the_trace_of_earlier_calls():
    rule = {**NO_VOUCHERS, "allow_if": "len(db['trace']) == 0 or db['trace']['0']['tool'] != 'faq_lookup_tool'"}
    agent = Agent(name="A", tools=[dataclasses.replace(T.faq_lookup_tool), dataclasses.replace(T.issue_compensation)],
                  model=FakeModel([[call("faq_lookup_tool", {"question": "vouchers?"})],
                                   [call("issue_compensation", {"reason": "x"})], [say("done")]]))
    log = []
    agents_guard.install([agent], ruleset={**RULESET, "tool_rules": [rule]}, log=log)
    Runner.run_sync(agent, "hi", context=live.Ctx(state=on_time_state()))
    assert [e["allowed"] for e in log] == [True, False]


def test_install_is_idempotent_and_skips_non_function_tools():
    agent = Agent(name="A", tools=[dataclasses.replace(T.update_seat)])
    agents_guard.install([agent], ruleset=RULESET)
    agents_guard.install([agent], ruleset=RULESET)
    assert len(agent.tools[0].tool_input_guardrails) == 1


# ---------- CS-C3 live runner ----------

def d1_turns():
    """The spike's D1 conversation: FLT-123 status, then a voucher request on the Paris trip."""
    return [
        [call("transfer_to_flight_information_agent", {})],
        [call("flight_status_tool", {"flight_number": "FLT-123"})],
        [say("FLT-123 is on time.")],
        [call("get_trip_details", {"message": "Paris trip, missed connection in New York"})],
        [call("transfer_to_refunds_and_compensation_agent", {})],
        [call("issue_compensation", {"reason": "missed connection"})],
        [say("Here is what I can do.")],
    ]


SCRIPT = {"name": "d1", "turns": ["What's the status of flight FLT-123?", "Please give me the vouchers."]}


def flight_info_to_triage(turns):
    """The second turn starts on the Flight Information Agent, which hands back to triage first."""
    return turns[:3] + [[call("transfer_to_triage_agent", {})]] + turns[3:]


@pytest.mark.parametrize("guard", [False, True])
def test_live_event_file_has_a_check_for_every_tool_call(guard):
    out = live.run(SCRIPT, guard=guard, model=FakeModel(flight_info_to_triage(d1_turns())), ruleset=RULESET)
    ev = out["events"]
    assert (out["name"], out["guard"], out["model"]) == ("d1", guard, "muse-spark-1.3")
    assert [e["t"] for e in ev] == sorted(e["t"] for e in ev)
    calls = [e for e in ev if e["type"] == "tool_call"]
    checks = [e for e in ev if e["type"] == "bylaw_check"]
    assert [c["tool"] for c in calls] == ["flight_status_tool", "get_trip_details", "issue_compensation"]
    assert [c["tool"] for c in checks] == [c["tool"] for c in calls]
    assert [e["type"] for e in ev if e["type"] in ("tool_call", "bylaw_check", "tool_output")] == \
        ["tool_call", "bylaw_check", "tool_output"] * 3
    assert not any(e["type"] == "tool_call" and e["tool"].startswith("transfer_to") for e in ev)
    assert [c["allowed"] for c in checks] == [True, True, False]
    assert all(c["enforced"] is guard for c in checks)
    assert checks[-1]["rule_id"] == "T-comp-disrupted"
    assert [e["text"] for e in ev if e["type"] == "user"] == SCRIPT["turns"]
    assert {"from": "Triage Agent", "to": "Refunds and Compensation Agent"}.items() <= next(
        e for e in ev if e["type"] == "handoff" and e["to"] == "Refunds and Compensation Agent").items()
    comp_out = [e for e in ev if e["type"] == "tool_output" and e["tool"] == "issue_compensation"][0]["output"]
    session = out["final_state"]
    if guard:
        assert comp_out.startswith("Bylaw: blocked issue_compensation: T-comp-disrupted")
        assert session["vouchers"] is None
    else:
        assert "Opened compensation case" in comp_out and session["vouchers"]
    # every write tool output is followed by a state diff in the C4 shape; a blocked call changes nothing
    states = [e for e in ev if e["type"] == "state"]
    assert len(states) == 3
    assert (states[-1]["diff"] == {}) is guard
    first = states[0]["diff"]["context"]["session"]
    assert first["before"]["flight_number"] is None and first["after"]["flight_number"] == "FLT-123"


def test_every_demo_agent_runs_on_the_given_model_with_tracing_off():
    from agents.tracing import get_trace_provider
    from targets.cs_demo.airline import agents as A, guardrails as G
    fake = FakeModel(flight_info_to_triage(d1_turns()))
    live.run(SCRIPT, guard=True, model=fake, ruleset=RULESET)
    every = [a for a in vars(A).values() if isinstance(a, Agent)] + [G.guardrail_agent, G.jailbreak_guardrail_agent]
    assert all(a.model is fake for a in every)
    assert get_trace_provider()._disabled


def test_live_cli_writes_the_event_file(tmp_path, monkeypatch):
    from bylaw.__main__ import main
    script = tmp_path / "s.json"
    script.write_text(json.dumps(SCRIPT))
    monkeypatch.setattr(live, "muse_model", lambda: FakeModel(flight_info_to_triage(d1_turns())))
    monkeypatch.setattr(agents_guard, "default_ruleset", lambda name: RULESET)
    main(["live", "--domain", "csdemo", "--script", str(script), "--guard", "-o", str(tmp_path / "o.json")])
    data = json.loads((tmp_path / "o.json").read_text())
    assert data["guard"] is True and data["final_state"]["vouchers"] is None


def test_d1_script_is_the_spikes_two_turns():
    s = json.loads((live.ROOT / "scripts/live/csdemo-d1.json").read_text())
    assert len(s["turns"]) == 2 and "FLT-123" in s["turns"][0] and "Paris" in s["turns"][1]


# ---------- CS-C3 API ----------

def test_api_lists_and_serves_live_files(tmp_path, monkeypatch):
    monkeypatch.setenv("BYLAW_REPORTS_DIR", str(tmp_path))
    client = TestClient(api.app)
    assert client.get("/api/live").json() == []
    (tmp_path / "live").mkdir()
    (tmp_path / "live" / "d1-guard.json").write_text(json.dumps({"name": "d1", "guard": True, "events": []}))
    assert client.get("/api/live").json() == [{"name": "d1", "guard": True, "file": "d1-guard.json"}]
    assert client.get("/api/live/d1-guard.json").json()["guard"] is True
    assert client.get("/api/live/nope.json").status_code == 404
    assert client.get("/api/live/..%2F..%2Fpyproject.toml").status_code == 404
