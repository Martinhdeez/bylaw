# 03 — Requirements

| Id | Requirement | Checked through |
|---|---|---|
| REQ-AP1-1 | `GET /api/domains` lists `airline` and `retail`; `GET /api/policy?domain=D` returns the policy text as numbered lines. | HTTP (FastAPI TestClient) |
| REQ-AP1-2 | `GET /api/reports/latest?domain=D` returns the latest stored report for D (C4, with C7 amendment fields when present), or 404 when none exists. | HTTP |
| REQ-AP1-3 | `POST /api/audits` starts an audit in the background and returns an id; `GET /api/audits/{id}/events` streams progress events (C9) ending in `done` or `error`; on `done` the report is stored and becomes the latest for its domain. With `use_llm=false` it runs fully offline. | HTTP + SSE |
| REQ-AP1-4 | `POST /api/holes/{key}/ratify?domain=D` appends that hole's amendment rule patch to the ratified store (C10); ratifying twice is idempotent; `GET /api/ratified?domain=D` returns the effective RuleSet (base + ratified patches) and the list of ratified amendments. | HTTP + `bylaw/ratified/<domain>.json` |
| REQ-AP1-5 | `GET /api/bench?domain=D` returns the stored bench JSON (C5 v1.2) or 404. The built web app is served at `/`. | HTTP |
| REQ-UI2-1 | Every screen of the prototype reads from the API instead of fixtures; no fixture import remains in production screens. | code + Playwright |
| REQ-UI2-2 | Playwright smoke: open `/`, run an offline audit on airline, open the first Class A hole, step the trace replay, open its amendment, ratify, see the ratified state. | `web/e2e/smoke.spec.ts` |
| REQ-UI2-3 | Screenshots of each screen at 1440 and 390 width are saved to `.artifacts/reports/`. | files |
| REQ-DM1-1 | `reports/airline.json`, `reports/retail.json` (audit with Muse + amendments + backtest) and `reports/airline.bench.json` are committed, each naming the commit and model that produced it. | files + JSON schema |
