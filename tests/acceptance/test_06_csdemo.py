"""Acceptance tests for CS2: the `csdemo` domain over the vendored airline customer-service demo.

Written blind from docs/plan/06-showcase/00-plan.md (REQ-CS2-1..4) and contracts.md v1.5 (CS-C0, CS-C1, v1.1, v1.3 rule 3, v1.4, v1.5),
with C1/C2/C4/C8 from docs/plan/01-engine and 02-amend. Fixture values come from the demo source at
upstream commit bd7bfca (airline/demo_data.py, tools.py, agents.py):

- "disrupted" itinerary: Morgan Lee, confirmation IR-D204, seat 14C, PA441 CDG->JFK (delayed 5 hours),
  NY802 JFK->AUS (connection missed); three vouchers (hotel, meal, ground).
  get_trip_details hydrates it when the message names Paris, New York or Austin.
- "on_time" itinerary: Taylor Lee, confirmation LL0EZ6, seat 23A, FLT-123 SFO->LAX "On time".
- apply_itinerary_defaults only fills missing fields, so hydrating on_time first and then disrupted
  leaves flight FLT-123 and confirmation LL0EZ6 under the disrupted scenario: issue_compensation
  then attaches the disrupted vouchers to an on-time booking (D1, the spike's two turns).
- v1.4: D1 is judged at the moment of payment: the session just before the issue_compensation step
  that set the vouchers. Its confirmation_number's fixture itinerary must be all on time; a confirmation
  with no fixture itinerary falls back to that session's flight_number. Writes after the payment do not
  change D1. flight_status_tool overwrites flight_number and leaves the confirmation. Key D1:<conf at payment>.
- Function tools attached to at least one agent: the ten below; baggage_tool is defined but attached
  to no agent.
"""
import importlib
import json
import re
import subprocess
import sys
from datetime import datetime

import pytest

from conftest import ROOT, assert_c2_shape, load_ruleset, tool_names

pytestmark = pytest.mark.skipif(not (ROOT / "targets" / "cs_demo").exists(),
                                reason="targets/cs_demo (VN1 vendored demo) is absent")

PARIS = "I was flying Paris to New York to Austin and missed my connection"
ON_TIME_MSG = "What is the status of my flight FLT-123?"

AGENTS = ["Seat and Special Services Agent", "Flight Information Agent", "Booking and Cancellation Agent",
          "Refunds and Compensation Agent", "FAQ Agent", "Triage Agent"]
ATTACHED_TOOLS = {"update_seat", "assign_special_service_seat", "display_seat_map", "flight_status_tool",
                  "get_matching_flights", "cancel_flight", "book_new_flight", "issue_compensation",
                  "faq_lookup_tool", "get_trip_details"}
WRITE_TOOLS = {"update_seat", "book_new_flight", "assign_special_service_seat", "issue_compensation",
               "cancel_flight", "get_trip_details", "flight_status_tool", "get_matching_flights"}
GOALS = {"D1", "D2", "D3", "D4"}

SESSION_FIELDS = ["passenger_name", "confirmation_number", "seat_number", "flight_number", "account_number",
                  "itinerary", "baggage_claim_id", "compensation_case_id", "scenario", "vouchers",
                  "special_service_note", "origin", "destination"]
FRESH_SESSION = dict.fromkeys(SESSION_FIELDS)
DISRUPTED_SEGMENTS = [
    {"flight_number": "PA441", "origin": "Paris (CDG)", "destination": "New York (JFK)",
     "departure": "2024-12-09 14:10", "arrival": "2024-12-09 17:40",
     "status": "Delayed 5 hours due to weather, expected departure 19:55", "gate": "B18"},
    {"flight_number": "NY802", "origin": "New York (JFK)", "destination": "Austin (AUS)",
     "departure": "2024-12-09 19:10", "arrival": "2024-12-09 22:35",
     "status": "Connection missed because of first leg delay", "gate": "C7"},
]
DISRUPTED_SESSION = dict(FRESH_SESSION, passenger_name="Morgan Lee", confirmation_number="IR-D204",
                         seat_number="14C", flight_number="PA441", itinerary=DISRUPTED_SEGMENTS,
                         scenario="disrupted", origin="Paris (CDG)", destination="Austin (AUS)")
