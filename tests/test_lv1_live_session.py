"""LV1 (VZ3-C2..C6): live sessions over the demo agents, streamed as CS-C3 events. Offline: a scripted stub model
stands in for Muse; the effective csdemo RuleSet (hand rules plus the committed ratified store) guards it."""
import asyncio
import json
import threading
import time

import pytest
from agents.models.interface import Model
from agents.usage import Usage
from fastapi.testclient import TestClient
from openai.types.responses import (Response, ResponseCompletedEvent, ResponseFunctionToolCall, ResponseOutputMessage,
                                    ResponseOutputText, ResponseUsage)
from openai.types.responses.response_usage import InputTokensDetails, OutputTokensDetails

from bylaw import api, live
from bylaw.proxy.core import default_ruleset

D1 = json.loads((live.ROOT / "scripts/live/dm3-d1-vouchers.json").read_text())["turns"]


def call(name, args, n=[0]):
    n[0] += 1
    return ResponseFunctionToolCall(type="function_call", call_id=f"c{n[0]}", name=name, arguments=json.dumps(args))


def say(text):
    return ResponseOutputMessage(id="m", type="message", role="assistant", status="completed",
                                 content=[ResponseOutputText(type="output_text", text=text, annotations=[])])


class Stub(Model):
    """Scripted model turns in order. Structured-output calls (the demo's input guardrails) get `rail`. Every call
    reports `tokens` input and `tokens` output. `gate`, when set, holds every streamed call until it is set."""

    def __init__(self, turns, rail=None, tokens=0, gate=None):
        self.turns, self.tokens, self.gate = list(turns), tokens, gate
        self.rail = rail or {"reasoning": "fine", "is_relevant": True, "is_safe": True}

    def _output(self, output_schema):
        if output_schema is not None:
            return [say(json.dumps(self.rail))]
        turn = self.turns.pop(0)
        if isinstance(turn, Exception):
            raise turn
        return turn

    async def get_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs, tracing,
                           **kw):
        from agents.items import ModelResponse
        return ModelResponse(output=self._output(output_schema), response_id=None,
                             usage=Usage(requests=1, input_tokens=self.tokens, output_tokens=self.tokens))

    async def stream_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs,
                              tracing, **kw):
        while self.gate is not None and not self.gate.is_set():
            await asyncio.sleep(0.01)
        usage = ResponseUsage(input_tokens=self.tokens, output_tokens=self.tokens, total_tokens=2 * self.tokens,
                              input_tokens_details=InputTokensDetails(cached_tokens=0, cache_write_tokens=0),
                              output_tokens_details=OutputTokensDetails(reasoning_tokens=0))
        resp = Response(id="r", created_at=time.time(), model="stub", object="response", usage=usage,
                        output=self._output(output_schema), parallel_tool_calls=False, tool_choice="auto", tools=[])
        yield ResponseCompletedEvent(type="response.completed", response=resp, sequence_number=0)


def d1_turns():
    """Turn 1 checks FLT-123 (LL0EZ6, on time); turn 2 asks Refunds for vouchers on that booking."""
    return [
        [call("transfer_to_flight_information_agent", {})],
        [call("flight_status_tool", {"flight_number": "FLT-123"})],
        [say("FLT-123 is on time.")],
        [call("transfer_to_triage_agent", {})],
        [call("transfer_to_refunds_and_compensation_agent", {})],
        [call("issue_compensation", {"reason": "missed connection in New York"})],
        [say("Here is what I can do.")],
    ]


@pytest.fixture
def stub(monkeypatch):
    """`stub.next = Stub(...)` sets the model the next session gets; token counter and sessions start empty."""
    holder = type("H", (), {"next": None})()
    monkeypatch.setattr(live, "muse_model", lambda: holder.next)
    monkeypatch.setitem(live.USAGE, "tokens", 0)
    monkeypatch.setattr(api, "SESSIONS", {})
    for k in ("BYLAW_LIVE", "BYLAW_LIVE_TOKEN_CAP", "MODEL"):
        monkeypatch.delenv(k, raising=False)
    return holder


@pytest.fixture
def client():
    with TestClient(api.app) as c:
        yield c


