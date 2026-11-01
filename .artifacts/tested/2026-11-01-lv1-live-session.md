# LV1: live session backend for the VZ3 demo UI

Item LV1 of iteration 06-showcase, 2026-11-01. Branch `feat/lv1-live-session` from `origin/bylaw/build` (00856fd, then merged 6964c7c for contract v1.1). Contract: `docs/plan/06-showcase/vz3-contract.md` v1.1, items C2 to C6. Evidence under `.scratch/after/lv1-live-session/` (gitignored, not committed), except the export of the live smoke, committed as `reports/live/lv1-smoke.json`.

## Problem

The VZ3 UI needs a live conversation on Muse, guard on or off, streamed event by event in the CS-C3 shape (VZ3-C2), with the guard's view on every `bylaw_check` (C3), the demo's own guardrails (C4), the agents list (C5) and public-demo limits (C6). Before this item only replays existed (C1): `live._run` played a whole script in one call.

## Root cause

A feature, no defect. `bylaw/live.py:44` (`_run` at 00856fd) held the state, the current agent and the input items as locals of one loop over `script["turns"]` (`bylaw/live.py:66`), so a single customer turn could not be run, streamed or resumed. `bylaw/api.py:258` served only the recorded files.

## Change

1. **`bylaw/live.py`**
   - `Session`: state, current agent, input items, events, the guard's verdict log. `Session.turn(text)` is an async generator of CS-C3 events for one customer turn; `export(name)` gives the event file. `live._run` / `live.run` now loop over `Session.turn`; same event file shape (no `guardrail` events in files, a tripwire still raises there, as before).
   - VZ3-C3: a `_Log` list subclass enriches each guard log entry at check time (before the tool runs) with `session`, `booking` (`facts.bookings[...]` or `null`), `prior_tools` (allowed calls, or every call when not enforced, as the guard's trace) and `rules_checked`. The guard's own log shape (CS-C2) is unchanged; `bylaw/proxy/agents_guard.py` was not touched.
   - VZ3-C4: guardrail results are read from `run.input_guardrail_results` as they finish; a tripped one is emitted last and ends the turn (items and agent not kept).
   - `Counted`: wraps the session's model and adds every reported usage (streamed and not, so guardrail agents too) to `live.USAGE["tokens"]`.
   - Sessions share the demo's module-level agents, so a per-process asyncio lock runs one turn at a time; each turn re-points the agents at its session's model and guard (the guard object, with its trace, is kept per session). Marked `ponytail:`.
2. **`bylaw/api.py`**: `GET /api/live/status`, `POST /api/live/session`, `POST /api/live/session/{id}/turn` (SSE, `event: done`, `event: error` with a redacted message), `GET /api/live/session/{id}/export`, `GET /api/csdemo/agents`. Limits: 20 sessions (21st evicts the least recently used), 30 min idle expiry, 12 turns, `BYLAW_LIVE_TOKEN_CAP`, `BYLAW_LIVE=0` → 503 before any 404. `/api/domains` unchanged.
3. **`tests/test_lv1_live_session.py`**: 17 offline tests with a stub model.
4. **`reports/live/lv1-smoke.json`**: export of the live guarded D1 session on Muse.

## Before / after

| Behaviour | Before | After |
|---|---|---|
| LV1 tests | 2 failed, 15 errors (`red-before.txt`) | 17 passed (`tests-green.txt`) |
| D1 vouchers, guard on, stub model | no live route (`red-before.txt`) | `issue_compensation` denied `D1:LL0EZ6/...`, `vouchers: null` (`tests-green.txt`) |
| Same with the guard not enforced in `Session` (mutation) | — | guard-on D1 test fails (`mutation-no-enforce.txt`) |
| Live guarded D1 session on Muse, 1 run | — | checks `flight_status_tool`, `get_trip_details`, `faq_lookup_tool` allowed, `issue_compensation` denied by `D1:LL0EZ6/R-comp-booking-disrupted`, vouchers null; 4 guardrail events all passed (`smoke-stream.txt`, `reports/live/lv1-smoke.json`) |
| Muse tokens of that run | — | 20291 (`smoke-status.json`) |
| Existing live tests (`tests/test_live.py`, `tests/acceptance/test_06_guard_live.py`) | pass | pass (`gate.txt`) |

## Tests added

`tests/test_lv1_live_session.py`: create shape; D1 blocked guard on / runs guard off with `enforced` false; C3 fields on a live check and on a `live.run` recording; tripwire ends the turn after its guardrail event; both guardrails report on a pass; model failure is an `error` event without the key and the session works after; 409 on a concurrent turn; 404 unknown and expired; 422 on text length; 429 on the 13th turn; LRU eviction of a 21st session; token cap from reported usage (session and turn 429); status and 503 when disabled; export; agents list.

## Out of scope / not done

- **Concurrency ceiling:** turns of different sessions queue behind one lock (shared agent objects). Per-session agent graphs would remove it.
- **Token cap overshoot:** the cap is checked when a session or turn starts, so one turn can pass it (smoke: 20291 with cap 20000).
- **Status route:** `GET /api/live/status` still answers 200 with `enabled: false` when live is off (it is how the UI learns live is off); every other live route answers 503.
- **Smoke token budget:** a first smoke run (5335 tokens, `smoke-status` overwritten) failed its second turn with `Event loop is closed` because the driver used a `TestClient` without its context (a new loop per request; uvicorn runs one loop). The second run used one loop. Total about 25.6k tokens, over the ~15k budget.
- **`uv run pytest -m live`:** not run (over the ~10k token allowance).
- **Order dependence (pre-existing):** `tests/test_live.py` before `tests/acceptance/test_06_guard_live.py::test_REQ_CS3_1_install_guards_every_function_tool_of_every_demo_agent` fails on 00856fd too (`order-dependence-base.txt`); the default gate order is not affected.
- No change to `targets/cs_demo/ui/`, `web/` or `bylaw/proxy/agents_guard.py`.

## Review round 1 (contract v1.2)

Evidence under `.scratch/after/lv1-review1/`. Merged `origin/bylaw/build` at 3432ed1 (contract v1.2, which makes the status route and the cap-at-turn-start behaviour above contractual). DM5 (PR #51) was not merged yet, so its `customer_text` change to the guard was not exercised together with this one.

| Finding | Fix | Before (d43e3f9) | After |
|---|---|---|---|
| 1. A tripwire did not end the turn: the parallel guardrails let a tool run and change state | live sessions set the demo input guardrails to `run_in_parallel=False` in `Session._apply`; no non-guardrail event is yielded once a guardrail has tripped | the tripwire test, now with a tool call, fails (`red-on-d43e3f9.txt`) | passes (`tests-green.txt`, 17 passed) |
| 2. C5 `input_guardrails` used the function name | `g.get_name()` ("Relevance Guardrail") | agents-list test fails (`red-on-d43e3f9.txt`) | passes (`tests-green.txt`) |
| 3. Verdicts without a tool output leaked into the next turn | `self.log.clear()` at turn start | not tested | one line, no test |
| 4. An aborted turn (error or tripwire) stayed in the export | its events are dropped from `Session.events` | the export assertion of the tripwire test fails (`red-on-d43e3f9.txt`) | passes (`tests-green.txt`) |
| 5. The 409 test hung when the check was removed | both requests in daemon threads with join timeouts; the model gate is released before asserting | — | with the 409 check removed the test fails in 6.5 s (`mutation-no-409.txt`) |

The CLI (`live.run`) keeps parallel guardrails and its event file shape. Live sessions now wait for the two guardrail calls before the agent's first model call. No new Muse run was made.
