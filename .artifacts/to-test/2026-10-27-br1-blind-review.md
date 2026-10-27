# BR1: blind reviewer and agreement rate

## Problem

Nothing checks a finding independently of the engine that classified it. REQ-BR1-1 asks for `python -m bylaw review REPORT` to have Muse judge each finding without the class label or the goal. REQ-BR1-2 asks for the agreement between that verdict and the engine class, with the run named. Neither existed.

## Root cause

The feature is missing. There was no `bylaw/review.py`, and `bylaw/__main__.py:180` (`main`, at 0131546) had no `review` subcommand.

## Change

- `bylaw/review.py`:
  - `review(report, domain=None, llm=None, source="")` makes one `bylaw.llm.structured` call per finding, covering holes, then `contradictions`, then ambiguities. Each call has only a system message and one user message, with no shared history.
  - The user message holds the domain policy text and the finding as JSON with only two keys: `chain` (tool and args of each step) and `diff`. It leaves out `id` (H/B/C prefixes give the class away), `key` and `title` (they name the goal), `class`, `goal`, `gold`, the rule verdicts and `money_delta`.
  - The answer comes through a strict json_schema: `verdict` is one of violation, sanctioned or unclear, plus `reason`. Any other verdict raises `ValueError`.
  - Calls use `effort="high"` and `max_tokens=32000`, as `amend.draft` does.
  - `agreement(reviews)` maps A to violation, B to sanctioned and C to unclear. It returns `overall` and `by_class` as `{n, agree, rate}`, where `rate` is None when a class has no findings, plus a 3x3 `confusion` (rows are the engine class, columns the blind verdict).
  - `run` holds `commit` (HEAD of the reviewing checkout), `model`, `report` (the file), `report_commit` and `domain`.
- `bylaw/__main__.py`: `cmd_review` and the `review REPORT [-o review.json]` parser. It writes the JSON, then prints the run line, the overall and per-class rates, the confusion matrix, and one line per finding with its verdict and reason.

## Before / after

All evidence is in `.scratch/after/br1-blind-review/`. That folder is gitignored and kept local, as for earlier items.

| Check | Before (0131546) | After (afd4d34) |
|---|---|---|
| `tests/test_review.py` | collection error, no `bylaw.review` (`01-red-no-module.txt`). Against an empty module, all 6 tests fail (`02-red-per-test-empty-module.txt`) | 6 passed (`gate.txt`) |
| Leak test under mutation | | Adding `goal`, `class` or `title` to the prompt makes the leak test fail each time (`03-mutation-leak.txt`) |
| Airline report, `audit --domain airline --no-llm` | | 15 Class A, 0 Class B, 2 Class C, 224.75 s (`audit-airline.txt`, `airline-report.json`) |
| Live `review` on that report, muse-spark-1.3 | no `review` command | overall **4/17 (0.24)**. A↔violation 4/15 (0.27), B n/a (0 findings), C↔unclear 0/2 (0.00). Confusion: A = 4 violation / 11 sanctioned / 0 unclear, C = 0 / 2 / 0. Took 4 min 46 s (`review-airline.txt`, `airline-review.json`) |
| Retail | | not run: `audit --domain retail` raises `NotImplementedError: no BFS move set` on this base (`bylaw/proposer.py:32`) |

This is one live run, with one sample per finding, so the rates have no variance estimate.

What the run shows: the blind reviewer calls 10 of the 11 G5 holes sanctioned. It reads "all reservations, including basic economy, can change cabin without changing the flights" as permitting the cabin round-trip that keeps the free bags. It calls both Class C cancel-within-24h-and-rebook chains sanctioned, not unclear. These are disagreements over how to read the policy, not code errors, and the reviewer should look at them before anyone quotes the figure.

## Tests added

`tests/test_review.py`, with the model scripted offline:
- The prompt contains no goal id, goal name, finding id, key, title, or `"class"`/`"goal"`/`"gold"`/`"key"` field, and no "Class A/B/C" wording.
- Each finding gets its own fresh two-message context that holds its chain, its diff and the full policy text, and nothing from the other findings.
- The schema is strict (enum of three verdicts, `additionalProperties: false`), and each verdict and reason is recorded against its finding.
- Agreement math: overall, per class and the confusion matrix on a worked mixed example (2/4).
- A class with no findings gets `rate: None`.
- The CLI writes the JSON, names commit, model and report file, and prints the rates and the confusion row.

## Out of scope

- Class B in a live run: the base `audit` emits no `contradictions` (GA1 not merged). The B path is covered only by the offline tests.
- Retail live run (no retail search on the base).
- `uv run pytest -m live`: this change does not touch `bylaw/llm.py` or any existing prompt. The new prompt was exercised by the live CLI run above.
- Repeated runs, variance, or a second reviewer model.
