# VZ3 contract: live chat for the real demo UI (v1.1, frozen)

Status: v1.0, frozen 2026-11-01 after the user approved the VZ3 prototype (branch `view/vz3-real-ui`). A change is a new version, announced to builder, test author and designer. The builder owns `bylaw/`; the designer owns `targets/cs_demo/ui/` and `web/`.

What the UI needs that does not exist yet: a live conversation on Muse with the guard on or off, streamed event by event in the CS-C3 event shape, and a few extra fields on `bylaw_check` so the rail's plain-language narration comes from the backend instead of a table copied into the UI.

## Changelog

- v1.1 (2026-11-01): clarifications from the blind test author, no behaviour removed. Text-length refusal is `422`. A 21st session evicts the least recently used one (its next turn gets `404`). The live session reads the model endpoint the same way `bylaw live` does (`MODEL_BASE_URL`, `MODEL`). `booking` holds the CS-C1 v1.5 facts entry (`flights`, `on_time`); `confirmation_number` in the example below is not required. Token cap counts every Muse request of the session, guardrail agents included. With live disabled, every live route answers `503` before any `404`. After a guardrail tripwire, only further `guardrail` events may precede `done`.

## VZ3-C1 Replays (exists, unchanged)

- `GET /api/live` and `GET /api/live/{file}` (CS-C3). The UI maps its four buttons to these files:

| Button | Guard off | Guard on |
|---|---|---|
| Vouchers on an on-time flight (D1) | `dm3-d1-vouchers.json` | `dm3-d1-vouchers-guard.json` |
| Someone else's seat (D2) | `dm3-d2-other-seat.json` | `dm3-d2-other-seat-guard.json` |
| Cancel, then claim compensation (D4) | `dm3-d4-cancel-then-comp.json` | `dm3-d4-cancel-then-comp-guard.json` |
| A real missed connection (legit) | `dm3-l-disrupted-comp.json` | `dm3-l-disrupted-comp-guard.json` |

- The UI paces the replay from each event's `t` (gaps capped at 2.6 s, plus a 2.2 s hold after a denied check).

## VZ3-C2 Live session

Reuse `bylaw/live.py`: split `_run` so one customer turn is an async generator of CS-C3 events over a session that keeps `state`, the current agent and the input items between turns.

- `POST /api/live/session` body `{"guard": bool}` → `201 {"session": "<id>", "guard": bool, "model": "<MODEL>", "current_agent": "Triage Agent", "context": <state.model_dump(mode="json")>}`.
  - Fresh `create_initial_context()`; the effective RuleSet for `csdemo` (hand rules plus `ratified/csdemo.json`); `agents_guard._install(..., enforce=guard)`, as `live.run` does.
  - Guard on/off is fixed per session. The UI's toggle starts a new session and clears the chat (same as switching a replay file).
- `POST /api/live/session/{id}/turn` body `{"text": str}` (1..2000 chars) → `200 text/event-stream`:
  - one SSE message per CS-C3 event, `data: <json>`, same objects as an event file's `events[]` (`t` counted from the session start);
  - then `event: done` with `data: {"current_agent": str, "context": <state dump>}`;
  - on a model or tool failure, `event: error` with `data: {"message": str}` (no key, no stack trace), then the stream closes; the session stays usable.
  - `409` while a turn of the same session is running; `404` for an unknown or expired session.
- Sessions live in memory, at most 20, idle expiry 30 minutes. Muse calls stay server-side through `bylaw.llm` (key from `.env`); nothing goes to OpenAI.
- Optional, `GET /api/live/session/{id}/export` → the session as an event file (`name: "live-<id>"`), so a good live take can be saved as a replay.

## VZ3-C3 Extra fields on `bylaw_check` (backward compatible)

Added to every `bylaw_check` event, live and in event files recorded from now on. Old files without them still replay; the UI then falls back to its own table.

```json
{"type": "bylaw_check", "tool": "issue_compensation", "allowed": false, "enforced": true,
 "rule_id": "D1:LL0EZ6/R-comp-booking-disrupted", "policy_ref": "...",
 "args": {"reason": "..."},
 "session": {"passenger_name": "Taylor Lee", "confirmation_number": "LL0EZ6", "flight_number": "FLT-123", "itinerary": [...]},
 "booking": {"confirmation_number": "LL0EZ6", "on_time": true, "flights": [{"flight_number": "FLT-123", "status": "On time and operating as scheduled", "on_time": true}]},
 "prior_tools": ["flight_status_tool", "faq_lookup_tool"],
 "rules_checked": ["R-comp-delay", "D1:LL0EZ6/R-comp-booking-disrupted", "D4:IR-D204/R-comp-no-self-cancel"]}
```

- `args`: the arguments the guard checked (today the UI pairs the check with the preceding `tool_call`).
- `session`: the session fields as the guard saw them, before the call.
- `booking`: `facts.bookings[session.confirmation_number]` (CS-C1 v1.5), or `null` when that booking has no record.
- `prior_tools`: tools of the guard's trace so far (allowed calls only, CS-C2 v1.2 item 4).
- `rules_checked`: ids of every rule on this tool in the effective RuleSet, in order.

## VZ3-C4 Demo guardrails (required in v1.0)

The demo's own Relevance and Jailbreak guardrails run on Muse too. When one runs, emit `{"type": "guardrail", "name": "relevance_guardrail" | "jailbreak_guardrail", "passed": bool, "reasoning": str}` so their two cards light up as upstream does. If a tripwire fires, the turn ends after this event, then `done`.

## VZ3-C5 Agents list (required in v1.0)

`GET /api/csdemo/agents` → `_build_agents_list()` shape (`name`, `description`, `handoffs`, `tools`, `input_guardrails`) from `targets.cs_demo.airline.agents`. Today the UI holds a static copy (`lib/agents.ts`).

## VZ3-C6 Limits for a public demo (added in v1.0)

- At most 12 turns per session: the 13th turn returns `429 {"detail": "turn limit"}`.
- A process-wide Muse token cap, `BYLAW_LIVE_TOKEN_CAP` (default 300000 input plus output tokens, counted from the model layer's reported usage). Once reached, `POST /api/live/session` and `/turn` return `429 {"detail": "token cap"}` until restart.
- `BYLAW_LIVE=0` disables the live endpoints (`503 {"detail": "live disabled"}`); replays keep working. Default on.
- `GET /api/live/status` → `{"enabled": bool, "model": str, "tokens_used": int, "token_cap": int, "sessions": int}` so the UI can grey out live typing and offer replays.

## Tests the builder should add

- Offline: a stub model drives one turn of a session; the SSE body parses into CS-C3 events in order `tool_call`, `bylaw_check`, `tool_output`; guard on blocks D1's `issue_compensation` and `final` context keeps `vouchers: null`; guard off lets it run with `enforced: false`.
- 409 on a concurrent turn, 404 after expiry.
- The new `bylaw_check` fields on a recorded run.
