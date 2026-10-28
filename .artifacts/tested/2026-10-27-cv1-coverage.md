# CV1: coverage table per forbidden goal

## Problem

REQ-CV1-1 (`docs/plan/05-rigor/00-plan.md`): `python -m bylaw coverage REPORT` prints, per forbidden goal, the chains tried, the executed write steps and the findings by class, as a Markdown table and JSON. There was no `coverage` subcommand, and the C4/C5 report recorded only run-wide `stats.chains_tried` and `stats.tool_calls`, so the per-goal search effort could not be read from a report.

## Root cause

Missing feature. `bylaw/report.py:177` (`audit`, at 82e9c3e) builds `stats` with run totals only; `bylaw/__main__.py:204` (`main`, at 82e9c3e) has no `coverage` parser.

## Change

- **C5 contract addition (backward compatible):** `stats.per_goal = {goal_id: {"chains", "executed", "A", "B", "C"}}`. It is an optional property in `REPORT_SCHEMA` (`bylaw/report.py`, `_STATS`), so older reports still validate.
- `bylaw/report.py` `audit`: a chain counts for every goal whose `domain.targets(goal)` include the chain's primary record, `_target(chain)`, which is the record that names the C4 key `goal:target` (reservation in airline, order in retail, else user). `chains` counts those chains, `executed` sums their executed write steps (C6 v1.8 cost). A/B/C count the final entries per goal by class, after a Class A has taken over a B or C key. Class B comes from GA1's gold adjudication (C4 v1.7).
- `bylaw/__main__.py` `cmd_coverage`: `coverage REPORT [--json OUT]` prints `| goal | chains | executed | A | B | C |`. JSON at OUT: `{"run", "goals": [{goal, chains, executed, A, B, C}]}`. A report without `per_goal` lists every goal of its domain with class counts from `holes`, `contradictions` and `ambiguities`, and `n/a` (JSON `null`) for chains and executed.

## Before / after

| Check | Before (82e9c3e, `origin/bylaw/build`) | After (4bdca67) |
|---|---|---|
| `tests/test_coverage.py` (3 tests) | 3 failed: `KeyError: 'per_goal'`, `invalid choice: 'coverage'` (`.scratch/after/cv1-coverage/red-before-rebased.txt`; first red at 0131546: `red-before.txt`) | 3 passed (`.scratch/after/cv1-coverage/green-after-merge.txt`) |
| `audit --domain airline --no-llm` (budget 2000) | no per-goal counts | 0 Class A, 15 Class B, 2 Class C; 906 chains, 1997 tool calls, 232.57 s (`.scratch/after/cv1-coverage/audit-airline-4bdca67.txt`, `report-airline-bfs-4bdca67.json`) |
| `coverage` on that report | no subcommand | airline table below (`.scratch/after/cv1-coverage/coverage-airline-4bdca67.txt`, `coverage-airline-4bdca67.json`) |
| `audit --domain retail --no-llm --budget 200` | no per-goal counts | 1 Class A, 0 B, 1 C; 660 chains, 199 tool calls, 61.75 s (`.scratch/after/cv1-coverage/audit-retail-4bdca67.txt`); retail table below (`coverage-retail-4bdca67.txt`, `coverage-retail-4bdca67.json`) |
| Gate | n/a | `gate: GREEN at e4d384c`; 422 passed, 1 skipped, 11 deselected in 2981.70 s; web build ok (`.scratch/after/cv1-coverage/gate.txt`; load at start 1.81, `gate-start-load.txt`) |

Airline, offline BFS, budget 2000, at 4bdca67 (`.scratch/after/cv1-coverage/coverage-airline-4bdca67.txt`):

| goal | chains | executed | A | B | C |
|---|---|---|---|---|---|
| G1 | 490 | 1056 | 0 | 2 | 2 |
| G2 | 94 | 195 | 0 | 1 | 0 |
| G3 | 452 | 1012 | 0 | 0 | 0 |
| G4 | 906 | 1997 | 0 | 0 | 0 |
| G5 | 906 | 1997 | 0 | 12 | 0 |
| G6 | 177 | 376 | 0 | 0 | 0 |
| G7 | 906 | 1997 | 0 | 0 | 0 |

