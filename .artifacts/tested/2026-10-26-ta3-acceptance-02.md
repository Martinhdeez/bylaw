# TA3: acceptance tests, iteration 02 (C7, C8)

- Branch: `test/02-amend` (rebased on `bylaw/build` 5e2dd54, contracts 02 v1.1)
- Files: `tests/acceptance/test_iter02_backtest.py`, `tests/acceptance/test_iter02_amend.py` (self-contained)
- Written blind from `docs/plan/02-amend/requirements.md`, `contracts.md` v1.1 and the 01 contracts (C1, C2, C4). Domain facts come from `.context/tau2-bench` (airline `tasks.json`, `db.json`) and `bylaw/rulesets/airline.json`.

## Tests per requirement

| Req | Tests | Notes |
|---|---|---|
| REQ-BT1-1 | 3 | 43 gold tasks (I counted: tasks 0, 10, 26, 28, 31, 34 and 46 have none). Tool order per task matches tasks.json. Every τ² argument is present. Task 44 keeps all 19 actions. |
| REQ-BT1-2 | 8 | An empty RuleSet blocks 0 of 43. Reads are checked. The first blocking rule is reported. Actions run in order and are checked on the snapshot before each call: a cabin rule blocks only task 32, at step 4. Each task gets a fresh env. `step` is 0-based, null when not blocked. `unknown` is an int plus a bool per task, and unknown tasks are not blocked. |
| REQ-BT1-3 | 4 | Through the CLI: `baseline_blocked` equals `backtest(hand)["blocked"]`. A no-op amendment costs 0. "No flight updates" blocks exactly the baseline plus the 13 flight-update tasks, minus unknown ones. `blocked_tasks` lists every blocked task. |
| REQ-AM1-1 | 8 (1 live) | Scripted model answers `{policy_text, rule_patch, rationale}`. Checks: the C7 shape, `effort="high"`, `hole_id` from the hole, and one retry, then `ValueError`, for an invalid patch or a 4-sentence text. A valid second answer is returned. `bylaw.llm.structured` is used when `llm=` is absent. |
| REQ-AM1-2 | 5 | `apply` is pure, appends the patch, and raises `ValueError` on an id collision. The patched base RuleSet and the patched hand RuleSet both block step 3 of the hole. Draft then apply also blocks it. |
| REQ-AM1-3 | 3 | `python -m bylaw amend` with `bylaw.llm.structured` replaced: the amendment, `closes` true for "no flight updates" and false for an always-true rule, and a backtest of 43 tasks. |

The hole is G1 (`key` G1:Q79V9W) on reservation Q79V9W (ivan_kim_3844, basic_economy). Its chain: cabin to economy, flight HAT265 to HAT073, cabin back to basic_economy. All three calls succeed in τ², and the hand RuleSet allows all three. The expected backtest values were worked out from a throwaway τ²-only simulation, not from an implementation.

## State on `bylaw/build` (5e2dd54)

All 30 offline tests error at setup: `bylaw.backtest` and `bylaw.amend` do not exist yet. The live test is deselected by default. `harness-trace`: 6 requirements, all named by a test.

## Remaining assumptions

- Among the airline gold tools, only `cancel_reservation` needs a conversation fact. So only the 7 cancel tasks may be `unknown`.
- `closes: false` depends on the re-audit finding the G1 hole again under the hand RuleSet. That depends on EX1. The precondition, that the hand RuleSet allows the chain, is asserted in `test_REQ_AM1_2_patched_hand_ruleset_blocks_the_hole`.