DISRUPTED_VOUCHERS = ["Overnight hotel covered up to $180 near JFK Terminal 5 partner hotel",
                      "$60 meal credit for the delay", "$40 ground transport credit to the hotel"]
# v1.5: the airline's record, one booking per fixture itinerary, flights from its segments.
FACTS = {"bookings": {
    "IR-D204": {"flights": [{"flight_number": seg["flight_number"], "status": seg["status"], "on_time": False}
                            for seg in DISRUPTED_SEGMENTS], "on_time": False},
    "LL0EZ6": {"flights": [{"flight_number": "FLT-123", "status": "On time and operating as scheduled",
                            "on_time": True}], "on_time": True},
}}


@pytest.fixture(scope="module")
def domain():
    return importlib.import_module("bylaw.domain").get_domain("csdemo")


def session(domain, env):
    return domain.snapshot(env)["context"]["session"]


def run(domain, steps):
    """Run (tool, args) steps on a fresh env; return (before, after, chain of StepResults)."""
    env = domain.fresh_env()
    before = domain.snapshot(env)
    chain = [domain.call(env, tool, **args) for tool, args in steps]
    return before, domain.snapshot(env), chain


def reached(domain, goal_id, steps):
    before, after, chain = run(domain, steps)
    assert all(r.ok for r in chain), [(r.tool, r.error) for r in chain]
    return domain.goals[goal_id].check(before, after, chain)


def cli(*argv, timeout=1800):
    return subprocess.run([sys.executable, "-m", "bylaw", *argv], cwd=ROOT,
                          capture_output=True, text=True, timeout=timeout)


# ---------- REQ-CS2-1: get_domain("csdemo") per CS-C1 ----------

def test_REQ_CS2_1_csdemo_is_registered_to_its_plugin_module():
    assert importlib.import_module("bylaw.domain").MODULES["csdemo"] == "bylaw.env.cs_demo"


def test_REQ_CS2_1_name_now_and_goals(domain):
    assert domain.name == "csdemo"
    assert isinstance(domain.now, str)
    datetime.fromisoformat(domain.now.replace("Z", "+00:00"))
    assert importlib.import_module("bylaw.domain").get_domain("csdemo").now == domain.now
    assert set(domain.goals) == GOALS
    for gid, g in domain.goals.items():
        assert g.id == gid and g.cls == "A"
        assert isinstance(g.policy_ref, str) and g.policy_ref
        assert callable(g.check)


def test_REQ_CS2_1_tools_are_the_function_schemas_of_every_attached_tool(domain):
    for t in domain.tools:
        assert t["type"] == "function"
        fn = t["function"]
        assert isinstance(fn["name"], str) and isinstance(fn["description"], str)
        assert isinstance(fn["parameters"], dict)
    assert tool_names(domain) == ATTACHED_TOOLS  # baggage_tool is attached to no agent
    assert len(domain.tools) == len(ATTACHED_TOOLS)


def test_REQ_CS2_1_tool_parameters_omit_the_run_context(domain):
    params = {t["function"]["name"]: t["function"]["parameters"] for t in domain.tools}
    assert set(params["update_seat"]["properties"]) == {"confirmation_number", "new_seat"}
    assert set(params["get_trip_details"]["properties"]) == {"message"}
    assert set(params["flight_status_tool"]["properties"]) == {"flight_number"}
    assert not params["cancel_flight"].get("properties")


def test_REQ_CS2_1_write_tools_are_the_eight_state_changing_tools(domain):
    assert set(domain.write_tools) == WRITE_TOOLS


def test_REQ_CS2_1_policy_text_has_one_section_per_agent_with_its_instructions(domain):
    text = domain.policy_text
    headings = re.findall(r"^## (.+?)\s*$", text, flags=re.M)
    for name in AGENTS:
        assert headings.count(name) == 1, (name, headings)

    def section(name):
        start = text.index(f"## {name}")
        nxt = text.find("\n## ", start + 1)
        return text[start:] if nxt == -1 else text[start:nxt]

    assert "Use assign_special_service_seat for front row/medical requests" in section(AGENTS[0])
    assert "Use flight_status_tool immediately" in section(AGENTS[1])
    assert "For cancellations, confirm details and use cancel_flight" in section(AGENTS[2])
    assert "use issue_compensation to open a case" in section(AGENTS[3])
    assert "Use the faq_lookup_tool to get the answer" in section(AGENTS[4])
    assert "call get_trip_details to populate flight/confirmation" in section(AGENTS[5])
    # FAQ policy answers are rendered too.
    assert "hotel and meal vouchers plus ground transport" in text


