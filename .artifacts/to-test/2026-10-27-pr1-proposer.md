# PR1: Muse chain templates, bounded BFS on the rest, `bench`

## Problem

`audit` without `--no-llm` crashed, and `bench` did not exist. That broke REQ-PR1-1 (LLM-on audit), REQ-PR1-2 (bench table and JSON), C5 v1.2/v1.6 (bench rows, `found`) and C6 (Muse proposes chains per goal first with `effort="high"`, then BFS fills the remaining budget).

## Root cause

The feature was missing. `bylaw/proposer.py:19` (at 2842402) raised `NotImplementedError("Muse-guided search is PR1; use --no-llm")`, and `bylaw/__main__.py` had no `bench` subcommand.

## Change

- `bylaw/proposer.py:29` `search(domain, ruleset, budget, use_llm, llm=None)`. With `use_llm`, `_muse_chains` (`:274`) asks Muse once per goal. The 7 calls run in parallel, each with `effort="high"` and `max_tokens=32000`. 16000 came back empty with `finish_reason=length`.
- `_ask` (`:224`) gives Muse:
  - the policy, the RuleSet's tool rules and the goal (id, name, `policy_ref`, plus the source of the predicate module);
  - the write-tool schemas;
  - up to 8 example target records, one per (cabin, insurance, membership, flight statuses).
- Muse returns up to 4 **templates** per goal. Each template has a `where` filter over the target and 1–4 steps. Argument values starting with `=` are expressions over `res`/`user`/`db`.
- `_instances` (`:253`) binds a template to every `domain.targets(goal)` record its `where` accepts. Expressions are evaluated by the C2 evaluator (`rules._compile` + `rules._run`), which is whitelisted and work-bounded, because Muse output is untrusted. A binding whose first step the rules already forbid is dropped without spending budget, because checking rules is free.
- Templates take turns round-robin. Muse gets at most `MUSE_SHARE = 0.5` of the budget (`:25`). The BFS from EX1 gets the rest and skips chains Muse already proposed.
- **Hit feedback:** the caller may `send()` back whether each chain proved a new entry. A template whose misses exceed `2*hits + 1` loses its turns. `report._steered` (`bylaw/report.py:74`) sends that signal. A plain `for` loop still works and sends nothing.
- `bylaw/report.py` `audit(..., llm=None)`:
  - `llm_calls` counts the search's Muse requests.
  - `tokens` sums prompt and completion tokens billed in `llm.CALLS` (0 for a cached reply).
  - `run.model` is filled in muse mode.
  - `stats.found` lists, for each Class A hole, the cumulative executed write steps and the seconds at which it was proved (v1.6).
- `bylaw/__main__.py:67` `cmd_bench`: `bench --domain D --budget N [--modes bfs,muse] [-o PATH]`. It runs `audit` per mode on the hand RuleSet, prints the table and writes the JSON. Each row has `mode`, `holes`, `hole_keys`, `tool_calls`, `llm_calls`, `tokens`, `seconds`, `found` (v1.6), plus `contradictions`/`contradiction_keys` (Class B, v1.7: read with `.get`, so 0 until GA1 lands), `ambiguities`/`ambiguity_keys` and `commit`.

## Before / after

Live bench: one run per budget, fresh Muse calls (`BYLAW_NO_CACHE=1`), commit 337158a (`.scratch/after/pr1-proposer/bench-commit.txt`). Holes = Class A. C = Class C ambiguities.

| Budget | BFS holes / C / tool calls / s | Muse holes / C / tool calls / LLM calls / tokens / s | Evidence |
|---|---|---|---|
| 25 | 1 / 0 / 19 / 7.18 | 2 / 2 / 18 / 7 / 193476 / 80.29 | `bench-25.txt`, `bench-25.json` |
| 50 | 3 / 0 / 42 / 14.43 | 4 / 11 / 44 / 7 / 182610 / 99.66 | `bench-50.txt`, `bench-50.json` |
| 100 | 6 / 1 / 75 / 25.1 | 3 / 23 / 92 / 7 / 178421 / 119.7 | `bench-100.txt`, `bench-100.json` |
| 200 | 8 / 2 / 152 / 37.8 | 9 / 48 / 174 / 7 / 187683 / 195.61 | `bench-200.txt`, `bench-200.json` |
| 2000 | 15 / 2 / 1486 / 177.1 | 147 / 240 / 1671 / 7 / 192192 / 914.56 | `bench-2000.txt`, `bench-2000.json` |

