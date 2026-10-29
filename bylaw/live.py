"""CS-C3 live runner: play a script's customer turns against the vendored demo agents and record an event file."""
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any

from agents import ItemHelpers, ModelSettings, Runner, set_tracing_disabled
from chatkit.types import ThreadMetadata
from pydantic import Field

from bylaw import llm
from bylaw.domain import get_domain
from bylaw.executor import diff
from bylaw.proxy import agents_guard
from bylaw.ratified import ROOT
from targets.cs_demo.airline.context import AirlineAgentChatContext, create_initial_context


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


def _session(state) -> dict:
    return {"context": {"session": state.model_dump(mode="json")}}


async def _run(script: dict, guard: bool, model, ruleset, domain_name) -> dict:
    from openai.types.shared import Reasoning

    from targets.cs_demo.airline import agents as A, guardrails as G

    set_tracing_disabled(True)
    main = [A.triage_agent, A.faq_agent, A.seat_special_services_agent, A.flight_information_agent,
            A.booking_cancellation_agent, A.refunds_compensation_agent]
    for ag in main + [G.guardrail_agent, G.jailbreak_guardrail_agent]:  # every model call goes to `model`
        ag.model, ag.model_settings = model, ModelSettings(reasoning=Reasoning(effort="low"))
    write_tools, log = get_domain(domain_name).write_tools, []
    agents_guard._install(main, domain_name, ruleset, log, enforce=guard)

    t0, events = time.monotonic(), []

    def emit(kind, **kw):
        events.append({"t": round(time.monotonic() - t0, 3), "type": kind, **kw})

    out = {"name": script["name"], "guard": guard, "model": llm.model(),
           "started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "events": events}
    state, agent, items, names = create_initial_context(), A.triage_agent, [], {}
    last = _session(state)
    for text in script["turns"]:
        emit("user", text=text)
        items.append({"role": "user", "content": text})
        run = Runner.run_streamed(agent, items, context=Ctx(state=state), max_turns=12)
        async for e in run.stream_events():
            if e.type != "run_item_stream_event":
                continue
            it = e.item
            if e.name == "message_output_created":
                emit("agent_message", agent=it.agent.name, text=ItemHelpers.text_message_output(it))
            elif e.name == "handoff_occured":
                emit("handoff", **{"from": it.source_agent.name, "to": it.target_agent.name})
            elif e.name == "tool_called":
                names[it.raw_item.call_id] = it.raw_item.name
                emit("tool_call", agent=it.agent.name, tool=it.raw_item.name, args=json.loads(it.raw_item.arguments or "{}"))
            elif e.name == "tool_output":
                while log:  # the guard ran before this output: its verdicts go first
                    c = log.pop(0)
                    emit("bylaw_check", tool=c["tool"], allowed=c["allowed"], rule_id=c["rule_id"],
                         policy_ref=c["policy_ref"], enforced=guard)
                tool = names[it.raw_item["call_id"]]
                emit("tool_output", tool=tool, output=str(it.output))
                if tool in write_tools:
                    now = _session(state)
                    emit("state", diff=diff(last, now))
                    last = now
        agent, items = run.last_agent, run.to_input_list()
    out["final_state"] = state.model_dump(mode="json")
    return out


def run(script: dict, guard: bool, model, ruleset: dict | None = None, domain_name: str = "csdemo") -> dict:
    """CS-C3 event file of one scripted conversation. Without `guard` the checks are recorded, not enforced."""
    return asyncio.run(_run(script, guard, model, ruleset, domain_name))
