# TA1: acceptance tests, wave 1 (C1 to C3)

- Branch: `test/01-wave1` (from `bylaw/build`)
- Files: `tests/acceptance/conftest.py`, `test_wave1_rules.py`, `test_wave1_compiler.py`, `test_wave1_retail.py`
- Written blind from `docs/plan/01-engine/requirements.md` and `contracts.md`. Fixture facts come from the τ² DBs in `.context/tau2-bench`.

## Tests per requirement

| Req | Tests | Notes |
|---|---|---|
| REQ-EN1-1 | 7 | synthetic RuleSet on the airline snapshot; uses args, db, now, hours_between, res and user |
| REQ-EN1-2 | 29 | 8 whitelisted expressions validate. 12 forbidden ones raise RuleError: `__import__`, dunders, `open`, lambda, eval, exec, getattr, unknown name, `db.pop`, walrus. 8 side-effect probes (4 via validate, 4 via check) confirm nothing runs. |
| REQ-EN1-3 | 8 | reservation 34XLFT (basic_economy, insurance "no", created 2024-05-12T02:00:41): rejected at +25h, +24h01m and domain.now; allowed at +1h, +23h, +23h59m |
| REQ-CP1-1 | 1 | live |
| REQ-CP1-2 | 7 | hand vs hand = 1.0 (airline, retail); equivalent rewrites = 1.0; empty or wrong-tool rules = 0.0; synthetic case = 0.5 |
| REQ-CP1-3 | 1 | live |
| REQ-RT1-1 | 3 | write in one env leaves other and new envs untouched; snapshots are copies |
| REQ-RT1-2 | 2 | ids `R\d+`, class A/C, policy_ref quoted from the policy text; every goal false on the untouched DB |
| REQ-RT1-3 | 2 | retail.json validates and names only retail tools; validate rejects a ruleset with no tool_rules |

## State on `bylaw/build` (6dbd9e7)

All 58 offline tests error at setup: `bylaw.rules`, `bylaw.domain` and `bylaw.compiler` do not exist yet. The 2 live tests are deselected by default.

## Contract gaps

- REQ-CP1-1 and CP1-3 can only run live. C3 gives no offline seam for a scripted model, and the `bylaw.llm.structured` signature is not in the contracts.
- REQ-EN1-3: the cancellation reason is not an argument of τ² `cancel_reservation`, and C2 does not say where it goes. The tests pass it as `args["reason"] = "change of plan"`.
- C1 does not specify the snapshot shape. The tests assume the τ² DB dump (`reservations`, `users` keyed by id).
