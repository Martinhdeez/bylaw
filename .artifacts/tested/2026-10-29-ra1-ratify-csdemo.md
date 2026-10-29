# RA1: the API accepts the csdemo domain, so Ratify works on it

Item RA1 of iteration 06. Branch `fix/ra1-ratify-csdemo` from `bylaw/build` at 41dbfc9. Evidence files are under `.scratch/after/ra1-ratify-csdemo/`, which is gitignored and so not committed.

## Problem

`POST /api/holes/{key}/ratify?domain=csdemo` returned 422 (`Input should be 'airline' or 'retail'`). DM2 had to call `bylaw.ratified.ratify("csdemo", hole)` directly. The video needs the Ratify click to work on csdemo. This breaks C9/C10: the ratified store is keyed by any domain, and csdemo is a registered domain plug-in (`bylaw/domain.py:39`), but the HTTP layer refused it.

## Root cause

`bylaw/api.py:24` (at 41dbfc9): `Domain = Literal["airline", "retail"]`, a hand list next to the registry `MODULES` in `bylaw/domain.py:39`. Every route that takes `domain` validated against it.

## Change

`bylaw/api.py:24`: `Domain = Literal[tuple(MODULES)]`. The query/body type now comes from the domain registry, so every registered plug-in (airline, retail, csdemo) is accepted. Unknown domains (`bank`) are still 422.

`DOMAINS` (the list `/api/domains` returns) stays `["airline", "retail"]`: `tests/acceptance/test_iter03_api.py:132` pins that exact list, and the web's Audit screen renders it.

### Routes checked

| Route | csdemo after the change | How checked |
|---|---|---|
| `GET /api/policy` | 200, the csdemo policy lines | new unit test |
| `GET /api/reports/latest` | 200, the stored report | new unit test |
| `GET /api/holes/{key}` | 200, the hole | new unit test |
| `POST /api/holes/{key}/ratify` | 200, entry written to `$BYLAW_RATIFIED_DIR/csdemo.json` | new unit test |
| `GET /api/ratified` | 200, hand `bylaw/rulesets/csdemo.json` plus ratified patches | new unit test |
| `POST /api/audits` (blind, `use_llm=false`) | 202, job ends `done`, report becomes latest | new unit test; probe at budget 30: 3 Class A holes (`probe-audit.txt`) |
| `POST /api/audits` with `use_llm=true, amend=true` | not run (needs Muse and the key) | not measured |
| `GET /api/bench` | 404 `no bench for csdemo`: no `reports/csdemo.bench.json` exists. A clear 4xx, not a crash | new unit test, `probe-audit.txt` |
| `GET /api/domains` | unchanged, does not list csdemo (acceptance-pinned) | acceptance test |

No route needed csdemo-specific handling.

## Before / after

| Check | Before (41dbfc9) | After |
|---|---|---|
| `POST ratify?domain=csdemo` on `D2:LL0EZ6` from `reports/csdemo.json` | 422, test fails: `before-test-fails.txt` | 200, test passes: `after-csdemo-tests.txt` |
| csdemo blind audit through the API | 422 (same `Domain` type) | `done`, 3 holes at budget 30: `probe-audit.txt` |
| `tests/test_api.py` + `tests/acceptance/test_iter03_api.py` | | 40 passed, 1 skipped (web/dist not built): `after-api-tests.txt` |

## Tests added

In `tests/test_api.py`:
- `test_csdemo_hole_from_the_committed_report_is_ratified_into_the_store`: copies the committed `reports/csdemo.json` into a tmp reports dir, ratifies `D2:LL0EZ6` into a tmp ratified dir, and checks report, hole, policy, the stored entry and the effective ruleset. Asserts the committed `ratified/csdemo.json` is byte-identical afterwards.
- `test_csdemo_audit_runs_and_becomes_latest_and_csdemo_bench_is_404`.

## Designer ask

The Ratify button cannot reach csdemo from the web app. `web/src/api.ts:4` has `type Domain = "airline" | "retail"` and `web/src/api.ts:5` has `DOMAINS = ["airline", "retail"]`. `web/src/main.tsx:58` only treats a hash segment in `DOMAINS` as a domain, so `#/csdemo/holes/<key>/amendment` falls back to airline. The API side is ready: every route above takes `domain=csdemo`. The designer needs to add `csdemo` to the web's domain type and route list, and decide whether it shows in the Audit domain picker.

## Out of scope

- `/api/domains` still lists only airline and retail (acceptance-pinned; changing it is a contract change).
- Muse audits and amends on csdemo through the API were not run (need the key).
- No web change.
