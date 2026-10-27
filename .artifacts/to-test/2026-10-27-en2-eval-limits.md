# EN2: rule evaluation limits, cross-process spike determinism, gold baseline

## Problem

1. Contracts 01 v1.5 (C2 evaluation limits, replacing the v1.3 wording): `check` bounds each rule evaluation by work, not wall-clock. The bound is at most 10^6 comprehension iterations plus elements or characters built, summed over the evaluation. A rule over the budget gives `Verdict(ok=False, error=...)`, `check` must be safe to call from several threads, and `validate` rejects `bytes` constants. In review of PR #4, `len('a' * 100000000000)` and a triple-nested comprehension over `db['reservations']` both passed `validate`, and `check` ran them without limit.
   - Review round 2 (v1.5 addendum) found two values whose cost was not charged: nested repetition `[[[0]*100]*100]*100` followed by a deep `==`, and an int squaring chain. Under the addendum, `*` applies to numbers only and computed numbers must stay within `abs(x) <= 10**15`.
2. The spike determinism test ran twice in one process. Both runs share one hash seed, so the test cannot see set-ordering bugs.
3. Contracts 01 v1.4 (baseline): the hand RuleSet must block 0 of the 43 airline gold tasks. It blocked tasks 15 and 16 at step 0 through `R-flights-not-both`.

## Threat model