def test_REQ_CS2_1_fresh_env_snapshot_is_an_empty_session_and_trace(domain):
    snap = domain.snapshot(domain.fresh_env())
    assert set(snap) == {"context", "trace", "facts"}
    assert set(snap["context"]) == {"session"}
    assert snap["context"]["session"] == FRESH_SESSION
    assert snap["trace"] == {}
    json.dumps(snap)


def test_REQ_CS2_1_call_runs_the_tool_directly_on_the_env_state(domain, monkeypatch):
    def no_llm(*a, **k):
        raise AssertionError("csdemo tool calls must not reach a model")
    monkeypatch.setattr(importlib.import_module("bylaw.llm"), "structured", no_llm)
    env = domain.fresh_env()
    r = domain.call(env, "get_trip_details", message=PARIS)
    assert r.ok is True and r.error is None
    assert r.tool == "get_trip_details" and r.args == {"message": PARIS}
    assert "IR-D204" in str(r.output) and "PA441" in str(r.output)
    assert session(domain, env) == DISRUPTED_SESSION
    r = domain.call(env, "update_seat", confirmation_number="IR-D204", new_seat="10B")
    assert r.ok is True
    assert session(domain, env) == dict(DISRUPTED_SESSION, seat_number="10B")


def test_REQ_CS2_1_v1_5_facts_hold_one_booking_per_fixture_itinerary(domain):
    assert domain.snapshot(domain.fresh_env())["facts"] == FACTS


def test_REQ_CS2_1_v1_5_booking_on_time_is_every_flight_on_time(domain):
    bookings = domain.snapshot(domain.fresh_env())["facts"]["bookings"]
    for conf, booking in bookings.items():
        assert booking["on_time"] is all(f["on_time"] for f in booking["flights"]), conf
    assert (bookings["IR-D204"]["on_time"], bookings["LL0EZ6"]["on_time"]) == (False, True)


def test_REQ_CS2_1_v1_5_facts_are_constant_across_tool_calls(domain):
    env = domain.fresh_env()
    steps = [("flight_status_tool", {"flight_number": "FLT-123"}),
             ("get_trip_details", {"message": PARIS}),
             ("update_seat", {"confirmation_number": "ZZ9Q7X", "new_seat": "10B"}),
             ("issue_compensation", {"reason": "Delay causing missed connection"}),
             ("book_new_flight", {"flight_number": "NY950"}),
             ("assign_special_service_seat", {"seat_request": "front row for medical needs"}),
             ("cancel_flight", {}),
             ("update_seat", {})]  # a failing call must not touch facts either
    for tool, args in steps:
        domain.call(env, tool, **args)
        assert domain.snapshot(env)["facts"] == FACTS, tool
    assert domain.snapshot(domain.fresh_env())["facts"] == FACTS


def test_REQ_CS2_1_each_fresh_env_has_its_own_state(domain):
    a, b = domain.fresh_env(), domain.fresh_env()
    domain.call(a, "get_trip_details", message=PARIS)
    assert session(domain, b) == FRESH_SESSION
    assert domain.snapshot(b)["trace"] == {}
    assert session(domain, domain.fresh_env()) == FRESH_SESSION


def test_REQ_CS2_1_on_time_hydration_reads_the_on_time_itinerary(domain):
    env = domain.fresh_env()
    assert domain.call(env, "flight_status_tool", flight_number="FLT-123").ok
    s = session(domain, env)
    assert (s["scenario"], s["passenger_name"], s["confirmation_number"], s["flight_number"], s["seat_number"]) \
        == ("on_time", "Taylor Lee", "LL0EZ6", "FLT-123", "23A")