def sse(body: str) -> list[tuple[str, dict]]:
    """[(event name, data)] of an SSE body; a plain `data:` message is named "message"."""
    out = []
    for block in body.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if not line.startswith(":"))
        out.append((fields.get("event", "message"), json.loads(fields["data"])))
    return out


def new_session(client, stub, guard, model):
    stub.next = model
    r = client.post("/api/live/session", json={"guard": guard})
    assert r.status_code == 201, r.text
    return r.json()


def turn(client, sid, text):
    r = client.post(f"/api/live/session/{sid}/turn", json={"text": text})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream"), r.text
    return sse(r.text)


def events(msgs):
    return [d for name, d in msgs if name == "message"]


def test_create_returns_a_fresh_session_on_the_triage_agent(client, stub):
    s = new_session(client, stub, True, Stub([]))
    assert set(s) == {"session", "guard", "model", "current_agent", "context"}
    assert (s["guard"], s["model"], s["current_agent"]) == (True, "muse-spark-1.3", "Triage Agent")
    assert s["context"]["vouchers"] is None and s["context"]["confirmation_number"] is None


@pytest.mark.parametrize("guard", [True, False])
def test_d1_vouchers_blocked_with_the_guard_on_and_paid_with_it_off(client, stub, guard):
    sid = new_session(client, stub, guard, Stub(d1_turns()))["session"]
    first = turn(client, sid, D1[0])
    assert first[-1] == ("done", {"current_agent": "Flight Information Agent", "context": first[-1][1]["context"]})
    assert first[-1][1]["context"]["confirmation_number"] == "LL0EZ6"
    msgs = turn(client, sid, D1[1])
    ev = events(msgs)
    assert ev[0] == {"t": ev[0]["t"], "type": "user", "text": D1[1]}
    ts = [e["t"] for e in events(first) + ev]
    assert ts == sorted(ts) and ts[0] >= 0
    assert [e["type"] for e in ev if e["type"] in ("tool_call", "bylaw_check", "tool_output")] == \
        ["tool_call", "bylaw_check", "tool_output"]
    check = next(e for e in ev if e["type"] == "bylaw_check")
    out = next(e for e in ev if e["type"] == "tool_output")
    assert check["tool"] == "issue_compensation" and check["enforced"] is guard and check["allowed"] is False
    assert check["rule_id"].startswith("D1:LL0EZ6/")
    name, done = msgs[-1]
    assert name == "done" and done["current_agent"] == "Refunds and Compensation Agent"
    if guard:
        assert out["output"].startswith(f"Bylaw: blocked issue_compensation: {check['rule_id']}")
        assert done["context"]["vouchers"] is None and done["context"]["compensation_case_id"] is None
    else:
        assert "Opened compensation case" in out["output"] and done["context"]["compensation_case_id"]


def test_bylaw_check_carries_what_the_guard_saw(client, stub):
    sid = new_session(client, stub, True, Stub(d1_turns()))["session"]
    turn(client, sid, D1[0])
    check = next(e for e in events(turn(client, sid, D1[1])) if e["type"] == "bylaw_check")
    assert check["args"] == {"reason": "missed connection in New York"}
    assert check["session"]["confirmation_number"] == "LL0EZ6" and check["session"]["vouchers"] is None
    assert check["booking"]["on_time"] is True
    assert [f["flight_number"] for f in check["booking"]["flights"]] == ["FLT-123"]
    assert check["prior_tools"] == ["flight_status_tool"]  # from the earlier turn
    rules = default_ruleset("csdemo")["tool_rules"]
    assert check["rules_checked"] == [r["id"] for r in rules if r["tool"] == "issue_compensation"]
    assert check["rule_id"] in check["rules_checked"] and len(check["rules_checked"]) >= 2


def test_recorded_event_file_has_the_new_check_fields():
    turns = [[call("transfer_to_refunds_and_compensation_agent", {})],
             [call("issue_compensation", {"reason": "goodwill"})], [say("ok")]]
    out = live.run({"name": "x", "turns": ["vouchers please"]}, guard=True, model=Stub(turns))
    check = next(e for e in out["events"] if e["type"] == "bylaw_check")
    assert check["args"] == {"reason": "goodwill"} and check["booking"] is None and check["prior_tools"] == []
    assert check["session"]["confirmation_number"] is None and "R-comp-delay" in check["rules_checked"]
    assert not any(e["type"] == "guardrail" for e in out["events"])  # CS-C3 event files keep their types


