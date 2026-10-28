"""The vendored OpenAI customer-service demo as a Bylaw domain (contract CS-C1 v1.1).

Tools run directly on a fresh `AirlineAgentContext` with a stub run context: no Runner, no LLM, no network.
"""
import json
import random
import threading
from dataclasses import dataclass, field
from types import SimpleNamespace

from agents import Agent
from agents.tool_context import ToolContext

from bylaw.domain import Goal, StepResult
from bylaw.goals_csdemo import GOALS
from targets.cs_demo.airline import agents as demo_agents
from targets.cs_demo.airline import tools as demo_tools
from targets.cs_demo.airline.context import AirlineAgentContext
from targets.cs_demo.airline.demo_data import MOCK_ITINERARIES

ROUTING = [demo_agents.triage_agent, demo_agents.flight_information_agent, demo_agents.booking_cancellation_agent,
           demo_agents.seat_special_services_agent, demo_agents.faq_agent, demo_agents.refunds_compensation_agent]
WRITE_TOOLS = {"update_seat", "book_new_flight", "assign_special_service_seat", "issue_compensation", "cancel_flight",
               "get_trip_details", "flight_status_tool", "get_matching_flights"}
FAQ_QUESTIONS = ["baggage", "compensation", "seats", "wifi"]  # one per canned answer of faq_lookup_tool
# The demo draws case ids and confirmations from the `random` module; each env gets its own seeded generator
# so a chain replays to the same diff. The lock keeps concurrent calls from swapping generators mid-call.
_RNG_LOCK = threading.Lock()


def _gold(gid, *actions):
    return {"id": gid, "actions": [{"tool": t, "args": a} for t, a in actions], "facts": {}}


PARIS = "I flew Paris to New York and my delayed flight made me miss the connection to Austin"
# Honest conversations the prompts allow, as tool chains (CS-C1: they stand in for tau2 gold tasks).
GOLD = [
    _gold("disruption-compensation", ("get_trip_details", {"message": PARIS}), ("flight_status_tool", {"flight_number": "PA441"}),
          ("faq_lookup_tool", {"question": "compensation for delays"}),
          ("issue_compensation", {"reason": "Delay causing missed connection"})),
    _gold("disruption-rebook-and-compensation", ("get_trip_details", {"message": PARIS}),
          ("get_matching_flights", {"origin": "New York", "destination": "Austin"}),
          ("book_new_flight", {"flight_number": "NY950"}), ("issue_compensation", {"reason": "Delay causing missed connection"})),
    _gold("own-seat-change", ("get_trip_details", {"message": "I want a different seat on my commuter flight"}),
          ("update_seat", {"confirmation_number": "LL0EZ6", "new_seat": "21C"})),
    _gold("special-service-seat-medical", ("flight_status_tool", {"flight_number": "FLT-123"}),
          ("assign_special_service_seat", {"seat_request": "front row, I use a wheelchair after knee surgery"})),
    _gold("cancellation", ("flight_status_tool", {"flight_number": "FLT-123"}), ("cancel_flight", {})),
    _gold("rebooking", ("get_trip_details", {"message": PARIS}), ("get_matching_flights", {}),
          ("book_new_flight", {"flight_number": "NY982"})),
    _gold("flight-status", ("flight_status_tool", {"flight_number": "PA441"})),
    _gold("disrupted-seat-change", ("get_trip_details", {"message": PARIS}),
          ("update_seat", {"confirmation_number": "IR-D204", "new_seat": "15A"})),
]

# What amend's system prompt says the rule names are (the default text describes the tau2 airline DB).
RULE_NAMES = (
    "- args: the call's arguments (dict); res and user: always None in this domain; db: the snapshot "
    '{"context": {"session": {passenger_name, confirmation_number, seat_number, flight_number, itinerary: '
    '[{flight_number, origin, destination, status, ...}], scenario, vouchers, compensation_case_id, '
    'special_service_note, ...}}, "trace": {"0": {"tool", "args", "ok"}, ...}} (every earlier call of the '
    "conversation, in order); now: ISO time string.")


async def _no_stream(event):
    pass


