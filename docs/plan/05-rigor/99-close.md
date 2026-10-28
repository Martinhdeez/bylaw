# 05 — Close

Integration branch at `65f02e8`. Final gate: pending. The orchestrator runs harness-gate on bylaw/build before the close checkpoint.

## Delivered

| Id | Item | Pull request | Merge commit | Change note |
|---|---|---|---|---|
| LC1 | `audit --long-context`, `run.context_tokens`, per-audit `stats.tokens` (contracts v1.10) | #27 | `66db8e1` | `.artifacts/tested/2026-10-27-lc1-long-context.md` |
| BR1 | `review REPORT`: blind Muse verdict per finding, agreement rate and confusion matrix | #23 | `88cb339` | `.artifacts/tested/2026-10-27-br1-blind-review.md` |
| CV1 | `coverage REPORT [--json OUT]`, optional `stats.per_goal` (contracts v1.13) | #29 | `d597213` | `.artifacts/tested/2026-10-27-cv1-coverage.md` |
| UP1 | Draft of the upstream τ²-bench issue, not filed | #25 | `1dd1f7f` | `.artifacts/backlog/2026-10-27-upstream-tau2-issue-draft.md` |

## Measured

Each figure comes from one run. None of them is a rate over repeated runs.

| What | Value | Run | Source |
|---|---|---|---|
| LC1 long-context airline audit, budget 2000, default effort, `BYLAW_NO_CACHE=1`, at 48951c5 (before GA1) | context_tokens 25303, tokens 269046, 7 LLM calls, 0 errors, 1999 tool calls, 569.41 s | `python -m bylaw audit --domain airline --long-context` | LC1 change note, PR #27 (`live-audit.txt`) |
| LC1 two concurrent audits, fake client | A 7140 tokens, B 189 (old code: A 7329, both audits' calls) | `tests/test_long_context.py` | LC1 change note |
| BR1 agreement on a pre-GA1 airline report (15 A, 0 B, 2 C), muse-spark-1.3 | 4/17 (0.24); A↔violation 4/15, C↔unclear 0/2. Pre-GA1 classes, not current | `python -m bylaw review <airline-report.json>` | BR1 change note, PR #23 (`review-airline.txt`) |
| BR1, same verdicts re-scored onto post-GA1 classes (0 A, 15 B, 2 C, byte-identical prompts) | 11/17 (0.65); B↔sanctioned 11/15, C↔unclear 0/2 | reviewer `br1rev-rescore.py` | BR1 change note, reviewer note |
| CV1 airline offline BFS, budget 2000, at 4bdca67 | 0 A, 15 B, 2 C; 906 chains, 1997 tool calls, 232.57 s; per-goal table in the change note | `python -m bylaw audit --domain airline --no-llm` + `python -m bylaw coverage` | CV1 change note (`coverage-airline-4bdca67.txt`) |
| CV1 retail offline BFS, **budget 200**, at 4bdca67 | 1 A (R6), 0 B, 1 C (R5); 660 chains, 199 tool calls, 61.75 s | `python -m bylaw audit --domain retail --no-llm --budget 200` + `coverage` | CV1 change note (`coverage-retail-4bdca67.txt`) |
| UP1 retail R6 on τ² alone, #W1068289 | paid 6906.56, refunded 13813.12, gift card +10359.84 | commands in the draft's evidence table | UP1 draft, PR #25 |

## Not measured

- **LC1:** one live run only, with no variance. No baseline run without `--long-context` on the same commit, so the prompt-size gain is not known. The run predates GA1 (its 18 Class A count is pre-v1.7) and FX1 (default effort, not `BYLAW_EFFORT`). The C9 progress events still read the process-wide `llm.USAGE`.
- **BR1:** no new live run after GA1. The 0.65 figure re-scores the single pre-GA1 run. Retail was not run, because there was no retail BFS on the base at build time. There is one sample per finding and no second reviewer model.
- **CV1:** both tables were measured at 4bdca67, before FX2 (#28) and FX1 (#26) merged. No audit was re-run on the merged code. No Muse-mode run. Retail was measured at budget 200, not the default 2000.
- **UP1:** the draft is unfiled, and nothing has been confirmed upstream.

## Parked

- **SO1**, Muse Spark Open via Baseten: there is no Baseten key (plan M5a).
- Filing the UP1 issue upstream needs the user's approval.

## Findings for the next iteration

- **BR1 leak test is a name list.** It checks that given field names and wording ("goal", "class", "title", "Class A/B/C") are absent. A new field that gives the class away under another name would pass.
- **BR1 does not record the effort it sent.** It hard-codes `effort="high"`, and `run` names only commit, model, report, report commit and domain, so its output cannot be compared with FX1's `run.effort`.
- **BR1 policy reading.** The blind reviewer calls 10 of the 11 G5 holes and both Class C chains "sanctioned". Someone should look at that before anyone quotes the agreement figure.
- **CV1 retail at budget 200.** The retail table is not comparable with the airline one at 2000. A default-budget run is pending.
- **CV1 attributes by target, not intent.** G4, G5 and G7 rows equal the run totals because those goals target every reservation.
- **LC1 baseline.** A same-commit pair, with and without `--long-context`, is needed before anyone claims a gain.

## Deviation from the harness

This iteration had no blind test-author, because parallel gates were saturating the machine (`00-plan.md`). Each reviewer proved instead that the new tests fail on old code and under mutation. CV1 #29 records three such mutations, and BR1 #23 records the leak-test mutation.

## Lessons for the harness

| Lesson | Evidence | Proposed edit (file) | Approved |
|---|---|---|---|
| Contract changes surfaced only at review time, as proposals in the PR body, and the orchestrator had to write the contract text | LC1 #27 proposed `run.context_tokens` and `--long-context`, which became v1.10 (`966db43`). FX2 #28 proposed the C4 G7 key, which became v1.11 (`075a80b`). CV1 #29 proposed `stats.per_goal`, which became v1.13 (`3b31c3a`). All three change notes say "contract text is not edited" | `harness:iteration` skill, plan step: "For each item, decide in the brief whether it adds a field, a flag or a key to a contract; if so, freeze the contract text before dispatch, not after review." | pending |
| The base moved under long gates (around 40–55 min), so the same item was re-gated several times | SR1 #18 went through heads 7c05abc, 1e0dd57 and 0fc8caa, then the post-GA1 merge (the orchestrator counts 4 gated heads). FX2 #28 merged bylaw/build "again" after LC1 (3 heads, orchestrator count). CV1 #29 gated at e4d384c and 79a9184, then again at e1b4af4 after FX2 and FX1 | `harness:reviewer` agent: "Merge with the integration head once, then gate. If the head moves only by files outside the item's diff, record a merge-tree check instead of a new gate; the close gate covers the merged tree." | pending |
| Agents sharing a scratchpad overwrote each other's files | The FX2 PR body file was overwritten by another agent's (orchestrator report) | `harness:builder` and `harness:reviewer` agents: "Write PR bodies and evidence to a path that names the item id, e.g. `.scratch/<item>/pr-body.md`, never a shared fixed name." | pending |

## Open for the user

- Approve or decline filing the UP1 issue upstream.
- Provide a Baseten key to unpark SO1, or drop it.