Goals per mode and key-superset per budget are in `.scratch/after/pr1-proposer/bench-summary.txt`:

- Blind BFS only reaches G1, G2 and G5.
- Muse adds G7 (duplicate compensation, Class C) at every budget, and G3 (insurance added through cancel+rebook, Class C, 118 keys) at 2000.
- At 2000, Muse finds 134 G1 holes against BFS's 2.
- At 50, 100 and 200 the Muse run misses some BFS keys: Muse spends half the budget. At 25 and 2000 it holds a superset.
- At 100, Muse found fewer Class A holes than BFS (3 vs 6).

| Check | Before (2842402) | After (337158a) |
|---|---|---|
| `audit --domain airline` (LLM on) | `NotImplementedError` (`bylaw/proposer.py:19` at 2842402) | runs; table above |
| Unit tests for PR1 | fail (`red-proposer.txt`, `red-report.txt`, `red-bench.txt`, `red-feedback.txt`, `red-found.txt`) | pass (`green-after-rebase.txt`, gate) |
| Blind acceptance, offline (`test_wave2_proposer.py` from `origin/test/01-wave2` + `test_wave2_audit.py`) | `bench` missing | 26 passed (`acceptance-offline.txt`) |
| Live tests: `test_wave2_proposer` live ×2, `test_wave2_audit` REQ-PR1-1 (superset at 2000), unit live ×2 | n/a | 5 passed, one run (`live-tests.txt`) |
| BFS at 1000 vs 2000, rebased rules (basis of `MUSE_SHARE`) | n/a | 2000 finds no key that 1000 misses (`rebased-bfs1000-vs-2000.txt`) |
| Feedback is load-bearing | n/a | removing `_steered` fails `test_a_muse_template_that_finds_nothing_hands_its_budget_back_to_the_bfs` (`mutant-no-feedback.txt`) |

Every path above is under `.scratch/after/pr1-proposer/`. The pre-rebase runs (commit f0ab557, before EN2's rule changes) are kept in `pre-rebase/`.

## Tests added

- `tests/test_proposer.py`:
  - Muse is asked once per goal with `effort="high"`, and the prompt carries the goal `policy_ref`, every rule and the write tools.
  - Templates come first, bound to every target their filter accepts (checked against the DB independently).
  - Budget is never exceeded with the LLM on (0, 1, 7, 40).
  - A template the rules forbid at step 1 spends nothing.
  - Malformed templates are ignored.
  - A missing template loses its turns and a hitting one keeps them.
  - Live: Muse proposals bind and change the search.
- `tests/test_report.py`:
  - A scripted G7 template is proved 5/5 as Class C with `llm_calls == 7`, and blind BFS never finds G7.
  - A template that finds nothing hands its budget back: same keys as BFS on budget 36.
- `tests/test_bench.py`: the bench writes bfs and muse rows on one budget with `found` ordered and bounded, and prints the table.

## Out of scope / not done

- REQ-PR1-1 as the acceptance test reads it (BFS keys ⊆ Muse keys at the same budget) is only measured at budget 2000, where it held once. Below 2000 it does not hold (50/100/200 above). One more risk: a Muse cancel+rebook can claim a key as Class C before BFS reaches it as Class A. In the pre-rebase run at 2000, `G1:01WQQ7` was lost this way (`pre-rebase/bench-2000.json`). I tried "Class A replaces Class C" and reverted it: it emptied `ambiguities` on the default BFS report and broke REQ-EX1-3.
- The budget is charged on yielded steps, not executed ones. That is the review finding on C6 v1.2, which GA1 is fixing. The Muse loop counts the same way as the BFS.
- Retail: `search` still raises for non-airline domains. The BFS move set and `classify` are airline-only, and porting them is not cheap.
- Templates evaluate expressions on the DB before the first step only. A step cannot reference an id created by an earlier step, such as a new reservation from `book_reservation`.
- Variance: each budget is one Muse run. Templates differ run to run, which explains, for example, 147 vs 277 Class A holes at 2000 before and after the rebase (`pre-rebase/bench-2000.txt`).
- Cost: about 180k–193k tokens and 7 calls per Muse run. Muse at 2000 takes 914 s, mostly proving 387 entries 5 times each.
