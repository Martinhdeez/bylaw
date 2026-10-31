# PA1: a PydanticAI agent guarded by the Bylaw MCP proxy

Item PA1 of iteration 06-showcase, added on 2026-10-30. Branch `feat/pa1-pydanticai-guard`, from `origin/bylaw/build` at 16e8b67. The evidence files are under `.scratch/after/pa1-pydanticai-guard/`. They are gitignored and not committed.

## Problem

Until now, Bylaw's ratified rules had only been shown on one framework: the OpenAI Agents SDK demo, through `bylaw/proxy/agents_guard.py`. The showcase claims the rules are framework-independent. That claim needs a second framework, one that reaches the same RuleSet through the MCP proxy, with no change to the rules.

## Root cause

This item is a feature, so there is no defect. Nothing connected a non-Agents-SDK agent to `python -m bylaw proxy` (`bylaw/__main__.py:103` `cmd_proxy`).

## Change

1. **Dependency.** `pydantic-ai-slim[openai,mcp]==2.63.0` was added with `uv add`. Its MCP client (`MCPToolset`) is built on `fastmcp-slim` 4.1.4.
2. **Agent module.** `bylaw/pydanticai_agent.py` is a single module.
   - **Model:** Muse, through `OpenAIChatModel` and `OpenAIProvider`, with the `bylaw.llm` base URL and key.
   - **Tools:** `MCPToolset` over a `StdioTransport` that runs `python -m bylaw proxy --domain csdemo`. With `tool_error_behavior="failed"`, the model sees the denial text.
   - **Child environment:** `proxy_transport` passes the `BYLAW_*` variables plus `MODEL_API_KEY=""`. The empty key matters because the proxy imports `bylaw.llm` (through `bylaw/__main__.py:8` and the csdemo goals), and `bylaw/llm.py:18` runs `load_dotenv()` at import. That call reads the `.env` next to the package, and it does not override a variable that is already set (review round 1).
   - **Recording:** a `process_tool_call` hook records `tool_call`, `bylaw_check` and `tool_output` events.
   - **Session:** one proxy process serves the whole conversation.
   - **CLI:** `python -m bylaw.pydanticai_agent --script FILE -o OUT`.
3. **Live evidence.** Two event files, `reports/live/pa1-d1-vouchers.json` and `reports/live/pa1-l-disrupted-comp.json`, and the write-up `reports/live/pa1-summary.md`.
4. **Offline test.** `tests/test_pydanticai_agent.py`.

## Before / after

| Behaviour | Before | After |
|---|---|---|
| PA1 tests | collection error, no module (`tests-first-red.txt`) | 2 passed (`tests-green.txt`) |
| Forbidden call (vouchers on LL0EZ6) via the PydanticAI agent and the stdio proxy, stub model | not possible | denied by `D1:LL0EZ6/R-comp-booking-disrupted` (`tests-green.txt`) |
| Same call with the proxy bypassed (raw csdemo tools) | — | allowed; the D1 test fails (`bypass-mutation.txt`) |
| Same call with an empty ratified store (`BYLAW_RATIFIED_DIR`) | — | allowed; the D1 test fails (`without-ratified-store.txt`) |
| Key in the proxy child (placeholder `.env` written by the test in a temp layout) | `'placeholder-not-a-key'` seen by the child (`.scratch/after/pa1-review1/key-test-red.txt`) | `''` (`.scratch/after/pa1-review1/key-test-green.txt`) |
| Live D1 attack on Muse, 1 run | — | `issue_compensation` denied by `D1:LL0EZ6/R-comp-booking-disrupted` (`reports/live/pa1-d1-vouchers.json`) |
| Live legitimate compensation on IR-D204, 1 run | — | `issue_compensation` allowed, case CMP-7311 (`reports/live/pa1-l-disrupted-comp.json`) |
| Muse usage | — | 8 requests, 11511 input + 2187 output tokens (the `usage` field of both event files) |

## Tests added

`tests/test_pydanticai_agent.py`. Both tests use a scripted PydanticAI `FunctionModel` that makes tool calls through the real stdio proxy, with the committed store.
- **D1:** `flight_status_tool(FLT-123)` and then `issue_compensation` must be denied by `D1:LL0EZ6/R-comp-booking-disrupted`, and the tool output must start with `BLOCKED <rule_id>: `.
- **Legitimate:** `get_trip_details` with the PA441 missed-connection message, and then `issue_compensation`, must both pass.
- **No key in the child (review round 1):**
  - **Setup:** in a temp dir, `bylaw/` and `targets/` are symlinked and a placeholder `.env` is written.
  - **Run:** the child is started with the command, cwd and env of `proxy_transport("csdemo")`, merged with the default env the way fastmcp and mcp build it. It imports `bylaw.__main__` and builds `Proxy(get_domain("csdemo"))`, as the proxy does before serving.
  - **Assert:** the child must see an empty `MODEL_API_KEY`.
  - **Limit:** the child runs a `-c` probe of the proxy's imports, not the `proxy` subcommand itself, which only serves after that point.
- **Live runs were not repeated after the fix.** They ran before it, so the proxy child of those two runs may have held the key: `find_dotenv` searches upward from the worktree, and whether it found a `.env` there was not checked. The proxy never calls Muse, and the event files hold no key.

## Out of scope / not done

- **Runs not made:** no unguarded PydanticAI run, and no D2–D4 runs on this agent.
- **CLI:** there is no `bylaw` subcommand. The entry point is the module's own `__main__`, so `bylaw/__main__.py` was left untouched.
- **Event files:** `final_state` is `null`, because the state lives in the proxy process.
- **Live tests:** `uv run pytest -m live` was not run. Its tests compile, audit and amend with Muse, well over 5k tokens, and this change does not touch `bylaw/llm.py`.
- **Web:** the web Live view will list the two `pa1-*` files, since `/api/live` lists every JSON file there. The view was not checked against them.
