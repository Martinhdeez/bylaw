# CV1: coverage table per forbidden goal

## Problem

REQ-CV1-1 (`docs/plan/05-rigor/00-plan.md`): `python -m bylaw coverage REPORT` prints, per forbidden goal, the chains tried, the executed write steps and the findings by class, as a Markdown table and JSON. There was no `coverage` subcommand, and the C4/C5 report recorded only run-wide `stats.chains_tried` and `stats.tool_calls`, so the per-goal search effort could not be read from a report.

## Root cause

Missing feature. `bylaw/report.py:133` (`audit`, at 0131546) builds `stats` with run totals only; `bylaw/__main__.py:180` (`main`, at 0131546) has no `coverage` parser.

## Change

- **C5 contract addition (backward compatible):** `stats.per_goal = {goal_id: {"chains", "executed", "A", "B", "C"}}`. It is an optional property in `REPORT_SCHEMA` (`bylaw/report.py`, `_STATS`), so older reports still validate.
- `bylaw/report.py` `audit`: a chain counts for every goal whose `domain.targets(goal)` include the record the chain starts on (the same target that names the C4 key `goal:target`). `chains` counts those chains, `executed` sums their executed write steps (C6 v1.8 cost), and A/B/C count the proven entries per goal by class. B stays 0 until GA1 lands; the count reads each entry's `class`, so it picks up Class B without a change.
- `bylaw/__main__.py` `cmd_coverage`: `coverage REPORT [--json OUT]` prints `| goal | chains | executed | A | B | C |`. JSON at OUT: `{"run", "goals": [{goal, chains, executed, A, B, C}]}`. A report without `per_goal` lists every goal of its domain with class counts from `holes`, `contradictions` and `ambiguities`, and `n/a` (JSON `null`) for chains and executed.

## Before / after

| Check | Before (0131546) | After (5e0ba10) |
|---|---|---|
| `tests/test_coverage.py` (3 tests) | 3 failed: `KeyError: 'per_goal'`, `invalid choice: 'coverage'` (`.scratch/after/cv1-coverage/red-before.txt`) | 3 passed (`.scratch/after/cv1-coverage/green-after.txt`) |
| `audit --domain airline --no-llm` (budget 2000) | no per-goal counts | 15 Class A, 2 ambiguities; 906 chains, 1997 tool calls, 219.9 s (`.scratch/after/cv1-coverage/audit-stdout.txt`, `report-airline-bfs.json`) |
| `coverage` on that report | no subcommand | table below (`.scratch/after/cv1-coverage/coverage-table.txt`, `coverage-airline-bfs.json`) |
| Full offline suite (`pytest -q`, shared venv, `TAU2_DATA_DIR` set; not `harness-gate`) | n/a | 360 passed, 3 failed, 3 skipped, 10 deselected. All 3 failures are about the environment: `.context/tau2-bench` is absent from this worktree (2 BT1 acceptance tests hardcode `tasks.json` under it, and the MCP stdio subprocess gets no `TAU2_DATA_DIR`) (`.scratch/after/cv1-coverage/suite.txt`) |

Coverage of the offline airline run (`.scratch/after/cv1-coverage/coverage-table.txt`):

| goal | chains | executed | A | B | C |
|---|---|---|---|---|---|
| G1 | 490 | 1056 | 2 | 0 | 2 |
| G2 | 94 | 195 | 1 | 0 | 0 |
| G3 | 452 | 1012 | 0 | 0 | 0 |
| G4 | 906 | 1997 | 0 | 0 | 0 |
| G5 | 906 | 1997 | 12 | 0 | 0 |
| G6 | 177 | 376 | 0 | 0 | 0 |
| G7 | 906 | 1997 | 0 | 0 | 0 |

G4, G5 and G7 target every reservation, so their rows equal the run totals (906 chains, 1997 tool calls). The two Class C entries sit on G1: cancel+rebook chains reclassified by `classify`.

## Tests added

`tests/test_coverage.py`:
- per_goal on a fake two-chain search (real executor): a chain the rules block at step 1 on a G2 target counts as a chain with 0 executed steps for G2; the 1KUOX2 hole chain (G1 target, not G2) adds 1 chain, 2 executed steps and one Class A to G1 only; class counts match the report's entries.
- table rendering and JSON from a report with per_goal.
- an old report without per_goal: every airline goal listed, class counts from holes/contradictions/ambiguities, `n/a` / `null` for chains and executed.

## Gate

`harness-gate` was not run. `make check` needs `.context/tau2-bench/` in the worktree. Creating it (a symlink to the shared checkout) and running `make tau2` were both denied by the permission system. The commit carries no green stamp.

## Out of scope

- Attribution is by target, not by intent: a BFS chain on a reservation counts for every goal that targets it, even goals the BFS move set cannot reach (G4, G7 have no `update_reservation_passengers` / `send_certificate` moves). The table says how much search touched each goal's targets, not how many chains were designed for it.
- `contracts.md` is not edited; the C5 addition is stated here and in the PR.
- Muse mode run (needs the key); retail run (search on this base is airline-only until SR1).
