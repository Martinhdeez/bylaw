# CS3: agents guard and live runner

Item CS3 of iteration 06 (REQ-CS3-1..3, contracts CS-C2, CS-C3, clarifications v1.2). Branch `feat/cs3-guard-live`.

## Problem

The demo agents run any tool call the model proposes. REQ-CS3-1 asks that a call the effective RuleSet forbids is not executed and that the agent reads `Bylaw: blocked <tool>: <rule_id> <policy_ref>`. REQ-CS3-2 and REQ-CS3-3 ask for a recorded live conversation (event file) and an API to serve it.

## Root cause

Not a defect: nothing existed. The interception point is `FunctionTool.tool_input_guardrails` (`.venv/.../agents/run_internal/tool_execution.py:2041`, guardrails run before `on_tool_start`; spike section 4).

## Change

- `bylaw/proxy/agents_guard.py:52` `install(agents, domain_name="csdemo", ruleset=None, log=None)`: one `ToolInputGuardrail` named `bylaw` per FunctionTool; a second install replaces it (idempotent). The check (`:25`) loads, on its first call, `ruleset or default_ruleset(domain_name)` (the C10 effective RuleSet) and `get_domain(domain_name).now`, reads `data.context.context.state`, builds the CS-C1 snapshot (`:14`) with the guard's own trace (allowed calls only, `ok: true`, keys from `"0"`), runs `rules.check` and names the first failing verdict in RuleSet order (`:33`). A private `_install(..., enforce=False)` records verdicts without blocking; the unguarded live run uses it.
- `bylaw/live.py`: `run(script, guard, model, ruleset=None)` sets every demo agent, including the relevance and jailbreak guardrail agents, to `model` with reasoning effort low, disables tracing, and plays the turns with `Runner.run_streamed`. Stream events map to `user`, `agent_message`, `handoff`, `tool_call`, `bylaw_check` (from the guard log, `enforced` = `--guard`), `tool_output`, and `state` (C4 diff of the session after each of the domain's `write_tools`; `{}` for a blocked call). Header `model` is `MODEL` (default `muse-spark-1.3`); `final_state` is `state.model_dump(mode="json")`. `muse_model()` builds `OpenAIChatCompletionsModel` from the `bylaw.llm` client settings.
- `bylaw/__main__.py`: `live --domain csdemo --script FILE [--guard] -o OUT`.
- `bylaw/api.py`: `GET /api/live` (`name`, `guard` from the header, `file` with `.json`; non-JSON skipped) and `GET /api/live/{file}` (404 when absent or outside `<reports>/live/`).
- `scripts/live/csdemo-d1.json`: the spike's two turns.

## Before / after

| Behaviour | Before | After |
|---|---|---|
| Unit tests `tests/test_live.py` | collection error, no `bylaw.live` (`.scratch/after/cs3-guard-live/cs3-tests-first.txt`) | 11 passed (`.scratch/after/cs3-guard-live/cs3-tests-green.txt`) |
| Acceptance `tests/acceptance/test_06_guard_live.py` (branch `test/06-guard-live`, run from a copy, offline) | not run | 12 passed, 1 deselected (the `live` one) (`.scratch/after/cs3-guard-live/cs3-tests-green.txt`) |
| Unit tests with enforcement disabled (mutation) | — | 4 failed, 7 passed (`.scratch/after/cs3-guard-live/cs3-mutation-no-enforce.txt`) |
| `python -m bylaw live --domain csdemo --script scripts/live/csdemo-d1.json --guard` on Muse, `BYLAW_EFFORT=low`, real hand RuleSet, empty ratified store | stand-in domain, no CLI run | 28 events, 4 checks, 0 denied; `issue_compensation` allowed by the hand RuleSet (reason names a missed connection, so `R-comp-delay` holds); vouchers issued on LL0EZ6 / FLT-123, an on-time booking: D1 reached through the guard (`.scratch/after/cs3-guard-live/cs3-csdemo-d1-guard.json`, `cs3-csdemo-d1-guard-summary.txt`) |

The guard did not block D1 because the hand RuleSet does not forbid it; that is the hole CS2's audit is meant to find and an amendment to close. The offline tests prove the block with a rule that denies it, ratified in a private store (`BYLAW_RATIFIED_DIR`), so the guard reads it through `default_ruleset` / `effective_ruleset`; one test also blocks with the hand RuleSet's own `R-comp-delay` (a reason with no delay). Evidence files under `.scratch/` are not committed (gitignored).

## Tests added

`tests/test_live.py`, offline with a scripted fake model, on the real `csdemo` domain and its effective RuleSet: blocked call not executed and state unchanged (ratified test rule, and the hand RuleSet's own `R-comp-delay`), allowed call runs, rules read the trace, install idempotent, event file per mode (check per tool call, order tool_call/bylaw_check/tool_output, handoffs never tool calls, enforced flag, state diffs), every demo agent on the given model with tracing off, the CLI, the d1 script, the API.

## Out of scope / not done

- The unguarded live run was not repeated on the real domain (one live run, `--guard` only).
- Committed event files in `reports/live/` (DM2).
- The trace records `ok: true` at check time; a tool that then raises is not corrected.