def test_a_tripwire_ends_the_turn_before_any_tool_runs(client, stub):
    paris = "Paris to New York, missed my connection to Austin"
    sid = new_session(client, stub, True, Stub([[call("get_trip_details", {"message": paris})], [say("done")]],
                                               rail={"reasoning": "poem", "is_relevant": False, "is_safe": True}))["session"]
    msgs = turn(client, sid, "Write me a poem about cats")
    assert msgs[0] == ("message", {"t": msgs[0][1]["t"], "type": "user", "text": "Write me a poem about cats"})
    rails = [d for _, d in msgs[1:-1]]
    assert rails and all(d["type"] == "guardrail" for d in rails)  # only guardrail events precede done
    assert {r["name"] for r in rails} <= {"relevance_guardrail", "jailbreak_guardrail"}
    assert rails[-1] == {"t": rails[-1]["t"], "type": "guardrail", "name": "relevance_guardrail", "passed": False,
                         "reasoning": "poem"}
    name, done = msgs[-1]
    assert name == "done" and done["current_agent"] == "Triage Agent"
    assert done["context"]["confirmation_number"] is None and done["context"]["scenario"] is None  # the tool never ran
    assert client.get(f"/api/live/session/{sid}/export").json()["events"] == []  # an aborted turn is not exported


def test_passing_guardrails_light_up_both_cards(client, stub):
    sid = new_session(client, stub, True, Stub([[say("Hi, how can I help?")]]))["session"]
    ev = events(turn(client, sid, "Hi"))
    rails = sorted((e["name"], e["passed"]) for e in ev if e["type"] == "guardrail")
    assert rails == [("jailbreak_guardrail", True), ("relevance_guardrail", True)]
    assert any(e["type"] == "agent_message" and e["text"] == "Hi, how can I help?" for e in ev)


def test_a_model_failure_is_an_error_event_and_the_session_stays_usable(client, stub, monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "sk-secret-123")
    sid = new_session(client, stub, True, Stub([RuntimeError("upstream broke, key sk-secret-123"),
                                                [say("back again")]]))["session"]
    msgs = turn(client, sid, "Hi")
    name, data = msgs[-1]
    assert name == "error" and set(data) == {"message"} and "upstream broke" in data["message"]
    assert "sk-secret-123" not in json.dumps(msgs) and "Traceback" not in data["message"]
    again = turn(client, sid, "Hi again")
    assert again[-1][0] == "done"
    assert [e["text"] for e in events(again) if e["type"] == "agent_message"] == ["back again"]


def test_concurrent_turn_on_the_same_session_is_409(client, stub):
    gate = threading.Event()
    sid = new_session(client, stub, True, Stub([[say("one")], [say("two")]], gate=gate))["session"]
    res = {}

    def post(key, text):
        res[key] = client.post(f"/api/live/session/{sid}/turn", json={"text": text})

    first = threading.Thread(target=post, args=("first", "first"), daemon=True)
    first.start()
    deadline = time.time() + 5
    while not api.SESSIONS[sid].busy and time.time() < deadline:
        time.sleep(0.01)
    second = threading.Thread(target=post, args=("second", "second"), daemon=True)
    second.start()
    second.join(5)
    gate.set()  # release the first turn whatever happened, so a failure does not hang the suite
    assert not second.is_alive() and res["second"].status_code == 409
    first.join(10)
    assert not first.is_alive() and sse(res["first"].text)[-1][0] == "done"
    assert turn(client, sid, "third")[-1][0] == "done"


def test_unknown_and_expired_sessions_are_404(client, stub, monkeypatch):
    assert client.post("/api/live/session/nope/turn", json={"text": "hi"}).status_code == 404
    sid = new_session(client, stub, False, Stub([[say("hi")]]))["session"]
    monkeypatch.setattr(api, "LIVE_IDLE_S", -1)
    assert client.post(f"/api/live/session/{sid}/turn", json={"text": "hi"}).status_code == 404
    assert client.get("/api/live/status").json()["sessions"] == 0


