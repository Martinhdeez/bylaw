# BT1: gold-task loader and backtest

## Problem

Nothing measured whether a RuleSet blocks honest customers. Without that, an amendment that closes a hole by forbidding legitimate τ² gold actions looks free. This breaks REQ-BT1-1..3 and C8 (`load_gold`, `backtest`), and AM1's `backtest` field needs C8 to exist.

## Root cause

- `bylaw/backtest.py`: absent on `bylaw/build` at 5e2dd54, so `from bylaw.backtest import ...` fails (`.scratch/after/bt1-backtest/red-test_backtest.txt`).
- `bylaw/__main__.py`: absent, so there was no `python -m bylaw` entry point.

## Change

- `bylaw/backtest.py:31` `load_gold(domain)` reads `tau2/domains/<name>/tasks.json` (under `TAU2_DATA_DIR`, default `.context/tau2-bench/data`). It keeps the tasks that have `evaluation_criteria.actions`, as `{"id", "actions": [{"tool", "args"}], "facts": {"reason"}}`.
- `bylaw/backtest.py:14` `REASON_RULES` and `infer_reason` infer the cancel reason from the user scenario text with keyword regexes, first match wins: `airline cancelled flight`, then `health` (sick, unwell, ill, health), then `weather`, then `change of plan` (changed plans, "cancel the current one and book", mixup). No LLM is used.
- `bylaw/backtest.py:43` `_replay` uses a fresh env per task. Each gold action is run through `rules.check` against the snapshot taken before the call, then executed with `Domain.call`. When `cancel_reservation` has no `reason` in its args, the inferred one is added (C2 v1.1). If none was inferred, the task is `unknown` (not blocked, `step: null`). A block at an earlier step still counts as blocked. The first failing verdict gives `rule_id`, and `step` is its 0-based index (C8 v1.1).
- `bylaw/backtest.py:59` `backtest(domain, ruleset)` returns `{"tasks", "blocked", "unknown", "results": [{"id", "blocked", "rule_id", "step", "unknown"}]}`.
- `bylaw/__main__.py`: a minimal argparse dispatcher, one function per subcommand. `backtest --domain D [--ruleset PATH]` always runs the hand RuleSet `bylaw/rulesets/<D>.json` as the baseline. It prints `tasks, blocked, unknown, baseline_blocked, delta, blocked_tasks (ids), blocking [{id, rule_id, step}], unknown_tasks` (REQ-BT1-3).

## Before / after

| Check | Before (5e2dd54) | After |
|---|---|---|
| `tests/test_backtest.py` | import error, no `bylaw.backtest` (`.scratch/after/bt1-backtest/red-test_backtest.txt`) | 10 passed inside `make check` (`.scratch/after/bt1-backtest/make-check.txt`) |
| Airline gold tasks | not loadable | 43 (`.scratch/after/bt1-backtest/baseline.json`) |
| Airline baseline, hand RuleSet | not measurable | 2 blocked, 1 unknown out of 43 (`.scratch/after/bt1-backtest/baseline.json`) |
| Gold tool calls that error on a fresh env | n/a | 0 (`.scratch/after/bt1-backtest/diagnostics.txt`) |
| Cancel reasons inferred (7 tasks with a cancel) | n/a | 6 inferred, 1 unknown (task 39) (`.scratch/after/bt1-backtest/diagnostics.txt`) |
| Same baseline if health/weather were sent as `"other"` | n/a | 5 blocked; 7, 19 and 29 extra on `R-cancel-ground` (`.scratch/after/bt1-backtest/diagnostics.txt`) |
| Gate `make check` | n/a | 104 passed, web build OK (`.scratch/after/bt1-backtest/make-check.txt`) |

### Baseline findings (rules stricter than τ² gold, not BT1 failures)

| Task | Rule | Step | Note |
|---|---|---|---|
| 15 | `R-flights-not-both` | 0 | The gold changes cabin and flights in one `update_reservation_flights` call. Our rule forbids both at once, a reading the policy does not state explicitly. |
| 16 | `R-flights-not-both` | 0 | Same pattern. |

Unknown: task 39. The user cancels "to give up your seat for someone else", which states none of the policy's reasons.

## Contract ambiguity for the reviewer

C2 v1.1 gives the reason values as "change of plan" | "airline cancelled flight" | "other". The hand RuleSet's `R-cancel-ground` reads `args['reason'] in ['health', 'weather']` for the insurance ground. BT1 emits `health`/`weather`, which the policy names as covered reasons. Emitting `"other"` would block 3 more honest insured cancellations (row above). Either the contract enum or the RuleSet should be made explicit.

## Tests added

`tests/test_backtest.py`:
- Gold loading: 43 airline tasks with ordered (tool, args), and 112 for retail.
- Reason inference: three tasks from their scenario text, a task with no reason, and an airline-cancelled phrase.
- `backtest` on a minimal fake domain run through the real `rules.check`: the check uses the snapshot before the call, each task gets a fresh env, the inferred reason reaches the rule, a missing reason gives `unknown` with `step: null`, and a block before the missing fact still counts as blocked.
- The CLI on the real airline domain: the hand baseline has delta 0, and a patched RuleSet that forbids cancels reports `baseline_blocked` from the hand run and `delta = blocked - baseline > 0`.

## Out of scope

- Retail backtest numbers. `load_gold("retail")` works (112 tasks), but no retail RuleSet or domain is on `bylaw/build` yet (RT1). Retail `cancel_pending_order` already carries its own `reason` arg.
- `send_certificate` facts (`reservation_id`, `complaint`): no gold task uses that tool.
- Rule changes for tasks 15/16 and the reason enum: these belong to EN1/the contracts.

## Review (PR #7)

- Conforms to 01 contracts v1.4: only `change of plan`, `airline cancelled flight`, `health`, `weather` are emitted; an uninferable reason gives `unknown`, never `other`.
- Acceptance `tests/acceptance/test_iter02_backtest.py` (origin/test/02-amend): 11 passed on the combined code, no test changed. The `REQ-BT1-3` tests in `test_iter02_amend.py` need the AM1 `amend` subcommand and stay with AM1.
- Baseline reproduced: airline 43 tasks, 2 blocked (15, 16 on `R-flights-not-both` step 0), 1 unknown (39). These two break the v1.4 rule that the hand RuleSet blocks 0 gold tasks. The rule is wrong, not the tests: the policy allows changing cabin without changing flights, but it does not forbid doing both. The fix is EN2's.
- After RT1 (#5): retail 112 tasks, 2 blocked (64 on `R-exch-1` step 6, 105 on `R-exch-5` step 0), 0 unknown. These are hand-rule findings for EN2/RT1.
