# EX1: executor, verifier, C4 report, `audit --no-llm` CLI

## Problem

Before this change, bylaw could only reach holes through the hand-written M0 spike (`spike/holes_by_hand.py`). No command searched for chains, executed them, proved them and wrote a report. REQ-EX1-1..4 and contracts C4, C5 (`audit`), C6 (search interface) and v1.2 (diff format, hole key, `replay` signature, budget = executed write steps) had no implementation.

## Root cause

The feature is missing: `bylaw/executor.py`, `bylaw/verifier.py`, `bylaw/report.py` and `bylaw/proposer.py` did not exist, and `bylaw/__main__.py:28` (`main`, at d07f8f8) had only `backtest`.

## Change

- `bylaw/executor.py:25` `run(domain, chain, ruleset)`: runs a chain on a fresh env. Each step is checked with `rules.check` on the snapshot just before the call. The run stops at the first step the rules forbid (that step is not executed) or the tool rejects. It returns the C4 steps, the StepResults, both snapshots and the v1.2 diff. `executor.py:50` `replay(domain, chain) -> {"steps", "diff"}` runs the chain without rules (v1.2).
- `bylaw/verifier.py:6` `prove(...) -> "k/n"`: a replay counts only if every step is allowed and succeeds, the diff equals the expected one, and the goal holds on the full before/after DB.
- `bylaw/proposer.py:17` `search(domain, ruleset, budget, use_llm)` (C6): BFS over write calls only, depth ≤ 4. The budget is the sum of yielded chain lengths, so executed steps can never exceed it. Targets come from `domain.targets(g)` for every goal. They are grouped into strata by (cabin, insurance, booked within 24h) and taken round-robin, one batch per round, depth-major inside a batch. Within a stratum, reservations whose legs are all available with seats in every cabin come first. Airline moves: cancel ("change of plan"), cabin change, date shift of every leg, fill the free bag allowance, and rebook after a cancel. Back-to-back cabin changes or back-to-back shifts are pruned. `use_llm=True` raises `NotImplementedError` (PR1).
- `bylaw/report.py`: `REPORT_SCHEMA` (C4 + v1.2 `key` and diff shape) and `audit(...)`. Each chain is executed. When every step is ok, goals are screened on the snapshot cut down to the changed records. Every hit is then proven 5 times on the full DB, and only `5/5` entries are kept. There is one entry per `goal:target_id` key, the first one found, which is the shortest chain. `classify` (report.py:35) marks an entry Class C when the goal is pre-registered C, or when the chain cancels a reservation and then books again for the same user (REQ-EX1-3). `money_delta` is the net money the chain paid out to the customer.
- `bylaw/__main__.py`: `cmd_audit` added in the BT1 style (`set_defaults(fn=...)`, lazy imports).

## Before / after

| Check | Before (d07f8f8) | After (cbd8c2a) |
|---|---|---|
| `audit --domain airline --no-llm` | no `audit` subcommand (`.scratch/after/ex1-executor/red-executor.txt`: no executor module) | 15 Class A holes (G1, G2, G5), 2 Class C, report validates (`.scratch/after/ex1-executor/holes.txt`, `report.json`) |
| Wall-clock, default budget 2000 | n/a | 166.42 s real (`.scratch/after/ex1-executor/audit-stderr.txt`); 706 chains, 1486 tool calls (`holes.txt`) |
| `--budget 25` | n/a | 1 Class A hole, 19 tool calls, 6.46 s (`.scratch/after/ex1-executor/audit-budget25-stdout.txt`) |
| Blind acceptance `test_wave2_audit.py` + `test_wave2_proposer.py` (from `origin/test/01-wave2`, run locally, not committed) | not runnable | 25 passed, 1 failed (`bench`, which is PR1) (`.scratch/after/ex1-executor/acceptance-wave2.txt`) |
| New unit tests | fail at collection (`red-executor.txt`, `red-verifier.txt`, `red-proposer.txt`, `red-report.txt` in `.scratch/after/ex1-executor/`) | pass in the gate (`.scratch/after/ex1-executor/gate.txt`) |

## Tests added

- `tests/test_executor.py`: the replay diff holds only the changed record with before/after; every replay starts from a fresh DB; `run` stops at a forbidden step without executing it (R-cancel-ground on T1QOBS); upgrade then cancel goes through.
- `tests/test_verifier.py`: upgrade+cancel on T1QOBS proves G2 5/5; a forbidden chain, a goal that does not hold, and an unreproduced diff each give 0/n.
- `tests/test_proposer.py`: the budget is never exceeded (0, 1, 50); chains are write-only with depth ≤ 4, depth 1 first; the search is deterministic.
- `tests/test_report.py`: a budget-40 audit validates and every entry is proven; the schema rejects a hole without its proof; classification of cancel+rebook and of the Class C goal G7.

## Out of scope

- Muse-guided search and `bench` (PR1). `audit` without `--no-llm` exits with `NotImplementedError`.
- `send_certificate` and `update_reservation_passengers` are not in the BFS move set, so G3, G4, G6 and G7 are not searched for directly.
- Search order for retail: `search` raises for any domain other than airline.
- EN2 (PR #8, removes R-flights-not-both) is not on `bylaw/build`. This run uses the current `airline.json`.
- Goal screening on the cut-down snapshot depends on goals reading only the diff (as the `bylaw/goals.py` docstring says). A goal that read untouched records would be missed, never falsely reported, because `prove` checks on the full DB.