G4, G5 and G7 target every reservation, so their rows equal the run totals. With GA1, G1, G2 and G5 are gold-sanctioned, so the 15 findings that were Class A before the merge (run at 5e0ba10, `.scratch/after/cv1-coverage/coverage-table.txt`) are now Class B. The same chains and executed counts came out at both commits.

Retail, offline BFS, budget 200, at 4bdca67 (`.scratch/after/cv1-coverage/coverage-retail-4bdca67.txt`):

| goal | chains | executed | A | B | C |
|---|---|---|---|---|---|
| R1 | 260 | 100 | 0 | 0 | 0 |
| R2 | 396 | 95 | 0 | 0 | 0 |
| R3 | 348 | 48 | 0 | 0 | 0 |
| R4 | 48 | 47 | 0 | 0 | 0 |
| R5 | 48 | 47 | 0 | 0 | 1 |
| R6 | 48 | 47 | 1 | 0 | 0 |
| R7 | 260 | 100 | 0 | 0 | 0 |
| R8 | 308 | 147 | 0 | 0 | 0 |

Retail rows are in scope. Many retail chains are blocked at step 1 and cost 0 steps (660 chains, 199 tool calls), so `chains` is often larger than `executed`.

## Tests added

`tests/test_coverage.py`:
- per_goal on a fake two-chain search (real executor): a chain the rules block at step 1 on a G2 target counts as 1 chain with 0 executed steps for G2. The 1KUOX2 chain (a G1 target, not a G2 one) adds 1 chain and 2 executed steps to G1, and one Class B, because G1 is gold-sanctioned (contracts v1.7, task 32). The class counts match the report's holes, contradictions and ambiguities.
- table rendering and JSON from a report with per_goal.
- an old report without per_goal: every airline goal listed, class counts from holes/contradictions/ambiguities, `n/a` / `null` for chains and executed.

## Out of scope

- Attribution is by target, not by intent: a BFS chain on a reservation counts for every goal that targets it, even goals the BFS move set cannot reach (airline G4 and G7). The table shows how much of the search touched each goal's targets, not how many chains were designed for that goal.
- `contracts.md` is not edited; the C5 addition is stated here and in the PR.
- No Muse-mode run (needs the key). The retail run uses budget 200, not the default.
- FX2 (PR #28, G7 keyed by user) is not on `bylaw/build`. When it lands, `_target` decides the G7 key and per_goal follows it.

## Review (PR #29)

- **Merged base:** origin/bylaw/build merged into the branch at 6f1bc66 (FX2 #28, contracts v1.13) and e1b4af4 (FX1 #26, contracts v1.14). FX1 conflicted in `bylaw/report.py` (`_STATS` next to FX1's `_RUN` schema). The reviewer kept both sides; nothing else changed.
- **Gate:** `gate: GREEN at e1b4af4`. 438 passed, 1 skipped, 11 deselected in 3300.35 s, plus the web build.
- **Tests fail on old code:** `tests/test_coverage.py` with `bylaw/` from 3b31c3a: 3 failed (`KeyError: 'per_goal'`, `invalid choice: 'coverage'`).
- **Mutations:** each one turned a test red:
  - dropping the A/B/C count gave `(0, 0) != (0, 1)`;
  - counting every chain for every goal (`if True:` in place of `target in aimed[gid]`) gave G2 chains 2 != 1, executed 2 != 0;
  - dropping the domain goals from the old-report path left only G1, G2 and G7 listed.
- **Trace:** `harness-trace docs/plan/05-rigor/00-plan.md tests`: 5 requirements, all named by a test.
- **Evidence:** the airline and retail tables above match `coverage-*-4bdca67.txt` in the builder's `.scratch/after/cv1-coverage/`. The finding counts match `audit-*-4bdca67.txt` (airline: B G1 2, G2 1, G5 12; C G1 2). These figures were measured at 4bdca67, before FX2 and FX1. No audit was re-run on the merged code.
- **Stale lines above:** contracts.md now records this addition (v1.13, 3b31c3a), and FX2 is on bylaw/build. The tests failed on 3b31c3a as well as on 82e9c3e.
