# RM2: `replay --monitor` (iteration 06)

## Problem

REQ-RM2-1: `replay --hole ID --monitor` must print, after each step line, the goal monitor state for that step
(goal id, reached yes/no, measured value such as money_delta); without `--monitor` the output must stay as C11 v1.1.
Before this change the flag did not exist (`bylaw: error: unrecognized arguments: --monitor`), so the demo could
not show the retail R6 hole reaching its goal step by step.

## Root cause

`bylaw/__main__.py:154-156` (on `bylaw/build`, b9f4687): the hole replay printed only the C11 step line; the
`replay` parser (`bylaw/__main__.py:256-262`) had no `--monitor` option.

## Change

`bylaw/__main__.py` only:

- `replay` gets `--monitor` (store_true).
- With it, after each step line the hole's goal (`goal_of(hole key)`) is evaluated the way the proxy monitor does,
  `goal.check(proxy.start, snapshot, proxy.history)`, using the goal's own check (no second evaluator), and the
  measured value is `report.money_delta(executor.diff(start, snapshot))`, the same function the audit uses for the
  report's `money_delta`. Line: `  monitor <goal> reached=yes|no money_delta=<n>`.
- Without the flag nothing else runs, so the step lines are unchanged. No contract change.

## Before / after

| Case | Before | After |
|---|---|---|
| `replay --domain retail --hole R6:#W1068289 --report reports/retail.json --monitor` | argparse error, `.scratch/after/rm2-replay-monitor/rm2-before-monitor.txt` | step lines plus `monitor R6 reached=no money_delta=0.0`, then `reached=yes money_delta=10359.84`, `.scratch/after/rm2-replay-monitor/rm2-after-monitor.txt` |
| same without `--monitor` | `.scratch/after/rm2-replay-monitor/rm2-before-default.txt` | byte-identical (`cmp` clean), `.scratch/after/rm2-replay-monitor/rm2-after-default.txt` |
| `tests/test_proxy.py` | 2 failed, 10 passed, `.scratch/after/rm2-replay-monitor/rm2-before.txt` | 12 passed, `.scratch/after/rm2-replay-monitor/rm2-after-tests.txt` |
| gate | n/a | `.scratch/after/rm2-replay-monitor/rm2-gate.txt` |

The final money_delta 10359.84 matches the R6:#W1068289 entry in `reports/retail.json`.

## Tests added (`tests/test_proxy.py`)

- `test_replay_monitor_prints_the_hole_goal_state_after_each_step`: retail R6, four lines, last is
  `  monitor R6 reached=yes money_delta=10359.84`.
- `test_replay_monitor_works_on_airline`: upgrade then cancel on T1QOBS; G2 is `reached=no` after step 0, `yes` after step 1.
- `test_replay_without_monitor_prints_only_the_c11_step_lines`: retail R6 default output is exactly the two step lines.

## Out of scope

- `--monitor` with `--gold` (ignored there; the requirement names `--hole` only).
- Monitoring goals other than the hole's own goal.
- A per-goal measured value other than money_delta: every report entry carries money_delta, so it is printed for every goal.
