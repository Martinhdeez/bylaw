# 03 — Contracts (frozen v1)

## C9 HTTP API — `bylaw/api.py`, FastAPI app object `app`

Run: `uv run uvicorn bylaw.api:app`. All JSON. Domain is `airline` | `retail`.

| Method | Path | Body / query | Response |
|---|---|---|---|
| GET | `/api/domains` | | `["airline", "retail"]` |
| GET | `/api/policy` | `domain` | `{"domain", "lines": [str]}` (1-based line n is `lines[n-1]`) |
| GET | `/api/reports/latest` | `domain` | C4 report (holes may carry C7 `amendment`, `closes`, `backtest`), 404 if none |
| POST | `/api/audits` | `{"domain", "use_llm": bool, "budget": int, "amend": bool}` | `{"id": str}` (202) |
| GET | `/api/audits/{id}` | | `{"id", "domain", "status": "running"|"done"|"error", "report": C4|null, "error": str|null}` |
| GET | `/api/audits/{id}/events` | | `text/event-stream`; each `data:` is an event (below). Late subscribers get all past events first. |
| GET | `/api/holes/{key}` | `domain` | the hole object from the latest report (`key` per C4 v1.2, e.g. `G1:T1QOBS`), 404 if absent |
| POST | `/api/holes/{key}/ratify` | `domain` | `{"ratified": true, "amendment_id", "rule_ids": [str]}`; 409 if the hole has no amendment |
| GET | `/api/ratified` | `domain` | `{"domain", "amendments": [C7 amendment + "hole_key", "ratified_at"], "ruleset": C2}` |
| GET | `/api/bench` | `domain` | C5 v1.2 bench JSON, 404 if none |
| GET | `/` and static | | built `web/dist` |

**Progress event:** `{"phase": "compile"|"search"|"verify"|"amend"|"backtest"|"done"|"error", "message": str, "muse": bool, "tokens": int, "llm_calls": int, "tool_calls": int, "holes": int, "t": float}` — counters are cumulative for the audit; `muse` is true when the phase uses Muse Spark.

**Report store:** `reports/<domain>.json` (committed demo reports, DM1) is the initial latest; audits run through the API write `.cache/reports/<domain>-<id>.json` and become latest for the server's lifetime (newest wins). Bench: `reports/<domain>.bench.json`.

## C10 Ratified store — `bylaw/ratified/<domain>.json`

```json
{"domain": "airline", "amendments": [{"id": "A1", "hole_key": "G1:T1QOBS", "policy_text": "", "rule_patch": [C2 tool_rule], "rationale": "", "ratified_at": "ISO-8601"}]}
```

- `bylaw.ratified.load(domain) -> dict` (empty amendments if the file is missing), `bylaw.ratified.ratify(domain, hole) -> dict`, `bylaw.ratified.effective_ruleset(domain) -> C2` = the domain's hand RuleSet with every ratified `rule_patch` applied via `bylaw.amend.apply` in order.
- The path can be overridden by env `BYLAW_RATIFIED_DIR` (tests use a tmp dir).