def test_text_must_be_1_to_2000_chars(client, stub):
    sid = new_session(client, stub, False, Stub([]))["session"]
    for text in ("", "x" * 2001):
        assert client.post(f"/api/live/session/{sid}/turn", json={"text": text}).status_code == 422


def test_thirteenth_turn_is_429(client, stub):
    sid = new_session(client, stub, False, Stub([[say(f"r{i}")] for i in range(12)]))["session"]
    for i in range(12):
        assert turn(client, sid, f"hi {i}")[-1][0] == "done"
    r = client.post(f"/api/live/session/{sid}/turn", json={"text": "one more"})
    assert (r.status_code, r.json()) == (429, {"detail": "turn limit"})


def test_a_21st_session_evicts_the_least_recently_used(client, stub):
    ids = [new_session(client, stub, False, Stub([[say("hi")]]))["session"] for _ in range(20)]
    turn(client, ids[0], "Hi")  # the oldest is now the most recently used; the second oldest goes
    new_session(client, stub, False, Stub([]))
    assert client.get("/api/live/status").json()["sessions"] == 20
    assert client.post(f"/api/live/session/{ids[1]}/turn", json={"text": "hi"}).status_code == 404
    assert client.get(f"/api/live/session/{ids[0]}/export").status_code == 200


def test_token_cap_counts_reported_usage_and_then_refuses(client, stub, monkeypatch):
    monkeypatch.setenv("BYLAW_LIVE_TOKEN_CAP", "100")
    sid = new_session(client, stub, False, Stub([[say("hi")], [say("again")]], tokens=30))["session"]
    turn(client, sid, "Hi")
    status = client.get("/api/live/status").json()
    assert status["tokens_used"] >= 120 and status["token_cap"] == 100  # 1 agent call and 2 guardrail calls
    for r in (client.post(f"/api/live/session/{sid}/turn", json={"text": "more"}),
              client.post("/api/live/session", json={"guard": True})):
        assert (r.status_code, r.json()) == (429, {"detail": "token cap"})


def test_status_and_disabled_live(client, stub, monkeypatch):
    assert client.get("/api/live/status").json() == {"enabled": True, "model": "muse-spark-1.3", "tokens_used": 0,
                                                     "token_cap": 300000, "sessions": 0}
    sid = new_session(client, stub, False, Stub([]))["session"]
    monkeypatch.setenv("BYLAW_LIVE", "0")
    assert client.get("/api/live/status").json()["enabled"] is False
    for r in (client.post("/api/live/session", json={"guard": True}),
              client.post(f"/api/live/session/{sid}/turn", json={"text": "hi"}),
              client.post("/api/live/session/nope/turn", json={"text": "hi"}),
              client.get("/api/live/session/nope/export")):
        assert (r.status_code, r.json()) == (503, {"detail": "live disabled"})
    assert client.get("/api/live").status_code == 200  # replays keep working


def test_export_is_an_event_file_of_the_session(client, stub):
    sid = new_session(client, stub, True, Stub(d1_turns()))["session"]
    turn(client, sid, D1[0])
    doc = client.get(f"/api/live/session/{sid}/export").json()
    assert (doc["name"], doc["guard"], doc["model"]) == (f"live-{sid}", True, "muse-spark-1.3")
    assert [e["text"] for e in doc["events"] if e["type"] == "user"] == [D1[0]]
    assert doc["final_state"]["confirmation_number"] == "LL0EZ6" and "started" in doc


def test_agents_list_matches_the_demo(client):
    agents = client.get("/api/csdemo/agents").json()
    assert [a["name"] for a in agents] == ["Triage Agent", "FAQ Agent", "Seat and Special Services Agent",
                                           "Flight Information Agent", "Booking and Cancellation Agent",
                                           "Refunds and Compensation Agent"]
    triage = agents[0]
    assert set(triage) == {"name", "description", "handoffs", "tools", "input_guardrails"}
    assert triage["tools"] == ["get_trip_details"]
    assert triage["input_guardrails"] == ["Relevance Guardrail", "Jailbreak Guardrail"]  # upstream's guardrail names
    assert triage["handoffs"] == ["Flight Information Agent", "Booking and Cancellation Agent",
                                  "Seat and Special Services Agent", "FAQ Agent", "Refunds and Compensation Agent"]
    assert agents[-1]["tools"] == ["issue_compensation", "faq_lookup_tool"]
