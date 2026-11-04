"""CS-C3 live runner: play a script's customer turns against the vendored demo agents and record an event file.
VZ3-C2: the same turn loop over a Session object, one customer turn at a time, for the live demo UI."""
import asyncio
import json
import time
import weakref
from datetime import datetime, timezone
from typing import Any

from agents import (FunctionTool, InputGuardrailTripwireTriggered, ItemHelpers, ModelSettings, Runner,
                    set_tracing_disabled)
from agents.models.interface import Model
from chatkit.types import ThreadMetadata
from pydantic import Field

from bylaw import llm
from bylaw.domain import get_domain
from bylaw.env.cs_demo import facts
from bylaw.executor import diff
from bylaw.proxy import agents_guard
from bylaw.proxy.core import default_ruleset
from bylaw.ratified import ROOT
from targets.cs_demo.airline.context import AirlineAgentChatContext, create_initial_context

# VZ3-C6: input plus output tokens reported by the live sessions' models, process-wide; TR1: also split in and out
USAGE = {"tokens": 0, "input_tokens": 0, "output_tokens": 0}
_LOCKS: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()  # event loop -> its turn lock


class Ctx(AirlineAgentChatContext):
    """The demo's chat context outside a ChatKit server: no thread store, progress updates dropped."""
    thread: ThreadMetadata = Field(default_factory=lambda: ThreadMetadata(id="live", created_at=datetime.now()))
    store: Any = None
    request_context: dict = Field(default_factory=dict)

    async def stream(self, event):
        pass


def muse_model():
    """Muse through Chat Completions with the Bylaw client settings (bylaw.llm); tracing off, nothing sent to OpenAI."""
    from agents import OpenAIChatCompletionsModel
    from openai import AsyncOpenAI

    sync = llm.client()  # reads MODEL_BASE_URL and MODEL_API_KEY loaded from .env
    return OpenAIChatCompletionsModel(model=llm.model(),
                                      openai_client=AsyncOpenAI(base_url=str(sync.base_url), api_key=sync.api_key))


class Counted(Model):
    """A model whose reported usage, streamed or not, adds up in USAGE (VZ3-C6 token cap)."""

    def __init__(self, inner):
        self.inner = inner

    def _add(self, usage):
        if usage is not None:
            i, o = usage.input_tokens or 0, usage.output_tokens or 0
            USAGE["input_tokens"] += i
            USAGE["output_tokens"] += o
            USAGE["tokens"] += i + o

    async def get_response(self, *a, **kw):
        r = await self.inner.get_response(*a, **kw)
        self._add(r.usage)
        return r

    async def stream_response(self, *a, **kw):
        async for e in self.inner.stream_response(*a, **kw):
            if e.type == "response.completed":
                self._add(e.response.usage)
            yield e


def _session(state) -> dict:
    return {"context": {"session": state.model_dump(mode="json")}}


def _demo_agents():
    from targets.cs_demo.airline import agents as A, guardrails as G

    return ([A.triage_agent, A.faq_agent, A.seat_special_services_agent, A.flight_information_agent,
             A.booking_cancellation_agent, A.refunds_compensation_agent], [G.guardrail_agent, G.jailbreak_guardrail_agent])


class _Log(list):
    """The guard's verdict log; each entry gets the VZ3-C3 fields at check time, before the tool runs."""

    def __init__(self, session):
        super().__init__()
        self.s = session

    def append(self, c):
        s = self.s
        st = s.state.model_dump(mode="json")
        super().append({**c, "session": st, "booking": facts()["bookings"].get(st["confirmation_number"]),
                        "prior_tools": list(s.trace),
                        "rules_checked": [r["id"] for r in s.ruleset["tool_rules"] if r["tool"] == c["tool"]]})
        if c["allowed"] or not s.guard:  # what the guard appends to its own trace
            s.trace.append(c["tool"])