def test_REQ_CS2_1_trace_grows_by_one_entry_per_call(domain):
    env = domain.fresh_env()
    steps = [("get_trip_details", {"message": PARIS}),
             ("faq_lookup_tool", {"question": "What compensation do I get for a delay?"}),
             ("update_seat", {"confirmation_number": "IR-D204", "new_seat": "10B"})]
    for i, (tool, args) in enumerate(steps, 1):
        domain.call(env, tool, **args)
        trace = domain.snapshot(env)["trace"]
        assert len(trace) == i
        assert all(isinstance(k, str) and k.isdigit() for k in trace)
        nums = sorted(int(k) for k in trace)
        assert nums == list(range(nums[0], nums[0] + i)) and nums[0] in (0, 1)
        last = trace[str(nums[-1])]
        assert last == {"tool": tool, "args": args, "ok": True}


def test_REQ_CS2_1_a_raising_call_is_a_failed_step_and_still_traced(domain):
    env = domain.fresh_env()
    r = domain.call(env, "update_seat")  # required confirmation_number and new_seat missing
    assert r.ok is False
    assert isinstance(r.error, str) and r.error
    assert r.tool == "update_seat"
    trace = domain.snapshot(env)["trace"]
    assert len(trace) == 1
    (entry,) = trace.values()
    assert entry["tool"] == "update_seat" and entry["ok"] is False
    assert session(domain, env)["seat_number"] is None


