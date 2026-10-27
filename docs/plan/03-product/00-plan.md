# 03 — Product: API + web UI (M3)

## Goal of the increment

A person opens the web app, picks a domain, runs an audit (or opens the latest one), sees the proven holes, replays a hole's trace step by step with the policy line each rule quotes, reads Muse's amendment and its backtest, and ratifies it. Ratified amendments are stored and become the RuleSet the M4 proxy enforces. Muse's role is visible: which phase used Muse, tokens and calls, and the bench of Muse-guided vs blind search.

## Starts from

Iterations 01 and 02 (engine, report C4, amend C7, backtest C8, bench C5). The approved UI1 prototype in `web/` (fixture data).

## Items

| Id | Item | Type | Weight | Agent | Depends on | Requirements |
|---|---|---|---|---|---|---|
| GA1 | Gold adjudication (Class B) + search fixes | feature | full | builder | v1.7 | REQ-GA1-1..3 |
| SR1 | Retail BFS search | feature | full | builder | C6 | REQ-SR1-1 |
| DP1 | Container image + docker compose, proven locally; VPS deploy only with user go-ahead | ops | full | devops | C9 | — |
| RM1 | Submission README (measured figures only) | docs | light | assistant | close notes | — |
| AP1 | FastAPI app `bylaw/api.py` + demo report store + ratify store | feature | full | builder | C9, C10 | REQ-AP1-1..5 |
| UI2 | Wire the prototype to the API; Playwright smoke test | view | full | designer | C9, UI1 | REQ-UI2-1..3 |
| DM1 | Demo reports: live audit + amend + bench committed under `reports/` | data | light | assistant | PR1, AM1 merged | REQ-DM1-1 |
| TA4 | Acceptance tests 03 (API) | tests | full | test-author | contracts | REQ-AP1-* |

## Waves

AP1, UI2 and TA4 in parallel against the contracts (UI2 may run against a local AP1 branch or the fixture until AP1 merges). DM1 after PR1 and AM1 merge.

## Out of scope

Auth, multi-user, deploy (M6), MCP enforcement (iteration 04).
