# TA3: acceptance tests, iteration 02 (C7, C8)

- Branch: `test/02-amend` (from `bylaw/build` 5b13538)
- Files: `tests/acceptance/test_iter02_backtest.py`, `tests/acceptance/test_iter02_amend.py` (self-contained, no conftest)
- Written blind from `docs/plan/02-amend/requirements.md`, `contracts.md` and the 01 contracts (C1, C2, C4, v1.1). Domain facts come from `.context/tau2-bench` (airline `tasks.json`, `db.json`).

## Tests per requirement

| Req | Tests | Notes |
|---|---|---|
| REQ-BT1-1 | 3 | 43 gold tasks (counted: 50 tasks, ids 0, 10, 26, 28, 31, 34 and 46 have none); tool order per task equals tasks.json; τ² args are a subset of the returned args; task 44 keeps all 19 actions |
| REQ-BT1-2 | 6 | empty RuleSet blocks 0 of 43; reads are checked; first blocking rule (tasks 4 and 44 by a read rule, the rest by a flight rule); in-order execution with the snapshot taken before each call (only task 32 blocked by a cabin rule); fresh env per task (15/16, 17/22 not blocked); step index |
| REQ-BT1-3 | 3 | through the CLI: `baseline_blocked` equals `backtest(hand)["blocked"]`; a no-op amendment costs 0; an "all flight updates forbidden" amendment adds the 12 non-cancel flight-update tasks to the baseline |
| REQ-AM1-1 | 5 (1 live) | `draft(..., llm=scripted)`: C7 shape, valid C2 patch, 1 or 2 sentences, `hole_id` from the hole; an invalid patch or a 4-sentence policy text from the model is never returned |
| REQ-AM1-2 | 5 | precondition (the chain runs under the base RuleSet); `apply` is pure and appends; the patched RuleSet blocks the 3rd step; draft then apply blocks; colliding ids never reach the RuleSet |
| REQ-AM1-3 | 3 | `python -m bylaw amend` with the model scripted by a runner that replaces `bylaw.llm.structured`: amendment, `closes` true for "no flight updates", false for an always-true rule, `backtest` with 43 tasks |

The hole is G1 on reservation Q79V9W (ivan_kim_3844, basic_economy): cabin to economy, flight HAT265 to HAT073, cabin back to basic_economy. All three calls succeed in τ².

## State on `bylaw/build` (5b13538)

25 offline tests error at setup: `bylaw.backtest`, `bylaw.amend`, `bylaw.domain` and `bylaw.rules` do not exist yet. The live test is deselected by default. `harness-trace`: 6 requirements, all named by a test.

## Contract gaps (assumptions the tests make)

- C8 does not type `domain`. The tests pass the C1 Domain object, as in C3 and C6.
- C8 `step` has no base. The tests take the 0-based index into the `load_gold` action list.
- C8 `unknown`: no key for the total, and no per-result flag. Exact blocked sets are asserted only on tasks without `cancel_reservation` (7, 14, 19, 23, 29, 39, 42 may be unknown).
- C7 does not define what the model returns to `draft`. The scripted model answers with the amendment fields, nested under one property only if the request schema nests them.
- C7 `apply` on colliding ids: the tests accept either an error or unique ids.
- C7 CLI offers no offline seam. The CLI tests replace `bylaw.llm.structured` before `python -m bylaw` starts. This fails if `draft` builds its own client.
- REQ-AM1-3 `closes: false` depends on the hand RuleSet leaving G1 open, i.e. on EX1's audit finding it again.
- `blocked_tasks` could list all blocked tasks or only the new ones. The tests accept both.
