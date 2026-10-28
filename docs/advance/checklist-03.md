# Checklist 03 — Product: API + web UI

Plan: `docs/plan/03-product/00-plan.md`. Progress: 13 / 15.

- [x] **AP1** FastAPI app + report and ratify stores — builder — PR #11
- [x] **UI2** Prototype wired to API + Playwright smoke — designer — PR #15
- [ ] **DM1** Demo reports committed — assistant — PR #
- [x] **TA4** Acceptance tests 03 — test-author — PR #18 (brought in with SR1)
- [x] **GA1** Gold adjudication (Class B) + search fixes — builder — PR #16
- [x] **SR1** Retail BFS search — builder — PR #18
- [x] **DP1** Container image + compose (no deploy) — devops — PR #19
- [x] **RM1** Submission README — assistant — PR #17
- [x] **UI3** Sidebar collapse toggle (Gemini/Lovable style), approved by the user — designer — PR #20
- [x] **UI4** Frontend redesign (legal-record, dark+light) — designer — PR #22
- [x] **DP2** Deploy hardening before VPS: bind 127.0.0.1:8000 behind auth reverse proxy (API has no auth; open port lets anyone spend Muse budget or ratify), `**/.env*` in .dockerignore, create `reports/` — devops — PR #24
- [x] **FX2** Finding keys for G7 (certificate sent twice): DM1 Muse audit gave 121 Class C entries, one per certificate; key them per user so the report is not flooded — builder — after GA1/SR1/FX1 merge — PR #28
- [x] **FX1** Loud Muse fallback, bench model, BYLAW_EFFORT — builder — PR #26
- [x] **FX3** G7 key from `send_certificate` steps only: a chain whose earlier step names another user took that user's key and could merge with their finding — builder — PR #31
- [x] **UI5** View fixes inside UI4: bfs-fallback shown offline, Class C grouped by goal, bench copy follows `model`, peak context tokens — designer — PR #30
