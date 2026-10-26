# 01 — Engine core (M1), with early starts on M3 views

## Goal of the increment

`uv run python -m bylaw audit --domain airline` compiles the τ² airline policy into a RuleSet, searches chains of allowed tool calls, executes them on fresh DB copies, and writes a hole report in which every Class A hole is proven: every step passes the rules, the forbidden goal holds, and the replays come out 5/5. The same command runs on `--domain retail`. `bylaw bench` measures Muse-guided search against blind BFS.

## Starts from

M0 spike (`spike/holes_by_hand.py`, `bylaw/env/tau2_airline.py`, `bylaw/goals.py`, `bylaw/rules.py`) and `bylaw/llm.py` (merged, 555a8cc). Plan decisions are in `.artifacts/todo/2026-10-26-bylaw-implementation-plan.md`. The user delegated every checkpoint to the orchestrator for this night run, 2026-10-26.

## Items

| Id | Item | Type | Weight | Agent | Depends on | Requirements |
|---|---|---|---|---|---|---|
| CP1 | Policy compiler (Muse → RuleSet JSON) + match rate | feature | full | builder | contracts C2, C3 | REQ-CP1-1..3 |
| RT1 | Retail domain plug-in (env, goals, hand RuleSet) | feature | full | builder | C1, M0 merged | REQ-RT1-1..3 |
| EN1 | Rule checker (safe expression eval) + airline hand RuleSet in JSON | feature | full | builder | M0 merged | REQ-EN1-1..3 |
| EX1 | Executor + verifier + report + `audit` CLI (`--no-llm`) | feature | full | builder | EN1 | REQ-EX1-1..4 |
| PR1 | Proposer: Muse chain proposals + bounded BFS + `bench` | feature | full | builder | EX1, CP1 | REQ-PR1-1..3 |
| TA1 | Acceptance tests wave 1 (C1–C3) | tests | full | test-author | contracts | REQ-CP1, RT1, EN1 |
| TA2 | Acceptance tests wave 2 (C4–C6) | tests | full | test-author | contracts | REQ-EX1, PR1 |
| UI1 | Web UI prototype (report, hole page, amendment, ratify) | view | full | designer | C4 | M3 early start |

## Waves

- Wave 1 (now): CP1, TA1, UI1 prototype. RT1 and EN1 start as soon as M0 is merged.
- Wave 2: EX1 and TA2.
- Wave 3: PR1.

## Out of scope

Amendments and backtest (M2), FastAPI and the UI implementation (M3), MCP proxy (M4), deploy.

## Open decisions for the user

None. Delegated: the orchestrator approves the plan and the UI1 prototype against the video style (dark, Archivo/JetBrains Mono, #ff4d2e/#2be3a0, N3 logo, Lucide icons).