Rules are authored by Muse (the compiler) and ratified by a human before they are enforced. They are not written by an adversary. The budget exists to bound accidental blow-ups, such as a model writing a triple-nested comprehension over the DB or repeating a list, so that a bad rule gives a failing verdict instead of a hung or crashed audit. It does not make `check` a sandbox for hostile code. Three review rounds closed every amplifier found, but the following paths are known and stay unbounded:
- `any` and `all` over a container, and `in` on a string, run in C uncharged, at a cost linear in the sizes involved.
- Slices are not charged. A slice copies at most the length of a value that already exists.
- The items of a `zip` object consumed directly by `min`, `max`, `sum`, `any` or `all` are not deep-charged. Inside a comprehension they are.
- Hashing in a set display or a `.get` key walks the key uncharged. The key is either input or a value the rule built, which is at most `MAX_DEPTH` deep and was charged when it was iterated.
- Containers that come from the snapshot or `args` are not charged by comparisons, `min`/`max` or iteration; only containers the rule built are. Comparing two distinct input values costs up to their size each time, so a rule that repeats such a comparison in a comprehension pays (iterations × input size), and only the iterations are charged.
- There is no wall-clock limit (v1.5).

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
  - Round 2:
    - `*` is numeric only. `validate` refuses it when one side is a sequence, string or comprehension, and at runtime it refuses any operand that is not a number.
    - The results of `* + - / // %`, unary `-`/`+` and `sum` must stay within `MAX_NUMBER = 10**15`, and so must number literals (checked at `validate`).
    - Comparison operands and `min`/`max` arguments charge every element they can reach, counting shared sub-lists each time they are reached. Sharing built through comprehensions then cannot amplify a deep compare. Probe: on 2000 reservations, three levels of shared rows compared with `==` ran 3.7 s and returned True before; it now stops at 0.07 s.
    - `in` against a dict or set charges only the left operand, because that is a hash lookup. `is` and `is not` are not charged.
  - Round 3:
    - `_Budget.it` charges every reachable element of each item it yields, so the doubling chain `v_k = (v_{k-1}, v_{k-1})` built by single-item comprehensions costs 2^k.
    - Every container the rule builds is registered with its nesting depth: displays, comprehension results, `+` on sequences, slices and the tuples from `zip`. One nested deeper than `MAX_DEPTH = 8` is refused.
    - The size charge only walks registered containers and is memoised by id. A first version walked snapshot data on every evaluation and made the compiler's match-rate test 7x slower (2.51 s → 17.19 s). Now it is 2.51 s → 3.69 s (`.scratch/after/en2-review3/compiler-test-timing.txt`).
    - Comprehension targets must be plain names. Before, `for db['users'] in [0]` overwrote the snapshot during `check` (found while testing round 3).
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
| Reviewer `amplify.py` (deep_eq_3..5, square_20..26) | deep_eq_5 and square_26 still running at 30 s (review); my run of both repros: pytest still running at 120 s (`.scratch/after/en2-review2/red.txt`) | all 6 ok=False in 0.0 s, max RSS 18–19 MB (`.scratch/after/en2-review2/amplify-after.txt`) |
| Comprehension-built sharing + deep `==`, 2000 reservations | 3.7 s, ok=True (probe run before the fix) | 0.07 s, ok=False (`.scratch/after/en2-review2/shared-eq-2000-after.txt`) |
| Round-2 tests on the previous code | 15 failed (`.scratch/after/en2-review2/red.txt`) | pass (gate) |
| Comparison charge removed (mutation) | n/a | `shared_deep_eq` fails in 0.09 s (`.scratch/after/en2-review2/compare-guard-removed.txt`) |
| Hand RuleSets under numeric-only `*` | n/a | airline 27 and retail 24 rules validate (`.scratch/after/en2-review2/rulesets-validate.txt`) |
| Retail gold tasks blocked | 2 of 112, tasks 64 and 105, with the `bylaw/build` rules.py (`.scratch/after/en2-review2/backtest-retail-before.txt`) | the same 2 of 112 (`.scratch/after/en2-review2/backtest-retail-after.txt`) |
| Reviewer `amplify3.py` (set_hash, get_hash, max_gen, eq_control; k = 30 and 33) | uncharged: 3 of the 4 round-3 tests at k=30 return ok=True, and the 9-deep display is accepted (`.scratch/after/en2-review3/red.txt`) | all 8 ok=False in 0.0 s, max RSS 19 MB (`.scratch/after/en2-review3/amplify3-after.txt`) |
| Depth cap removed (mutation) | n/a | the per-item size charge alone still fails all 4 doubling tests (`.scratch/after/en2-review3/depth-cap-removed.txt`) |
| Comprehension target writing into the snapshot or args | accepted, snapshot overwritten (4 failed, `.scratch/after/en2-review3/red-targets.txt`) | `RuleError` at validate, failing verdict and untouched snapshot in check (gate) |
| Earlier repros on the final code (`amplify.py`, 2000-row shared `==`) | — | all ok=False in 0.0 s (`.scratch/after/en2-review3/amplify-after.txt`, `.scratch/after/en2-review3/shared-eq-2000-after.txt`) |
| Gold tasks blocked by the hand RuleSet (backtest from PR #7) | 2 of 43 (tasks 15, 16; `.scratch/after/en2-gold-baseline/backtest-before.txt`) | 0 of 43 (`.scratch/after/en2-gold-baseline/backtest-after.txt`; with merged `bylaw/backtest.py`: `.scratch/after/en2-review/backtest-after.txt`; after round 2: `.scratch/after/en2-review2/backtest-after.txt`; after round 3: `.scratch/after/en2-review3/backtest-after.txt`, where retail is still 2 of 112, the same tasks 64 and 105) |
| New gold-baseline tests on the old rules | 2 failed (`.scratch/after/en2-gold-baseline/red.txt`) | pass (`.scratch/after/en2-eval-limits/make-check.txt`) |
| Spike Class A | H1–H3 (`.scratch/after/en1-rules/spike-output.txt`) | H1–H3, H1 cabin hop still a hole (`.scratch/after/en2-gold-baseline/spike-output.txt`) |

## Tests added

- `tests/test_rules.py::test_rule_over_the_evaluation_budget_gives_a_failing_verdict` (9 cases, on a 200-reservation snapshot so a removed guard fails instead of hanging), `test_rules_within_the_budget_still_evaluate`, `test_the_budget_is_per_evaluation_not_per_process`, `test_concurrent_checks_over_the_budget_all_fail_cleanly` (8 threads) and `test_bytes_constants_are_rejected` (3 cases).
- Round 2:
  - New cases in the budget test: `deep_eq_repeat`, `int_squaring`, `runtime_repeat`, `shared_deep_eq`, `shared_deep_max` and `sum_over_cap`.
  - `test_repetition_and_oversized_literals_are_rejected_by_validate` (6 cases) and `test_numbers_over_ten_to_the_fifteen_fail` (6 cases).
  - `test_rules_within_the_budget_still_evaluate` now covers deep `==` on small values, `in`, `max` over lists and arithmetic just under the cap.
- `tests/test_rules.py::test_basic_economy_may_change_cabin_but_never_flights` and `test_other_cabins_may_change_cabin_and_flights_in_one_call` (gold task 15/16 arguments). The latter replaces `test_cabin_and_flights_in_one_call_is_denied_but_each_alone_is_not`.
- `tests/test_spike.py::test_spike_output_is_deterministic_and_leaves_the_tracked_file_alone`, rewritten to use subprocesses.

- Round 3:
  - Budget cases `set_hash`, `get_hash`, `max_gen` and `eq_doubling` (the `amplify3.py` chains at k = 30), and `depth_9`.
  - `test_rules_within_the_budget_still_evaluate` now also covers an 8-deep display and a 3-step doubling chain.
  - `test_comprehension_targets_cannot_write_into_the_snapshot_or_args` (4 cases).

## Out of scope

- Gold task 39 counts as "unknown" in the backtest, because `bylaw/backtest.py` (PR #7) infers no cancel reason for it. That belongs to PR #7.
- The residual unbounded paths are listed under Threat model.
- Retail gold tasks 64 and 105 are blocked by `R-exch-1` and `R-exch-5`. That was already so before this change, and it belongs to the retail RuleSet (RT1).
- Slices are not charged. A slice copies at most the length of a value that already exists.
- Big-integer growth: without `**`, an expression can only multiply as many times as it has `*` operators.
- The hash seeds 1, 4 and 6 were chosen because they give three different outputs under the mutation. Another ordering bug might coincide on these seeds.
