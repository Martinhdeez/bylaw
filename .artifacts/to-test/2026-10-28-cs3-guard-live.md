# CS3: agents guard and live runner

Item CS3 of iteration 06 (REQ-CS3-1..3, contracts CS-C2, CS-C3, clarifications v1.2). Branch `feat/cs3-guard-live`.

## Problem

The demo agents run any tool call the model proposes. REQ-CS3-1 asks that a call the effective RuleSet forbids is not executed and that the agent reads `Bylaw: blocked <tool>: <rule_id> <policy_ref>`. REQ-CS3-2 and REQ-CS3-3 ask for a recorded live conversation (event file) and an API to serve it.

## Root cause

Not a defect: nothing existed. The interception point is `FunctionTool.tool_input_guardrails` (`.venv/.../agents/run_internal/tool_execution.py:2041`, guardrails run before `on_tool_start`; spike section 4).

## Change

- `bylaw/proxy/agents_guard.py:56` `install(agents, domain_name="csdemo", ruleset=None, log=None)`: one `ToolInputGuardrail` named `bylaw` per FunctionTool; a second install replaces it (idempotent). The check (`:29`) reads `data.context.context.state`, builds the CS-C1 snapshot (`:18`) with the guard's own trace (allowed calls only, `ok: true`, keys from `"0"`), runs `rules.check` and names the first failing verdict in RuleSet order (`:37`). A private `_install(..., enforce=False)` records verdicts without blocking; the unguarded live run uses it.
- `bylaw/live.py`: `run(script, guard, model, ruleset=None)` sets every demo agent, including the relevance and jailbreak guardrail agents, to `model` with reasoning effort low, disables tracing, and plays the turns with `Runner.run_streamed`. Stream events map to `user`, `agent_message`, `handoff`, `tool_call`, `bylaw_check` (from the guard log, `enforced` = `--guard`), `tool_output`, and `state` (C4 diff of the session after each write tool; `{}` for a blocked call). Header `model` is `MODEL` (default `muse-spark-1.3`); `final_state` is `state.model_dump(mode="json")`. `muse_model()` builds `OpenAIChatCompletionsModel` from the `bylaw.llm` client settings.
- `bylaw/__main__.py`: `live --domain csdemo --script FILE [--guard] -o OUT`.
- `bylaw/api.py`: `GET /api/live` (`name`, `guard` from the header, `file` with `.json`; non-JSON skipped) and `GET /api/live/{file}` (404 when absent or outside `<reports>/live/`).
- `scripts/live/csdemo-d1.json`: the spike's two turns.

## Before / after

| Behaviour | Before | After |
|---|---|---|
| Unit tests `tests/test_live.py` | collection error, no `bylaw.live` (`.scratch/after/cs3-guard-live/cs3-tests-first.txt`) | 10 passed (`.scratch/after/cs3-guard-live/cs3-tests-green.txt`) |
| Live d1 on Muse, unguarded | no runner | 28 events, 4 checks, `issue_compensation` denied but not enforced, vouchers issued (`.scratch/after/cs3-guard-live/cs3-csdemo-d1.json`) |
| Live d1 on Muse, `--guard` path | no runner | 27 events, `issue_compensation` blocked, agent got the Bylaw text, `vouchers` null (`.scratch/after/cs3-guard-live/cs3-csdemo-d1-guard.json`) |

The live runs used a stand-in RuleSet (`.scratch/cs3-live.py`): CS2's hand RuleSet `bylaw/rulesets/csdemo.json` and `bylaw.env.cs_demo` (for `now`) are not on `bylaw/build` yet, so `python -m bylaw live` itself cannot run yet. These files are therefore not committed to `reports/live/`.

## Tests added

`tests/test_live.py`, offline with a scripted fake model: blocked call not executed and state unchanged, allowed call runs, rules read the trace, install idempotent, event file per mode (check per tool call, order tool_call/bylaw_check/tool_output, handoffs never tool calls, enforced flag, state diffs), every demo agent on the given model with tracing off, the CLI, the d1 script, the API.

## Out of scope / not done

- Switch to `bylaw.env.cs_demo` for `now` and `write_tools` once CS2 merges (`agents_guard._now` already calls `get_domain(name).now`; `live.WRITE_TOOLS` is a copy of the CS-C1 list).
- Committed event files in `reports/live/` (DM2, after CS2).
- The trace records `ok: true` at check time; a tool that then raises is not corrected.
