# PR1: Muse chain templates, bounded BFS on the rest, `bench`

## Problem

`audit` without `--no-llm` crashed, and `bench` did not exist. That broke:

- REQ-PR1-1 (LLM-on audit), now scoped to the default budget by v1.8;
- REQ-PR1-2 (bench table and JSON);
- C5 v1.2/v1.6 (bench rows, `found`);
- C6, plus its v1.8 feedback protocol and Muse-failure fallback.

## Root cause

The feature was missing. `bylaw/proposer.py:19` (at 2842402) raised `NotImplementedError("Muse-guided search is PR1; use --no-llm")`, and `bylaw/__main__.py` had no `bench` subcommand.

## Change

- **Muse calls:** `bylaw/proposer.py:29` `search(domain, ruleset, budget, use_llm, llm=None)`. With `use_llm`, `_muse_chains` (`:283`) asks Muse once per goal, 7 calls in parallel, with `effort="high"` and `max_tokens=32000`. 16000 came back empty with `finish_reason=length`.
- **Failed calls:** a call that fails for a goal (an exception, or an empty reply after the client's retry) gives that goal no templates, so the BFS covers it. It never aborts (v1.8).
- **Prompt:** `_ask` (`:233`) gives Muse:
  - the policy, the RuleSet's tool rules and the goal (id, name, `policy_ref`, plus the source of the predicate module);
  - the write-tool schemas;
  - up to 8 example target records, one per (cabin, insurance, membership, flight statuses).
- **Templates:** Muse returns up to 4 per goal. Each has a `where` filter over the target and 1–4 steps. Argument values starting with `=` are expressions over `res`/`user`/`db`.
- **Binding:** `_instances` (`:262`) binds a template to every `domain.targets(goal)` record its `where` accepts.
  - Expressions go through the C2 evaluator (`rules._compile` + `rules._run`), which is whitelisted and work-bounded, because Muse output is untrusted.
  - A binding whose first step the rules already forbid is dropped and costs nothing, because checking rules is free.
- **Budget split:** templates take turns round-robin. Muse gets at most `MUSE_SHARE = 0.5` of the budget (`:25`). The BFS gets the rest and skips chains Muse already proposed, at no cost.
- **C6 v1.8 feedback:** after each chain the caller sends `(executed, hit)`, and the budget is charged with `executed` in both the Muse and BFS phases (`_cost`, `:51`; `_bfs`, `:56`). A chain blocked at step 1 costs 0. Without feedback (a plain `for` loop) a chain costs its length, so the C6 bound still holds. A template whose misses exceed `2*hits + 1` loses its turns.
- **`report._steered`** (`bylaw/report.py:74`) sends the feedback from the running `tool_calls`.
- **`audit(..., llm=None)`** (`report.py:87`):
  - passes `llm=` to `search` only in muse mode;
  - `llm_calls` counts the Muse requests and `llm_errors` the failed ones (v1.8);
  - `tokens` sums prompt and completion tokens billed in `llm.CALLS`;
  - `run.model` is filled in muse mode;
  - `stats.found` holds, for each Class A hole, the cumulative executed write steps and the seconds at which it was proved (v1.6).
- **`cmd_bench`** (`bylaw/__main__.py:156`): `bench --domain D --budget N [--modes bfs,muse] [-o PATH]`. Each row has `mode`, `holes`, `hole_keys`, `tool_calls`, `llm_calls`, `llm_errors`, `tokens`, `seconds`, `found` and `commit`. It also has `contradictions`/`contradiction_keys` (Class B, v1.7, read with `.get`, so 0 until GA1 lands) and `ambiguities`/`ambiguity_keys`.
- **`tests/test_api.py:182`:** the fake `search` takes `**kw`. It is a unit test, edited with the reviewer's leave.

## Before / after

Live bench: one run per budget, fresh Muse calls (`BYLAW_NO_CACHE=1`), commit c4c136f (`.scratch/after/pr1-proposer/bench-commit.txt`). Holes = Class A. C = Class C ambiguities. Tool calls = executed write steps.

| Budget | BFS holes / C / tool calls / s | Muse holes / C / tool calls / LLM calls / tokens / s | Evidence |
|---|---|---|---|
| 25 | 1 / 0 / 25 / 8.28 | 2 / 5 / 25 / 7 / 185684 / 76.56 | `bench-25.txt`, `bench-25.json` |
| 50 | 4 / 0 / 49 / 17.28 | 4 / 9 / 50 / 7 / 185521 / 92.94 | `bench-50.txt`, `bench-50.json` |
| 100 | 7 / 2 / 99 / 31.56 | 8 / 23 / 100 / 7 / 184757 / 138.7 | `bench-100.txt`, `bench-100.json` |
| 200 | 9 / 2 / 200 / 44.97 | 38 / 22 / 199 / 7 / 196882 / 199.18 | `bench-200.txt`, `bench-200.json` |
| 2000 | 15 / 2 / 1997 / 211.35 | 18 / 123 / 1999 / 7 / 173705 / 499.26 | `bench-2000.txt`, `bench-2000.json` |

`.scratch/after/pr1-proposer/bench-summary.txt` has the goals per mode, the key-subset check and `llm_errors` (0 in every run):

- Muse finds at least as many Class A holes as BFS at every budget, but its keys contain the BFS keys only at 2000. Below 2000 the bench reports both honestly (v1.8 scope).
- Blind BFS never reaches G7 (duplicate compensation, Class C). Muse proves it at every budget, 121 keys at 2000.
- Variance is large: the previous sweep (at 337158a, before v1.8 and on yielded-step budgeting) gave 147 Class A holes at 2000, and this one 18 (`r1-337158a/`).

| Check | Before (2842402) | After (c4c136f) |
|---|---|---|
| `audit --domain airline` (LLM on) | `NotImplementedError` (`bylaw/proposer.py:19` at 2842402) | runs; table above |
| Unit tests for PR1 (v1.8 additions) | fail (`red-proposer.txt`, `red-report.txt`, `red-bench.txt`, `red-feedback.txt`, `red-found.txt`, `red-v1.8.txt`) | pass (gate) |
| Blind acceptance, offline (`test_wave2_proposer.py` from `origin/test/01-wave2` + `test_wave2_audit.py`) | `bench` missing | 26 passed (`acceptance-offline.txt`) |
| Live tests: `test_wave2_proposer` live ×2, `test_wave2_audit` REQ-PR1-1 at 2000, unit live ×2 | n/a | 5 passed, one run (`live-tests.txt`) |
| BFS at 1000 vs 2000 (basis of `MUSE_SHARE`), executed-step budget | n/a | 15 holes each, no key at 2000 that 1000 misses (`v18-bfs.txt`, `v18-bfs1000.json`, `v18-bfs2000.json`, `bench-summary.txt` first line) |
| Mutant M3: plain `eval` instead of `rules._run(_compile)` | survived | killed by `test_malformed_templates_are_ignored` (`mutant-M3-raw-eval.txt`) |
| Mutant M4: constant `found[].tool_calls` | survived | killed by `test_found_records_the_cumulative_write_steps_at_which_each_hole_was_proved` (`mutant-M4-found-constant.txt`) |
| Feedback is load-bearing | n/a | without `_steered`, `test_a_muse_template_that_finds_nothing_hands_its_budget_back_to_the_bfs` fails (`mutant-no-feedback.txt`, round 1) |

Every path above is under `.scratch/after/pr1-proposer/`.

## Tests added

- `tests/test_proposer.py`:
  - Muse is asked once per goal with `effort="high"`, and the prompt carries `policy_ref`, every rule and the write tools.
  - Templates come first, bound to every target their filter accepts.
  - The budget is never exceeded with the LLM on.
  - A template blocked at step 1 spends nothing.
  - Malformed templates are ignored, including expressions plain `eval` would accept (`9 ** 2`, `res.keys()`).
  - A template that misses loses its turns; one that hits keeps them, under `(executed, hit)`.
  - The budget is charged with executed steps (a chain blocked at step 1 is free), with and without the LLM.
  - A failed Muse call for one goal leaves the other goals and the BFS running.
  - Live: Muse proposals bind and change the search.
- `tests/test_report.py`:
  - A scripted G7 template is proved 5/5 as Class C with `llm_calls == 7`.
  - A dud template hands its budget back: same keys as BFS at 38, and `tool_calls` = 2 + BFS's.
  - `found` holds exact cumulative steps: 2 for the scripted first hole, then BFS's own values offset by 2.
  - Failed calls are counted in `llm_errors` and the audit still proves G7.
- `tests/test_bench.py`: bfs and muse rows on one budget, with `found` ordered and bounded, and the table printed.

## Out of scope / not done

- `tokens` still reads the process-wide `llm.CALLS`. Two audits with Muse running at once in one process would mix their counts, the same ceiling `bylaw/api.py:71` documents. A per-audit count needs `llm.structured` to return usage, which is not cheap.
- Muse can claim a key as Class C (cancel+rebook) before the BFS reaches it as Class A. "A replaces C" was tried and reverted because it breaks REQ-EX1-3. At 2000 the subset held in this run.
- Retail: `search` raises for non-airline domains. The BFS move set and `classify` are airline-only.
- Templates evaluate on the DB before the first step. A step cannot use an id created by an earlier step.
- Each budget is one Muse run, and replies vary a lot between runs (see variance above).
- Cost: about 174k–197k tokens and 7 calls per Muse run.
