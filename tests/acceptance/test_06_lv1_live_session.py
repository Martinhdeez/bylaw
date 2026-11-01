"""Acceptance tests for LV1: the live session backend (VZ3-C2..C6), written blind.

Sources: docs/plan/06-showcase/vz3-contract.md v1.0 (C2-C6) and contracts.md v1.5 (CS-C1..C3). Fixture facts come
from the vendored demo (targets/cs_demo/airline) and the repo's ratified/csdemo.json (the effective RuleSet).

Offline. Each test starts its own `uvicorn bylaw.api:app` subprocess, so process-wide state (the token counter, the
session table, BYLAW_LIVE, BYLAW_LIVE_TOKEN_CAP) never leaks between tests and the env is in place whenever the
implementation reads it. The model is a local fake chat completions server on 127.0.0.1 reached through
MODEL_BASE_URL (the CS-C3 client settings), as test_06_guard_live.py does for the CLI; no key, no network.
Assumption (no seam named by the contract): the live session reads MODEL_BASE_URL/MODEL the same way `bylaw live` does.
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from conftest import ROOT

MODEL = "fake-muse"
SECRET = "sk-lv1-acceptance-SECRET-0001"
END = None  # plan marker: the model answers with text, ending the turn
TEXT = "Turn done."
ON_TIME = "What is the status of my commuter flight FLT-123?"
VOUCHER_ASK = "I need hotel and meal vouchers for the delay."
COMP_ARGS = {"reason": "Delay causing missed connection"}
D1_PLAN = [("get_trip_details", {"message": ON_TIME}), END,
           ("transfer_to_refunds", {}), ("issue_compensation", COMP_ARGS), END]
D1_RULE = "D1:LL0EZ6/R-comp-booking-disrupted"
D1_REF = ("Compensation and disruption vouchers may only be issued on the booking on record when that booking itself "
          "is disrupted; a disrupted session itinerary or scenario alone does not qualify an on-time booking for "
          "compensation.")
COMP_RULES = ["R-comp-delay", D1_RULE, "D4:IR-D204/R-comp-no-self-cancel"]  # hand rules, then ratified, in order
LL0EZ6_FLIGHTS = [{"flight_number": "FLT-123", "status": "On time and operating as scheduled", "on_time": True}]
FRESH = {k: None for k in ("passenger_name", "confirmation_number", "seat_number", "flight_number", "account_number",
                           "itinerary", "baggage_claim_id", "compensation_case_id", "scenario", "vouchers",
                           "special_service_note", "origin", "destination")}
DEMO_AGENTS = {"Seat and Special Services Agent", "Flight Information Agent", "Booking and Cancellation Agent",
               "Refunds and Compensation Agent", "FAQ Agent", "Triage Agent"}
TYPES = {"user", "agent_message", "handoff", "tool_call", "bylaw_check", "tool_output", "state", "guardrail"}


class FakeMuse:
    """Chat completions on 127.0.0.1. Guardrail requests (response_format) get a schema-filled answer: booleans
    from `bools` (default true), strings "ok". Agent requests follow `plan` like test_06_guard_live.FakeMuse.
    `fail` answers every request with a 400 whose message echoes the Authorization header. `hold` blocks requests
    until `release` is set, signalling `entered`. Every answer reports usage 1 + 1 tokens."""

    def __init__(self):
        self.plan, self.bools, self.fail, self.hold = [], {}, False, False
        self.requests, self.lock = [], threading.Lock()
        self.entered, self.release = threading.Event(), threading.Event()
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def send(self, code, obj, ctype="application/json"):
                out = json.dumps(obj).encode() if not isinstance(obj, bytes) else obj
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
                if fake.hold:
                    fake.entered.set()
                    fake.release.wait(30)
                with fake.lock:
                    fake.requests.append(body)
                    if fake.fail:
                        auth = self.headers.get("Authorization", "")
                        return self.send(400, {"error": {"message": f"bad request for {auth}", "type": "invalid"}})
                    msg = fake.answer(body)
                finish = "tool_calls" if msg.get("tool_calls") else "stop"
                base = {"id": "chatcmpl-fake", "created": 0, "model": body.get("model", MODEL)}
                usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
                if not body.get("stream"):
                    return self.send(200, dict(base, object="chat.completion", usage=usage,
                                               choices=[{"index": 0, "message": msg, "finish_reason": finish}]))
                delta = {"role": "assistant", "content": msg.get("content")}
                if msg.get("tool_calls"):
                    delta["tool_calls"] = [dict(tc, index=i) for i, tc in enumerate(msg["tool_calls"])]
                chunks = [{"choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
                          {"choices": [{"index": 0, "delta": {}, "finish_reason": finish}]},
                          {"choices": [], "usage": usage}]
                data = "".join(f"data: {json.dumps(dict(base, object='chat.completion.chunk', **c))}\n\n"
                               for c in chunks) + "data: [DONE]\n\n"
                self.send(200, data.encode(), "text/event-stream")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def answer(self, body):
        fmt = body.get("response_format")
        if fmt:
            props = (fmt.get("json_schema") or {}).get("schema", {}).get("properties", {})
            fill = {k: self.bools.get(k, True) if v.get("type") == "boolean" else "ok" for k, v in props.items()}
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
        return {"role": "assistant", "content": TEXT}


@pytest.fixture
def muse():
    m = FakeMuse()
    yield m
    m.release.set()
    m.server.shutdown()


@pytest.fixture
def start(tmp_path, muse):
    """start(**env) -> an httpx client on a fresh bylaw.api server wired to the fake model."""
    procs, clients = [], []
    reports = tmp_path / "reports"
    (reports / "live").mkdir(parents=True)

    def _start(**extra):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        env = dict(os.environ, MODEL_BASE_URL=muse.url, MODEL=MODEL, MODEL_API_KEY=SECRET, OPENAI_BASE_URL=muse.url,
                   OPENAI_API_KEY=SECRET, BYLAW_REPORTS_DIR=str(reports), BYLAW_NO_CACHE="1")
        for k in ("BASE_URL", "BYLAW_LIVE", "BYLAW_LIVE_TOKEN_CAP", "BYLAW_RATIFIED_DIR"):
            env.pop(k, None)
        env.update(extra)
        log = open(tmp_path / f"server-{port}.log", "w")
        p = subprocess.Popen([sys.executable, "-m", "uvicorn", "bylaw.api:app", "--host", "127.0.0.1",
                              "--port", str(port), "--log-level", "warning"], cwd=ROOT, env=env,
                             stdout=log, stderr=subprocess.STDOUT)
        procs.append(p)
        c = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=120)
        clients.append(c)
        for _ in range(240):
            try:
                c.get("/api/domains")
                return c
            except httpx.TransportError:
                assert p.poll() is None, (tmp_path / f"server-{port}.log").read_text()
                time.sleep(0.25)
        raise AssertionError("server did not start")

    _start.reports = reports
    yield _start
    for c in clients:
        c.close()
    for p in procs:
        p.terminate()
        p.wait(10)


def parse_sse(text):
    """-> (CS-C3 events from unnamed messages, [(event name, data)] for named ones), in order."""
    events, named = [], []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        name, data = None, []
        for line in block.split("\n"):
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].lstrip())
        if not data:
            continue
        obj = json.loads("\n".join(data))
        if name is None:
            events.append(obj)
        else:
            named.append((name, obj))
    return events, named


def new_session(c, guard):
    r = c.post("/api/live/session", json={"guard": guard})
    assert r.status_code == 201, r.text
    return r.json()


def turn(c, sid, text):
    r = c.post(f"/api/live/session/{sid}/turn", json={"text": text})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream")
    return parse_sse(r.text)


def done_of(named):
    assert [n for n, _ in named] == ["done"], named
    return named[0][1]


def one(events, type_, tool):
    found = [e for e in events if e["type"] == type_ and e.get("tool") == tool]
    assert len(found) == 1, (type_, tool, events)
    return found[0]


def run_d1(c, muse, guard):
    muse.plan = list(D1_PLAN)
    s = new_session(c, guard)
    ev1, n1 = turn(c, s["session"], ON_TIME)
    ev2, n2 = turn(c, s["session"], VOUCHER_ASK)
    return s, ev1 + ev2, done_of(n1), done_of(n2)


# ---------- VZ3-C2 live session ----------

@pytest.mark.parametrize("guard", [True, False])
def test_REQ_VZ3_C2_create_session_returns_201_with_fresh_state(start, guard):
    c = start()
    s = new_session(c, guard)
    assert set(s) >= {"session", "guard", "model", "current_agent", "context"}
    assert isinstance(s["session"], str) and s["session"]
    assert s["guard"] is guard and s["model"] == MODEL and s["current_agent"] == "Triage Agent"
    assert s["context"] == FRESH


def test_REQ_VZ3_C2_turn_streams_cs_c3_events_then_done_and_keeps_state_between_turns(start, muse):
    c = start()
    s, ev, d1, d2 = run_d1(c, muse, guard=True)
    assert ev and {e["type"] for e in ev} <= TYPES
    ts = [e["t"] for e in ev]
    assert all(isinstance(t, (int, float)) for t in ts) and ts[0] >= 0 and ts == sorted(ts)  # from session start
    flow = [(e["type"], e["tool"]) for e in ev if e["type"] in ("tool_call", "bylaw_check", "tool_output")]
    assert flow == [(k, t) for t in ("get_trip_details", "issue_compensation")
                    for k in ("tool_call", "bylaw_check", "tool_output")]
    calls = [(e["agent"], e["tool"], e["args"]) for e in ev if e["type"] == "tool_call"]
    assert calls == [("Triage Agent", "get_trip_details", {"message": ON_TIME}),
                     ("Refunds and Compensation Agent", "issue_compensation", COMP_ARGS)]
    assert [(e["from"], e["to"]) for e in ev if e["type"] == "handoff"] == [
        ("Triage Agent", "Refunds and Compensation Agent")]
    # turn 1 left the Triage agent current with the LL0EZ6 trip loaded; turn 2 started from there
    assert d1["current_agent"] == "Triage Agent"
    assert d1["context"]["confirmation_number"] == "LL0EZ6" and d1["context"]["flight_number"] == "FLT-123"
    assert d2["current_agent"] == "Refunds and Compensation Agent"
    assert d2["context"]["confirmation_number"] == "LL0EZ6"
    # a third turn continues with the Refunds agent (current agent and input kept)
    ev3, n3 = turn(c, s["session"], "Thanks.")
    assert done_of(n3)["current_agent"] == "Refunds and Compensation Agent"
    assert [e["agent"] for e in ev3 if e["type"] == "agent_message"] == ["Refunds and Compensation Agent"]
    assert min(e["t"] for e in ev3) >= max(ts)


def test_REQ_VZ3_C2_guard_on_blocks_d1_compensation_on_LL0EZ6(start, muse):
    c = start()
    _, ev, _, done = run_d1(c, muse, guard=True)
    check = one(ev, "bylaw_check", "issue_compensation")
    assert {k: check[k] for k in ("allowed", "enforced", "rule_id", "policy_ref")} == {
        "allowed": False, "enforced": True, "rule_id": D1_RULE, "policy_ref": D1_REF}
    assert one(ev, "tool_output", "issue_compensation")["output"] == \
        f"Bylaw: blocked issue_compensation: {D1_RULE} {D1_REF}"
    assert done["context"]["vouchers"] is None and done["context"]["compensation_case_id"] is None
    assert all(e["enforced"] is True for e in ev if e["type"] == "bylaw_check")


def test_REQ_VZ3_C2_guard_off_lets_d1_compensation_run_unenforced(start, muse):
    c = start()
    _, ev, _, done = run_d1(c, muse, guard=False)
    check = one(ev, "bylaw_check", "issue_compensation")
    assert {k: check[k] for k in ("allowed", "enforced", "rule_id")} == {
        "allowed": False, "enforced": False, "rule_id": D1_RULE}  # computed, not enforced
    assert one(ev, "tool_output", "issue_compensation")["output"].startswith("Opened compensation case CMP-")
    assert done["context"]["compensation_case_id"].startswith("CMP-")
    assert done["context"]["vouchers"] == []  # the on-time itinerary carries no vouchers
    assert all(e["enforced"] is False for e in ev if e["type"] == "bylaw_check")


def test_REQ_VZ3_C2_model_failure_is_an_error_event_without_key_or_trace_and_session_survives(start, muse):
    c = start()
    s = new_session(c, True)
    muse.fail = True
    ev, named = turn(c, s["session"], ON_TIME)
    assert [n for n, _ in named] == ["error"], named  # no done after the error
    msg = named[0][1]["message"]
    assert isinstance(msg, str) and msg
    assert SECRET not in msg and "Traceback" not in msg and 'File "' not in msg
    muse.fail = False
    _, named = turn(c, s["session"], ON_TIME)
    assert done_of(named)["current_agent"] == "Triage Agent"


def test_REQ_VZ3_C2_concurrent_turn_is_409(start, muse):
    c = start()
    sid = new_session(c, True)["session"]
    muse.hold = True
    first = {}
    t = threading.Thread(target=lambda: first.update(r=c.post(f"/api/live/session/{sid}/turn", json={"text": "Hi"})))
    t.start()
    assert muse.entered.wait(60), "the first turn never reached the model"
    assert c.post(f"/api/live/session/{sid}/turn", json={"text": "Hi again"}).status_code == 409
    muse.hold = False
    muse.release.set()
    t.join(120)
    assert first["r"].status_code == 200 and done_of(parse_sse(first["r"].text)[1])
    _, named = turn(c, sid, "Still there?")  # the lock is released after the turn
    done_of(named)


def test_REQ_VZ3_C2_unknown_session_is_404(start):
    c = start()
    assert c.post("/api/live/session/no-such-session/turn", json={"text": "Hi"}).status_code == 404


def test_REQ_VZ3_C2_text_must_be_1_to_2000_chars(start):
    c = start()
    sid = new_session(c, True)["session"]
    for body in ({"text": ""}, {"text": "x" * 2001}, {}):
        code = c.post(f"/api/live/session/{sid}/turn", json=body).status_code
        assert 400 <= code < 500 and code not in (404, 409, 429), (body, code)  # contract names no code; 422 expected
    _, named = turn(c, sid, "x" * 2000)
    done_of(named)
    _, named = turn(c, sid, "x")
    done_of(named)


# ---------- VZ3-C3 extra bylaw_check fields ----------

@pytest.mark.parametrize("guard", [True, False])
def test_REQ_VZ3_C3_bylaw_check_carries_args_session_booking_prior_tools_rules(start, muse, guard):
    c = start()
    _, ev, _, _ = run_d1(c, muse, guard=guard)
    trip = one(ev, "bylaw_check", "get_trip_details")
    assert trip["args"] == {"message": ON_TIME}
    assert trip["session"]["confirmation_number"] is None  # before the call: the fresh session
    assert trip["booking"] is None  # no booking record for a missing confirmation
    assert trip["prior_tools"] == []
    assert trip["rules_checked"] == ["R-trip-message"]
    comp = one(ev, "bylaw_check", "issue_compensation")
    assert comp["args"] == COMP_ARGS
    assert {k: comp["session"][k] for k in ("passenger_name", "confirmation_number", "flight_number")} == {
        "passenger_name": "Taylor Lee", "confirmation_number": "LL0EZ6", "flight_number": "FLT-123"}
    assert comp["session"]["vouchers"] is None
    assert comp["booking"]["on_time"] is True and comp["booking"]["flights"] == LL0EZ6_FLIGHTS
    assert comp["prior_tools"] == ["get_trip_details"]  # the handoff is not a tool
    assert comp["rules_checked"] == COMP_RULES


def test_REQ_VZ3_C3_old_event_file_without_new_fields_still_loads(start):
    """Regression guard: this already holds today (C1 unchanged)."""
    c = start()
    doc = {"name": "old-run", "guard": True, "model": MODEL, "started": "2026-10-28T00:00:00",
           "events": [{"t": 0.0, "type": "tool_call", "agent": "Triage Agent", "tool": "issue_compensation",
                       "args": COMP_ARGS},
                      {"t": 0.1, "type": "bylaw_check", "tool": "issue_compensation", "allowed": False,
                       "enforced": True, "rule_id": D1_RULE, "policy_ref": D1_REF}],
           "final_state": FRESH}
    (start.reports / "live" / "old-run.json").write_text(json.dumps(doc))
    assert {"name": "old-run", "guard": True, "file": "old-run.json"} in c.get("/api/live").json()
    r = c.get("/api/live/old-run.json")
    assert r.status_code == 200 and r.json() == doc


# ---------- VZ3-C4 demo guardrails ----------

def test_REQ_VZ3_C4_guardrail_events_on_a_passing_turn(start):
    c = start()
    sid = new_session(c, True)["session"]
    ev, named = turn(c, sid, "Hi, I have a question about my flight.")
    g = [e for e in ev if e["type"] == "guardrail"]
    assert sorted(e["name"] for e in g) == ["jailbreak_guardrail", "relevance_guardrail"]
    assert all(e["passed"] is True and e["reasoning"] == "ok" and isinstance(e["t"], (int, float)) for e in g)
    done_of(named)


def test_REQ_VZ3_C4_tripwire_ends_the_turn_then_done(start, muse):
    c = start()
    sid = new_session(c, True)["session"]
    muse.bools = {"is_relevant": False}
    muse.plan = [("get_trip_details", {"message": ON_TIME}), END]
    ev, named = turn(c, sid, "Write me a poem about cheese.")
    failed = [i for i, e in enumerate(ev) if e["type"] == "guardrail" and e["passed"] is False]
    assert [ev[i]["name"] for i in failed] == ["relevance_guardrail"]
    assert ev[failed[0]]["reasoning"] == "ok"
    assert all(e["type"] == "guardrail" for e in ev[failed[0] + 1:]), ev  # nothing of the turn after the tripwire
    assert not any(e["type"] in ("agent_message", "handoff") for e in ev)
    done = done_of(named)
    assert done["current_agent"] == "Triage Agent"


# ---------- VZ3-C5 agents list ----------

def test_REQ_VZ3_C5_agents_list_shape(start):
    from agents import Agent

    mod = __import__("targets.cs_demo.airline.agents", fromlist=["x"])
    demo = {a.name: a for a in vars(mod).values() if isinstance(a, Agent) and a.name in DEMO_AGENTS}
    c = start()
    r = c.get("/api/csdemo/agents")
    assert r.status_code == 200
    got = r.json()
    assert isinstance(got, list) and {a["name"] for a in got} == DEMO_AGENTS and len(got) == len(DEMO_AGENTS)
    for a in got:
        assert set(a) >= {"name", "description", "handoffs", "tools", "input_guardrails"}
        src = demo[a["name"]]
        assert a["description"] == src.handoff_description
        assert a["tools"] == [t.name for t in src.tools]
        assert a["handoffs"] == [getattr(h, "agent_name", None) or h.name for h in src.handoffs]
        assert a["input_guardrails"] == [g.get_name() for g in src.input_guardrails]


# ---------- VZ3-C6 limits ----------

def test_REQ_VZ3_C6_thirteenth_turn_is_429_turn_limit(start):
    c = start()
    sid = new_session(c, True)["session"]
    for i in range(12):
        _, named = turn(c, sid, f"Question {i + 1}")
        done_of(named)
    r = c.post(f"/api/live/session/{sid}/turn", json={"text": "Question 13"})
    assert r.status_code == 429 and r.json() == {"detail": "turn limit"}


def test_REQ_VZ3_C6_token_cap_refuses_turns_and_sessions(start, muse):
    c = start(BYLAW_LIVE_TOKEN_CAP="2")
    sid = new_session(c, True)["session"]
    r = c.post(f"/api/live/session/{sid}/turn", json={"text": "Hi"})  # every fake answer reports 2 tokens
    assert r.status_code == 200
    for r in (c.post(f"/api/live/session/{sid}/turn", json={"text": "Hi again"}),
              c.post("/api/live/session", json={"guard": True})):
        assert r.status_code == 429 and r.json() == {"detail": "token cap"}
    st = c.get("/api/live/status").json()
    assert st["token_cap"] == 2 and st["tokens_used"] == 2 * len(muse.requests)


def test_REQ_VZ3_C6_live_disabled_is_503_and_replays_still_work(start):
    c = start(BYLAW_LIVE="0")
    r = c.post("/api/live/session", json={"guard": True})
    assert r.status_code == 503 and r.json() == {"detail": "live disabled"}
    st = c.get("/api/live/status")
    assert st.status_code == 200 and st.json()["enabled"] is False
    doc = {"name": "replay", "guard": False, "model": MODEL, "started": "2026-10-28T00:00:00",
           "events": [{"t": 0.0, "type": "user", "text": "hi"}], "final_state": {}}
    (start.reports / "live" / "replay.json").write_text(json.dumps(doc))
    assert {"name": "replay", "guard": False, "file": "replay.json"} in c.get("/api/live").json()
    assert c.get("/api/live/replay.json").json() == doc


def test_REQ_VZ3_C6_status_fields(start, muse):
    c = start()
    r = c.get("/api/live/status")
    assert r.status_code == 200
    assert r.json() == {"enabled": True, "model": MODEL, "tokens_used": 0, "token_cap": 300000, "sessions": 0}
    sid = new_session(c, True)["session"]
    new_session(c, False)
    _, named = turn(c, sid, "Hi")
    done_of(named)
    st = c.get("/api/live/status").json()
    assert st["sessions"] == 2 and muse.requests and st["tokens_used"] == 2 * len(muse.requests)


def test_REQ_VZ3_C2_domains_list_is_unchanged(start):
    """Regression guard: csdemo is served by the live endpoints, not added to /api/domains."""
    assert start().get("/api/domains").json() == ["airline", "retail"]