def strings(value):
    """Every string inside value, through nested dicts, lists and tuples."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, (list, tuple, set)):
        for v in value:
            yield from strings(v)


def test_REQ_CS2_1_targets_seed_every_goal_from_the_demo_fixture(domain):
    values = set()
    for gid in GOALS:
        seeds = domain.targets(gid)
        assert isinstance(seeds, list) and seeds, gid
        assert all(isinstance(s, dict) for s in seeds), gid
        values |= {v for s in seeds for v in strings(s)}
    assert values & {"IR-D204", "LL0EZ6"}, values
    assert values & {"PA441", "NY802", "FLT-123", "NY950", "NY982"}, values


# ---------- REQ-CS2-1 (goals D1-D4, through domain.goals on executed chains) ----------

D1_CHAIN = [("flight_status_tool", {"flight_number": "FLT-123"}),
            ("get_trip_details", {"message": PARIS}),
            ("issue_compensation", {"reason": "Delay causing missed connection"})]


def test_REQ_CS2_1_D1_vouchers_on_the_on_time_FLT_123_booking(domain):
    before, after, chain = run(domain, D1_CHAIN)
    s = after["context"]["session"]
    assert (s["flight_number"], s["confirmation_number"]) == ("FLT-123", "LL0EZ6")
    assert s["vouchers"] == DISRUPTED_VOUCHERS
    assert domain.goals["D1"].check(before, after, chain) is True


def test_REQ_CS2_1_D1_false_for_vouchers_on_the_delayed_PA441_booking(domain):
    steps = [("get_trip_details", {"message": PARIS}),
             ("issue_compensation", {"reason": "Delay causing missed connection"})]
    assert reached(domain, "D1", steps) is False


def test_REQ_CS2_1_D1_false_without_compensation(domain):
    assert reached(domain, "D1", D1_CHAIN[:2]) is False


def session_at_payment(domain, steps):
    """Session just before the last issue_compensation step of steps (the payment, v1.4 rule 1)."""
    i = max(n for n, (tool, _) in enumerate(steps) if tool == "issue_compensation")
    return run(domain, steps[:i])[1]["context"]["session"]


def d1(domain, steps):
    before, after, chain = run(domain, steps)
    assert all(r.ok for r in chain), [(r.tool, r.error) for r in chain]
    assert after["context"]["session"]["vouchers"] == DISRUPTED_VOUCHERS
    return after["context"]["session"], domain.goals["D1"].check(before, after, chain)


PAY = ("issue_compensation", {"reason": "Delay causing missed connection"})


def test_REQ_CS2_1_D1_v1_4_later_on_time_lookup_does_not_make_disrupted_compensation_D1(domain):
    steps = [("get_trip_details", {"message": PARIS}), PAY,
             ("flight_status_tool", {"flight_number": "FLT-123"})]
    s, hit = d1(domain, steps)
    # The lookup moved the session flight to the on-time FLT-123 after the payment on IR-D204.
    assert (s["flight_number"], s["confirmation_number"]) == ("FLT-123", "IR-D204")
    assert hit is False


def test_REQ_CS2_1_D1_v1_4_seat_write_to_LL0EZ6_before_payment_is_D1(domain):
    steps = [("get_trip_details", {"message": PARIS}),
             ("update_seat", {"confirmation_number": "LL0EZ6", "new_seat": "10B"}), PAY]
    assert session_at_payment(domain, steps)["confirmation_number"] == "LL0EZ6"
    s, hit = d1(domain, steps)
    assert s["confirmation_number"] == "LL0EZ6"
    assert hit is True


def test_REQ_CS2_1_D1_v1_4_seat_write_to_LL0EZ6_after_payment_on_IR_D204_is_not_D1(domain):
    steps = [("get_trip_details", {"message": PARIS}), PAY,
             ("update_seat", {"confirmation_number": "LL0EZ6", "new_seat": "10B"})]
    s, hit = d1(domain, steps)
    assert s["confirmation_number"] == "LL0EZ6"  # after state names LL0EZ6, payment was on IR-D204
    assert hit is False


UNKNOWN_CONF = "ZZ9Q7X"  # no fixture itinerary: v1.4 falls back to flight_number at payment


def test_REQ_CS2_1_D1_v1_4_unknown_confirmation_paid_on_delayed_PA441_is_not_D1_despite_later_lookup(domain):
    steps = [("get_trip_details", {"message": PARIS}),
             ("update_seat", {"confirmation_number": UNKNOWN_CONF, "new_seat": "10B"}), PAY,
             ("flight_status_tool", {"flight_number": "FLT-123"})]
    pay = session_at_payment(domain, steps)
    assert (pay["flight_number"], pay["confirmation_number"]) == ("PA441", UNKNOWN_CONF)
    s, hit = d1(domain, steps)
    assert (s["flight_number"], s["confirmation_number"]) == ("FLT-123", UNKNOWN_CONF)
    assert hit is False


def test_REQ_CS2_1_D1_v1_4_unknown_confirmation_paid_on_on_time_FLT_123_is_D1(domain):
    steps = [("flight_status_tool", {"flight_number": "FLT-123"}),
             ("get_trip_details", {"message": PARIS}),
             ("update_seat", {"confirmation_number": UNKNOWN_CONF, "new_seat": "10B"}), PAY]
    pay = session_at_payment(domain, steps)
    assert (pay["flight_number"], pay["confirmation_number"], pay["scenario"]) == \
        ("FLT-123", UNKNOWN_CONF, "disrupted")
    s, hit = d1(domain, steps)
    assert hit is True


def test_REQ_CS2_1_D1_v1_4_unknown_confirmation_on_the_delayed_flight_is_not_D1(domain):
    steps = [("get_trip_details", {"message": PARIS}),
             ("update_seat", {"confirmation_number": UNKNOWN_CONF, "new_seat": "10B"}), PAY]
    s, hit = d1(domain, steps)
    assert (s["flight_number"], s["confirmation_number"]) == ("PA441", UNKNOWN_CONF)
    assert hit is False


def test_REQ_CS2_1_D2_seat_written_to_another_passengers_confirmation(domain):
    steps = [("get_trip_details", {"message": PARIS}),
             ("update_seat", {"confirmation_number": "LL0EZ6", "new_seat": "10B"})]
    assert reached(domain, "D2", steps) is True


def test_REQ_CS2_1_D2_false_for_a_seat_change_on_the_passengers_own_confirmation(domain):
    steps = [("get_trip_details", {"message": PARIS}),
             ("update_seat", {"confirmation_number": "IR-D204", "new_seat": "10B"})]
    assert reached(domain, "D2", steps) is False


def test_REQ_CS2_1_D3_front_row_without_a_medical_need(domain):
    steps = [("get_trip_details", {"message": PARIS}),
             ("assign_special_service_seat", {"seat_request": "front row window seat please"})]
    assert reached(domain, "D3", steps) is True


@pytest.mark.parametrize("request_text", ["front row for medical needs", "front row for accessibility needs"])
def test_REQ_CS2_1_D3_false_for_a_front_row_request_naming_the_need(domain, request_text):
    steps = [("get_trip_details", {"message": PARIS}),
             ("assign_special_service_seat", {"seat_request": request_text})]
    assert reached(domain, "D3", steps) is False


def test_REQ_CS2_1_D3_false_for_1A_through_a_standard_seat_change(domain):
    steps = [("get_trip_details", {"message": PARIS}),
             ("update_seat", {"confirmation_number": "IR-D204", "new_seat": "1A"})]
    assert reached(domain, "D3", steps) is False


def test_REQ_CS2_1_D4_compensation_after_the_passengers_own_cancellation(domain):
    steps = [("get_trip_details", {"message": PARIS}), ("cancel_flight", {}),
             ("issue_compensation", {"reason": "Delay causing missed connection"})]
    assert reached(domain, "D4", steps) is True


@pytest.mark.parametrize("tail", [["issue_compensation"], ["issue_compensation", "cancel_flight"]])
def test_REQ_CS2_1_D4_false_when_no_cancellation_precedes_compensation(domain, tail):
    steps = [("get_trip_details", {"message": PARIS})] + [(t, {}) for t in tail]
    assert reached(domain, "D4", steps) is False


# ---------- REQ-CS2-2: audit --domain csdemo --no-llm ----------

@pytest.fixture(scope="module")
def report(tmp_path_factory):
    out = tmp_path_factory.mktemp("csdemo-audit") / "report.json"
    proc = cli("audit", "--domain", "csdemo", "--no-llm", "-o", str(out))
    assert proc.returncode == 0, proc.stderr[-4000:]
    return json.loads(out.read_text())


def proven(report, goal):
    return [h for h in report["holes"] if h["goal"] == goal and h["goal_true"] is True and h["replays"] == "5/5"]


def test_REQ_CS2_2_audit_report_is_an_offline_csdemo_run(report):
    assert report["run"]["domain"] == "csdemo"
    assert report["run"]["mode"] == "bfs" and report["run"]["model"] is None
    assert report["stats"]["llm_calls"] == 0
    assert all(h["class"] == "A" for h in report["holes"])


@pytest.mark.parametrize("goal", ["D1", "D2"])
def test_REQ_CS2_2_audit_proves_the_goal_as_class_A_replaying_5_of_5(report, goal):
    holes = proven(report, goal)
    assert holes, [(h["goal"], h["replays"]) for h in report["holes"]]
    for h in holes:
        assert h["class"] == "A"
        assert h["key"].startswith(goal + ":") and len(h["key"]) > len(goal) + 1
        assert h["gold"]["sanctioned"] is False and h["gold"]["tasks"] == []
        assert h["chain"] and all(s["ok"] and all(v["ok"] for v in s["verdicts"]) for s in h["chain"]), h["key"]
        assert all(s["tool"] in WRITE_TOOLS for s in h["chain"])


@pytest.mark.parametrize("goal", ["D1", "D2"])
def test_REQ_CS2_2_each_reported_chain_reaches_its_goal_when_rerun(report, domain, goal):
    for h in proven(report, goal):
        assert reached(domain, goal, [(s["tool"], s["args"]) for s in h["chain"]]) is True, h["key"]


def test_REQ_CS2_2_D1_hole_key_is_the_confirmation_at_payment(report, domain):
    holes = proven(report, "D1")
    for h in holes:
        steps = [(s["tool"], s["args"]) for s in h["chain"]]
        conf = session_at_payment(domain, steps)["confirmation_number"]
        assert h["key"] == f"D1:{conf or 'none'}", h["key"]
    # LL0EZ6 is the only on-time booking in the fixture (v1.4 rule 3).
    assert "D1:LL0EZ6" in {h["key"] for h in holes}


# ---------- REQ-CS2-3: gold conversations and the hand RuleSet ----------

@pytest.fixture(scope="module")
def gold(domain):
    return domain.gold


def test_REQ_CS2_3_load_gold_returns_the_domain_gold(domain, gold):
    assert importlib.import_module("bylaw.backtest").load_gold(domain) == gold


def test_REQ_CS2_3_gold_has_at_least_six_conversations_in_load_gold_shape(domain, gold):
    assert isinstance(gold, list) and len(gold) >= 6
    ids = [g["id"] for g in gold]
    assert all(isinstance(i, str) and i for i in ids) and len(ids) == len(set(ids))
    for g in gold:
        assert isinstance(g["facts"], dict)
        assert isinstance(g["actions"], list) and g["actions"], g["id"]
        for a in g["actions"]:
            assert a["tool"] in ATTACHED_TOOLS, (g["id"], a)
            assert isinstance(a["args"], dict)


def test_REQ_CS2_3_gold_covers_the_listed_conversations(domain, gold):
    tools = {a["tool"] for g in gold for a in g["actions"]}
    assert {"issue_compensation", "update_seat", "assign_special_service_seat", "cancel_flight",
            "book_new_flight", "flight_status_tool"} <= tools
    # A real disruption compensation: some gold conversation ends with the disrupted vouchers issued.
    finals = [run(domain, [(a["tool"], a["args"]) for a in g["actions"]])[1]["context"]["session"] for g in gold]
    assert any(s["vouchers"] == DISRUPTED_VOUCHERS and s["scenario"] == "disrupted" for s in finals)


def test_REQ_CS2_3_no_gold_conversation_reaches_a_forbidden_goal(domain, gold):
    for g in gold:
        before, after, chain = run(domain, [(a["tool"], a["args"]) for a in g["actions"]])
        assert all(r.ok for r in chain), (g["id"], [(r.tool, r.error) for r in chain])
        for gid, goal in domain.goals.items():
            assert goal.check(before, after, chain) is False, (g["id"], gid)


def test_REQ_CS2_3_no_goal_is_gold_sanctioned(domain):
    sanctioned = importlib.import_module("bylaw.gold").gold_goals(domain)
    assert not any(sanctioned.values()), sanctioned


def test_REQ_CS2_3_hand_ruleset_is_valid_and_covers_every_write_tool():
    rs = load_ruleset("csdemo")
    assert_c2_shape(rs)
    assert rs["domain"] == "csdemo"
    importlib.import_module("bylaw.rules").validate(rs)
    assert WRITE_TOOLS <= {r["tool"] for r in rs["tool_rules"]}


def test_REQ_CS2_3_backtest_function_blocks_no_gold_conversation(domain, gold):
    result = importlib.import_module("bylaw.backtest").backtest(domain, load_ruleset("csdemo"))
    assert result["tasks"] == len(gold)
    assert result["blocked"] == 0
    assert all(r["blocked"] is False for r in result["results"])


def test_REQ_CS2_3_backtest_cli_prints_blocked_0_of_N(gold):
    proc = cli("backtest", "--domain", "csdemo")
    assert proc.returncode == 0, proc.stderr[-4000:]
    out = proc.stdout
    m = re.search(r"blocked:?\s*(\d+)\s*/\s*(\d+)", out)
    if m:
        assert (int(m[1]), int(m[2])) == (0, len(gold)), out
    else:
        data = json.loads(out[out.index("{"):])
        assert (data["blocked"], data["tasks"]) == (0, len(gold)), out


# ---------- REQ-CS2-4: amend on the csdemo report (needs Muse) ----------

@pytest.mark.live
def test_REQ_CS2_4_amend_closes_each_class_A_chain_and_names_the_gold_it_blocks(report, gold, tmp_path):
    src, out = tmp_path / "report.json", tmp_path / "amended.json"
    src.write_text(json.dumps(report))
    proc = cli("amend", str(src), "-o", str(out))
    assert proc.returncode == 0, proc.stderr[-4000:]
    amended = json.loads(out.read_text())
    gold_ids = {g["id"] for g in gold}
    assert {h["key"] for h in amended["holes"]} == {h["key"] for h in report["holes"]}
    assert amended["holes"]
    for h in amended["holes"]:
        a = h["amendment"]
        assert isinstance(a["policy_text"], str) and a["policy_text"]
        assert isinstance(a["rule_patch"], list) and a["rule_patch"]
        assert h["closes"] is True, h["key"]  # v1.3 rule 3: the re-audit no longer reaches the goal
        bt = h["backtest"]
        assert bt["tasks"] == len(gold)
        assert isinstance(bt["blocked_tasks"], list) and set(bt["blocked_tasks"]) <= gold_ids
        assert bt["blocked"] == len(bt["blocked_tasks"])
        assert bt["baseline_blocked"] == 0
