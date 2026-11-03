# RO1: read-only switch for the public deploy

## Problem

bylaw goes public at bylaw.martinhdeez.com. Any visitor could `POST /api/holes/{key}/ratify` and change the rules the proxy enforces, or `POST /api/audits` and write a new report that becomes the latest one shown. The user decided the site is public, so writes must be off there.

## Root cause

No route checked any deploy mode before writing:

- `bylaw/api.py:224` (old) `ratify` writes the ratified store through `ratified.ratify`.
- `bylaw/api.py:170` (old) `start_audit` starts `_run`, which writes `<cache>/<domain>-<id>.json` (`bylaw/api.py:144` old).

No other route writes. Live sessions do not touch the store or reports, and `GET /api/live/session/{sid}/export` returns the event file as JSON without writing it (`bylaw/live.py:211`).

## Change

- `BYLAW_READONLY=1`: `ratify` and `start_audit` answer `403 {"detail": "read-only deployment"}` before doing anything (`_writable()` in `bylaw/api.py`).
- `GET /api/config` returns `{"readonly": bool}`. Not added to `/api/live/status`: `tests/acceptance/test_06_lv1_live_session.py::test_REQ_VZ3_C6_status_fields` asserts that payload exactly.
- web: the Amendment screen reads `/api/config`; when read-only the Ratify button is disabled and labelled "Ratify is off on the public demo". The e2e mock serves `/api/config` with a `readonly` option.
- `docs/deploy.md`: the `BYLAW_READONLY` row in the env table.

## Before / after

| Check | Before | After |
|---|---|---|
| Unit: ratify, audits 403 with the flag; reads and live keep working; without the flag ratify writes | 4 failed (`.scratch/after/ro1-readonly/before-unit.txt`) | 40 passed with test_api and test_lv1 (`.scratch/after/ro1-readonly/after-unit.txt`) |
| e2e: Ratify disabled and labelled in read-only | 1 failed (`.scratch/after/ro1-readonly/before-e2e.txt`) | 13 passed with ra2 and ui4 (`.scratch/after/ro1-readonly/after-e2e.txt`) |

## Tests added

- `tests/test_ro1_readonly.py`
- `web/e2e/ro1.spec.ts`

## Out of scope

- No auth or rate limit on the remaining routes; live sessions keep their own token cap.
- `.env.example` not changed (the brief named only `docs/deploy.md`).