class Session:
    """One live conversation: the demo state, the current agent and the input items kept between customer turns."""

    def __init__(self, guard: bool, model, ruleset: dict | None = None, domain_name: str = "csdemo",
                 guardrail_events: bool = True):
        main, _ = _demo_agents()
        self.guard, self.model, self.guardrail_events = guard, model, guardrail_events
        self.ruleset = ruleset or default_ruleset(domain_name)
        self.write_tools = get_domain(domain_name).write_tools
        self.state, self.agent, self.items = create_initial_context(), main[0], []
        self.names, self.trace, self.log = {}, [], _Log(self)
        self.last = _session(self.state)
        self.t0, self.events = time.monotonic(), []
        self.started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.busy, self.turns, self.used = False, 0, time.monotonic()  # the API's bookkeeping (VZ3-C2, C6)
        agents_guard._install(main, domain_name, self.ruleset, self.log, enforce=guard)
        self.bylaw_guard = next(g for g in main[0].tools[0].tool_input_guardrails if g.name == agents_guard.NAME)

    def _apply(self):
        """Point the shared demo agents at this session's model and guard; every model call goes to `model`."""
        from openai.types.shared import Reasoning

        set_tracing_disabled(True)
        main, rails = _demo_agents()
        for ag in main + rails:
            ag.model, ag.model_settings = self.model, ModelSettings(reasoning=Reasoning(effort="low"))
        for ag in main:
            for g in ag.input_guardrails:  # live: the demo guardrails finish before the agent may call a tool
                g.run_in_parallel = not self.guardrail_events
            for t in ag.tools:
                if isinstance(t, FunctionTool):
                    t.tool_input_guardrails = [g for g in t.tool_input_guardrails or []
                                               if g.name != agents_guard.NAME] + [self.bylaw_guard]

    def _ev(self, kind, **kw) -> dict:
        e = {"t": round(time.monotonic() - self.t0, 3), "type": kind, **kw}
        self.events.append(e)
        return e

    def _item(self, e) -> list[dict]:
        it = e.item
        if e.name == "message_output_created":
            return [self._ev("agent_message", agent=it.agent.name, text=ItemHelpers.text_message_output(it))]
        if e.name == "handoff_occured":
            return [self._ev("handoff", **{"from": it.source_agent.name, "to": it.target_agent.name})]
        if e.name == "tool_called":
            self.names[it.raw_item.call_id] = it.raw_item.name
            return [self._ev("tool_call", agent=it.agent.name, tool=it.raw_item.name,
                             args=json.loads(it.raw_item.arguments or "{}"))]
        if e.name != "tool_output":
            return []
        out = []
        while self.log:  # the guard ran before this output: its verdicts go first
            c = self.log.pop(0)
            out.append(self._ev("bylaw_check", tool=c["tool"], allowed=c["allowed"], rule_id=c["rule_id"],
                                policy_ref=c["policy_ref"], enforced=self.guard, args=c["args"], session=c["session"],
                                booking=c["booking"], prior_tools=c["prior_tools"], rules_checked=c["rules_checked"]))
        tool = self.names[it.raw_item["call_id"]]
        out.append(self._ev("tool_output", tool=tool, output=str(it.output)))
        if tool in self.write_tools:
            now = _session(self.state)
            out.append(self._ev("state", diff=diff(self.last, now)))
            self.last = now
        return out

    def _rails(self, run, seen: int) -> list[dict]:
        """VZ3-C4 events of the demo guardrails finished since result `seen`, a tripped one last."""
        if not self.guardrail_events:
            return []
        done = sorted(run.input_guardrail_results[seen:], key=lambda r: r.output.tripwire_triggered)
        return [self._ev("guardrail", name=r.guardrail.guardrail_function.__name__,
                         passed=not r.output.tripwire_triggered,
                         reasoning=getattr(r.output.output_info, "reasoning", "")) for r in done]

    async def turn(self, text: str):
        """One customer turn as CS-C3 events. A model or tool failure raises and leaves the input items and the
        current agent as they were; a guardrail tripwire ends the turn after its guardrail event."""
        # ponytail: one turn at a time per process, since sessions share the demo's agent objects; per-session
        # copies of the agent graph if visitors queue too long
        async with _LOCKS.setdefault(asyncio.get_running_loop(), asyncio.Lock()):
            self._apply()
            self.log.clear()  # verdicts of an aborted turn that never reached a tool output
            n = len(self.events)
            yield self._ev("user", text=text)
            items = self.items + [{"role": "user", "content": text}]
            run = Runner.run_streamed(self.agent, items, context=Ctx(state=self.state), max_turns=12)
            seen = 0

            def tripped():
                return any(r.output.tripwire_triggered for r in run.input_guardrail_results)

            try:
                async for e in run.stream_events():
                    for ev in self._rails(run, seen):
                        yield ev
                    seen = len(run.input_guardrail_results)
                    if e.type == "run_item_stream_event" and not tripped():
                        for ev in self._item(e):
                            yield ev
            except InputGuardrailTripwireTriggered:
                if not self.guardrail_events:
                    raise
            except Exception:
                del self.events[n:]  # the export keeps only completed turns
                raise
            for ev in self._rails(run, seen):
                yield ev
            if tripped():  # VZ3-C4: the turn ends here; the customer's message is not kept
                del self.events[n:]
                return
            self.agent, self.items = run.last_agent, run.to_input_list()

    def export(self, name: str) -> dict:
        """The conversation so far as a CS-C3 event file."""
        return {"name": name, "guard": self.guard, "model": llm.model(), "started": self.started,
                "events": self.events, "final_state": self.state.model_dump(mode="json")}


async def _run(script: dict, guard: bool, model, ruleset, domain_name) -> dict:
    s = Session(guard, model, ruleset, domain_name, guardrail_events=False)
    for text in script["turns"]:
        async for _ in s.turn(text):
            pass
    return s.export(script["name"])


def run(script: dict, guard: bool, model, ruleset: dict | None = None, domain_name: str = "csdemo") -> dict:
    """CS-C3 event file of one scripted conversation. Without `guard` the checks are recorded, not enforced."""
    return asyncio.run(_run(script, guard, model, ruleset, domain_name))
