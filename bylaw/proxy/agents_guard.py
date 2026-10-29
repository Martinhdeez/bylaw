"""CS-C2 agents guard: a ToolInputGuardrail on every FunctionTool that checks the call against the effective RuleSet
on the live context before the tool runs."""
import json

from agents import FunctionTool, ToolGuardrailFunctionOutput, ToolInputGuardrail

from bylaw import rules
from bylaw.domain import get_domain
from bylaw.proxy.core import default_ruleset

NAME = "bylaw"


def snapshot(state, trace: list[dict]) -> dict:
    """CS-C1 snapshot of a live AirlineAgentContext and the guard's trace."""
    return {"context": {"session": state.model_dump(mode="json")}, "trace": {str(n): s for n, s in enumerate(trace)}}


def _install(agents, domain_name, ruleset, log, enforce: bool) -> None:
    """install, with enforce=False for a run that records the verdicts without blocking (the unguarded live run)."""
    # ponytail: one trace per state object for the guard's lifetime; states stay referenced until the guard goes
    traces: dict[int, tuple[object, list[dict]]] = {}
    effective = now = None

    def check(data):
        nonlocal effective, now
        if effective is None:  # on the first call, so an install never reads the store or builds the domain
            effective, now = ruleset or default_ruleset(domain_name), get_domain(domain_name).now
        ctx = data.context
        state = ctx.context.state
        trace = traces.setdefault(id(state), (state, []))[1]
        tool, args = ctx.tool_name, json.loads(ctx.tool_arguments or "{}")
        denied = next((v for v in rules.check(effective, snapshot(state, trace), tool, args, now)
                       if not v.ok), None)
        if log is not None:
            log.append({"tool": tool, "args": args, "allowed": denied is None,
                        "rule_id": denied and denied.rule_id, "policy_ref": denied and denied.policy_ref})
        if denied and enforce:
            return ToolGuardrailFunctionOutput.reject_content(
                f"Bylaw: blocked {tool}: {denied.rule_id} {denied.policy_ref}")
        # ponytail: ok=True at check time; the guard does not see whether the tool then raised
        trace.append({"tool": tool, "args": args, "ok": True})
        return ToolGuardrailFunctionOutput.allow()

    guard = ToolInputGuardrail(guardrail_function=check, name=NAME)
    for agent in agents:
        for t in agent.tools:
            if isinstance(t, FunctionTool):
                t.tool_input_guardrails = [g for g in t.tool_input_guardrails or [] if g.name != NAME] + [guard]


def install(agents, domain_name="csdemo", ruleset=None, log=None) -> None:
    """CS-C2: append one Bylaw ToolInputGuardrail to every FunctionTool of every agent. Idempotent: a second install
    replaces the first guard."""
    _install(agents, domain_name, ruleset, log, enforce=True)
