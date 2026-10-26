# EN2: rule evaluation limits, cross-process spike determinism, gold baseline

## Problem

1. Contracts 01 v1.5 (C2 evaluation limits, replacing the v1.3 wording): `check` bounds each rule evaluation by work, not wall-clock. The bound is at most 10^6 comprehension iterations plus elements or characters built, summed over the evaluation. A rule over the budget gives `Verdict(ok=False, error=...)`, `check` must be safe to call from several threads, and `validate` rejects `bytes` constants. In review of PR #4, `len('a' * 100000000000)` and a triple-nested comprehension over `db['reservations']` both passed `validate`, and `check` ran them without limit.
2. The spike determinism test ran twice in one process. Both runs share one hash seed, so the test cannot see set-ordering bugs.
3. Contracts 01 v1.4 (baseline): the hand RuleSet must block 0 of the 43 airline gold tasks. It blocked tasks 15 and 16 at step 0 through `R-flights-not-both`.

## Root cause

- `bylaw/rules.py:125` (5e2dd54): `eval(...)` runs the compiled rule with no size or time bound.
- `tests/test_spike.py:51-56` (5e2dd54): both runs happen in the same process.
- `bylaw/rulesets/airline.json`, rule `R-flights-not-both` (5e2dd54): it denies any call that changes both cabin and flights. The policy only says "Basic economy flights cannot be modified" and "all reservations, including basic economy, can change cabin without changing the flights". So basic economy may change cabin but never flights. Other cabins may change both in one call.

## Change

- `bylaw/rules.py`:
  - Each evaluation gets its own `_Budget` of `BUDGET = 10**6`. It lives in that evaluation's namespace, so threads never share it.
  - After validation, an AST transform wraps every comprehension iterable as `_it(IT)`, which charges 1 per iteration. It also sends `*` and `+` through helpers that charge the length of the sequence they will build, before building it.
  - String `%` is refused, because `'%0999999999d' % 1` builds its result in C.
  - `sum` accepts only a numeric start, because `sum(lists, [])` concatenates in C, out of reach of the `+` helper.
  - `validate` rejects `bytes` constants.
  - Going over the budget gives `Verdict(ok=False, error=...)`.
  - The first PR #8 revision used a `sys.settrace` 50 ms hook. It segfaulted Python 3.12 when the limit fired with several threads running the rule (review), so it is removed.
- `tests/test_spike.py`: the spike runs in three subprocesses with `PYTHONHASHSEED` 1, 4 and 6, and the test asserts one identical output.
- `bylaw/rulesets/airline.json`: `R-flights-not-both` is removed (28 → 27 rules). `R-flights-not-basic` reads the booked cabin, so a basic economy reservation still cannot change flights in the call that changes its cabin. Its `policy_ref` and `note` now quote both policy lines.
- `spike/holes_by_hand.json`: regenerated. The step rule lists no longer name `R-flights-not-both`.

## Before / after

| Check | Before | After |
|---|---|---|
| `'a'*10**9`, `[0]*2*10**6`, concat, `sum(.., [])` | 4 failed: no error returned (`.scratch/after/en2-eval-limits/red-size-bound.txt`) | ok=False with error (`tests/test_rules.py`, gate) |
| Triple-nested comprehension over 2000 reservations | still running at 20 s, killed (`.scratch/after/en2-eval-limits/red-time-bound.txt`) | ok=False with error in 0.04 s (`.scratch/after/en2-review/reviewer-probe-after.txt`) |
| Determinism test with the ordering guards removed | old same-process test passes (`.scratch/after/en2-eval-limits/determinism-mutation.txt`) | new subprocess test fails (same file) |
| 4 threads x triple-nested rule, reviewer probe x5 | settrace version: segfault (review; `.scratch/after/en2-review/red.txt` shows `Fatal Python error: Segmentation fault` in the new concurrency test) | 5/5 runs exit 0, every verdict ok=False with a budget error (`.scratch/after/en2-review/reviewer-probe-after.txt`) |
| `[[0] * 10**6 for a in reservations]` | per-operation bound let each value through (review: 1.4 GB) | ok=False at once, max RSS 19 MB (`.scratch/after/en2-review/reviewer-probe-after.txt`) |
| Nested tests with the comprehension guard removed | hung (review) | fail in 0.18 s (`.scratch/after/en2-review/guard-removed.txt`) |
| Gold tasks blocked by the hand RuleSet (backtest from PR #7) | 2 of 43 (tasks 15, 16; `.scratch/after/en2-gold-baseline/backtest-before.txt`) | 0 of 43 (`.scratch/after/en2-gold-baseline/backtest-after.txt`; with merged `bylaw/backtest.py`: `.scratch/after/en2-review/backtest-after.txt`) |
| New gold-baseline tests on the old rules | 2 failed (`.scratch/after/en2-gold-baseline/red.txt`) | pass (`.scratch/after/en2-eval-limits/make-check.txt`) |
| Spike Class A | H1–H3 (`.scratch/after/en1-rules/spike-output.txt`) | H1–H3, H1 cabin hop still a hole (`.scratch/after/en2-gold-baseline/spike-output.txt`) |

## Tests added

- `tests/test_rules.py::test_rule_over_the_evaluation_budget_gives_a_failing_verdict` (9 cases, on a 200-reservation snapshot so a removed guard fails instead of hanging), `test_rules_within_the_budget_still_evaluate`, `test_the_budget_is_per_evaluation_not_per_process`, `test_concurrent_checks_over_the_budget_all_fail_cleanly` (8 threads) and `test_bytes_constants_are_rejected` (3 cases).
- `tests/test_rules.py::test_basic_economy_may_change_cabin_but_never_flights` and `test_other_cabins_may_change_cabin_and_flights_in_one_call` (gold task 15/16 arguments). The latter replaces `test_cabin_and_flights_in_one_call_is_denied_but_each_alone_is_not`.
- `tests/test_spike.py::test_spike_output_is_deterministic_and_leaves_the_tracked_file_alone`, rewritten to use subprocesses.

## Out of scope

- Gold task 39 counts as "unknown" in the backtest, because `bylaw/backtest.py` (PR #7) infers no cancel reason for it. That belongs to PR #7.
- There is no wall-clock limit (v1.5). Builtins that walk a container in C (`any`, `len`, `in`, `==`, `min` over a list) are not charged, so their cost is linear in the snapshot size and not bounded by the budget.
- Slices are not charged. A slice copies at most the length of a value that already exists.
- Big-integer growth: without `**`, an expression can only multiply as many times as it has `*` operators.
- The hash seeds 1, 4 and 6 were chosen because they give three different outputs under the mutation. Another ordering bug might coincide on these seeds.