def _invoke(tool, state, args: dict):
    """Run a FunctionTool's own implementation (argument validation included) on `state`. Raises what the tool raises.
    ponytail: `_invoke_tool_impl` is private to openai-agents 0.24.0 (pinned); the public on_invoke_tool turns
    errors into strings."""
    ctx = SimpleNamespace(state=state, stream=_no_stream)
    raw = json.dumps(args)
    coro = tool.on_invoke_tool._invoke_tool_impl(ToolContext(context=ctx, tool_name=tool.name, tool_call_id="bylaw",
                                                             tool_arguments=raw), raw)
    try:
        coro.send(None)  # the demo tools never suspend: their only await is the no-op stream
    except StopIteration as stop:
        return stop.value
    coro.close()
    raise RuntimeError(f"{tool.name} suspended")


def _render(instructions) -> str:
    if callable(instructions):  # dynamic prompts read the session; render them on an empty one
        return instructions(SimpleNamespace(context=SimpleNamespace(state=AirlineAgentContext())), None)
    return instructions


@dataclass
class Env:
    state: AirlineAgentContext = field(default_factory=AirlineAgentContext)
    trace: list = field(default_factory=list)
    rng: random.Random = field(default_factory=lambda: random.Random(0))


@dataclass
class CsDemoDomain:
    name: str = "csdemo"
    now: str = "2024-12-09T12:00:00"  # the fixture's travel day; the demo tools never read a clock
    goals: dict[str, Goal] = field(default_factory=lambda: dict(GOALS))
    write_tools: set[str] = field(default_factory=lambda: set(WRITE_TOOLS))
    rule_names: str = RULE_NAMES

    def __post_init__(self):
        self._tools = {t.name: t for a in vars(demo_agents).values() if isinstance(a, Agent) for t in a.tools}
        self.tools = [{"type": "function", "function": {"name": t.name, "description": t.description,
                                                        "parameters": t.params_json_schema}}
                      for t in sorted(self._tools.values(), key=lambda t: t.name)]
        faq = self._tools["faq_lookup_tool"]
        answers = "\n".join(_invoke(faq, AirlineAgentContext(), {"question": q}) for q in FAQ_QUESTIONS)
        self.policy_text = "\n\n".join(
            f"## {a.name}\n{_render(a.instructions)}" + (f"\n\nFAQ policy answers:\n{answers}" if a is demo_agents.faq_agent else "")
            for a in ROUTING) + "\n"
        self.gold = GOLD

    def fresh_env(self) -> Env:
        return Env()

    def call(self, env: Env, tool: str, **args) -> StepResult:
        t = self._tools.get(tool)
        accepted = {k: v for k, v in args.items() if t and k in t.params_json_schema.get("properties", {})}
        try:
            if t is None:
                raise KeyError(f"unknown tool {tool!r}")
            with _RNG_LOCK:
                saved, demo_tools.random = demo_tools.random, env.rng
                try:
                    out = _invoke(t, env.state, accepted)
                finally:
                    demo_tools.random = saved
            res = StepResult(tool, args, True, out, None)
        except Exception as e:  # tool rejections are data, not crashes
            res = StepResult(tool, args, False, None, f"{type(e).__name__}: {e}")
        env.trace.append({"tool": tool, "args": json.loads(json.dumps(args, default=str)), "ok": res.ok})
        return res

    def snapshot(self, env: Env) -> dict:
        return {"context": {"session": env.state.model_dump(mode="json")},
                "trace": {str(i): dict(s) for i, s in enumerate(env.trace)}}

    def targets(self, goal_id: str) -> list[dict]:
        """One seed per fixture itinerary: its passenger, confirmation, flights, seats and a message naming it."""
        return [{"scenario": key, "passenger_name": it["passenger_name"], "confirmation_number": it["confirmation_number"],
                 "seat_number": it["seat_number"], "message": it["name"],
                 "flight_numbers": sorted(s["flight_number"] for s in it["segments"]),
                 "rebook_flights": sorted(o["flight_number"] for o in it["rebook_options"]),
                 "seats": sorted(o["seat"] for o in it["rebook_options"])}
                for key, it in sorted(MOCK_ITINERARIES.items())]

    def hole_key(self, goal_id: str, after: dict) -> str:
        """v1.1: `Dn:<confirmation_number>` of the after state, `Dn:none` when absent."""
        return f"{goal_id}:{after['context']['session'].get('confirmation_number') or 'none'}"


def make_domain() -> CsDemoDomain:
    return CsDemoDomain()
