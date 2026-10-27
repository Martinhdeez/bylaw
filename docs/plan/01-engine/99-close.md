# 01 — Close

Integration branch at `1198d7a`; gate: `make check` (via `harness-gate`) green on 2026-10-27 (363 passed, reviewer of PR #13).

## Delivered

| Id | Item | Pull request | Change note |
|---|---|---|---|
| Fix | Spike output determinism | #3 | `.artifacts/tested/2026-10-26-spike-determinism.md` |
| OP1 | Reproducible tau2 setup (`make setup`) | #6 | `.artifacts/tested/2026-10-26-op1-setup.md` |
| EN1 | Rule checker (C2) + airline RuleSet + Domain (C1) | #4 | `.artifacts/tested/2026-10-26-en1-rules.md` |
| EN2 | Rule evaluation budget (thread-safe), cross-process determinism, gold baseline 0/43 | #8 | `.artifacts/tested/2026-10-27-en2-eval-limits.md` |
| CP1 | Muse policy compiler + match_rate | #1 | `.artifacts/tested/2026-10-26-cp1-compiler.md` |
| RT1 | Retail domain plug-in, goals R1–R8 pre-registered | #5 | `.artifacts/tested/2026-10-26-rt1-retail.md` |
| EX1 | Executor, verifier, report, `audit --no-llm` | #9 | `.artifacts/tested/2026-10-27-ex1-executor.md` |
| PR1 | Muse proposer + `bench` | #13 | `.artifacts/tested/2026-10-27-pr1-proposer.md` |
| UI1 | Web prototype (approved) → implementation (UI2) | #2, #15 | `.artifacts/tested/2026-10-27-ui2-wire.md` |
| TA1/TA2 | Acceptance tests wave 1 / 2 | merged with #4, #5, #1, #9, #13 | — |

## Measured

| What | Value | Command | Output |
|---|---|---|---|
| Compiler match rate vs hand airline RuleSet | 0.643 by parts / 0.607 strict (one live compile, 28 hand rules) | `python -m bylaw compile --domain airline -o <file>` + `match_rate` | CP1 evidence `live-compile-v4.txt` |
| Hand RuleSet vs airline gold | 0/43 blocked, 1 unknown (task 39) | `python -m bylaw backtest --domain airline` | EN2 review |
| Blind BFS audit, airline, budget 2000 | 15 findings (pre-v1.7 all "Class A"; G1, G2, G5), 2 Class C, ~170–210 s | `python -m bylaw audit --domain airline --no-llm` | EX1/GA1 reviews |
| Bench Muse vs BFS (one run per budget, c4c136f) | Class A count Muse ≥ BFS at 25/50/100/200/2000 (2/1, 4/4, 8/7, 38/9, 18/15); ~185k tokens, 7 LLM calls per Muse run | `python -m bylaw bench --domain airline --budget <n> --modes bfs,muse` | PR1 evidence `bench-summary.txt` |

## Not measured

- Variance between Muse runs: one run per budget; a previous sweep gave 147 Class A at 2000 vs 18 in this one.
- Compiler precision (extra compiled rules) and a live retail compile.
- Per-audit token counts (process-wide counter).

## Parked

- M1 target "compiler matches ≥90% of hand rules": unmet (0.643). Reopen with few-shot prompts or by reviewing which of the 10 unmatched hand rules are judgement calls.
- Retail Muse search (templates are airline-only).

## Findings for the next iteration

- **τ² gold sanctions the airline chains** (tasks 7, 18, 25, 32): decision `docs/plan/decisions-2026-10-27-gold-adjudication.md`, contract v1.7, implemented by GA1.
- The rule language needed four hardening rounds (EN2); the threat model is "Muse writes, a human ratifies".

## Lessons for the harness

| Lesson | Evidence | Proposed edit (file) | Approved |
|---|---|---|---|
| Reviewers merged onto a moved integration branch without re-gating the merged tree | PR #12 merged after AP1 #11 → red `bylaw/build`; reviewer of #12 reported the same mistake twice | `harness:reviewer` agent: "Before merging, merge with the current integration head and run the gate on that exact tree; re-gate if the head moves." | pending |
| Tests that pass whatever the code does ("decoration") reached review repeatedly | CP1 (4 surviving mutants), RT1 (Class C goals), PR1 (M3, M4), GA1 (5/5 filter, `_extends`) | `harness:builder` agent: "For each new test, break the code it guards once and show it goes red, saved in evidence." | pending |
| Two parallel reviews touching the same modules | AP1 #11 and AM1 #12 reviewed in parallel, merged on top of each other | `## Harness` in AGENTS.md: "Items that edit the same module are reviewed and merged one at a time." | pending |

## Open for the user

- Confirm or reverse the gold-adjudication decision (Class B).
- Accept the 0.643 compiler match rate for the demo, or schedule more prompt work.
