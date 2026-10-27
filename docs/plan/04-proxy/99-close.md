# 04 — Close

Integration branch at `1d1b763`; gate green on 2026-10-27 (reviewer of PR #13, 363 passed; acceptance 04 included since PR #11).

## Delivered

| Id | Item | Pull request | Change note |
|---|---|---|---|
| PX1 | MCP proxy (stdio), goal monitor, `proxy` and `replay` CLI | #10 | `.artifacts/tested/2026-10-27-px1-proxy.md` |
| TA5 | Acceptance tests 04 (24 tests) | brought in with #11 | — |

## Measured

All from one run each, PX1 review on the merged tree unless noted.

| What | Value | Command | Output |
|---|---|---|---|
| Airline gold through the proxy, nothing ratified | blocked: 0/43 (unknown: 1) | `python -m bylaw replay --domain airline --gold` | PX1 review |
| Retail gold through the proxy, nothing ratified | blocked: 2/112 (tasks 64, 105; τ² also rejects those actions) | `python -m bylaw replay --domain retail --gold` | PX1 `replay-gold-retail.txt` |
| H1-type hole `G1:1ERWZ8` with its goal monitored | step 1 BLOCKED by G1 (step 0 ALLOWED) | `measure.py` (monitor_goals=[G1]) | PX1 `replay-holes.txt` |
| Same hole with a hand-written stand-in amendment | step 0 BLOCKED by the rule | `measure.py` | PX1 `replay-holes.txt` |

## Not measured

- The full path with a **Muse-drafted amendment ratified through the API** and then replayed through the proxy. AM1 and AP1 landed after PX1; this is part of DM1.
- MCP latency per call.

## Parked

- Networked transports, multi-session server, auth.

## Findings for the next iteration

- A G1 amendment that blocks the chain at step 0 also blocks gold tasks 7, 17, 22, 32 and 44, because τ² allows upgrading basic economy. This is the Class B trade-off of 01 v1.7.

## Lessons for the harness

See 01 close.

## Open for the user

- None.
