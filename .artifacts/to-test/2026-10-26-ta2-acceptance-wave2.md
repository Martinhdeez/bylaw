# TA2: acceptance tests, wave 2 (C4 to C6)

- Branch: `test/01-wave2` (from `bylaw/build` 3436f63)
- Files: `tests/acceptance/test_wave2_audit.py`, `tests/acceptance/test_wave2_proposer.py`. There is no conftest change, so this branch does not conflict with `test/01-wave1`.
- Written blind from `docs/plan/01-engine/requirements.md` and `contracts.md` (v1.1). Domain facts come from `.context/tau2-bench`: clock 2024-05-15T15:00:00, 41 reservations created in the last 24h, and deterministic reservation and payment ids.

## Tests per requirement (27: 24 offline, 3 live)

| Req | Tests | Notes |
|---|---|---|
| REQ-EX1-1 | 7 | Validates against `REPORT_SCHEMA` and checks that the schema rejects broken reports. Checks the C4 shape field by field, and that the run block has mode `bfs`, budget 2000 and 0 LLM calls/tokens. Expects ≥3 Class A holes, each on a domain goal with `cls == "A"`, and G1, G2 and G5 all found. |
| REQ-EX1-2 | 3 | Every step `ok` and every verdict ok, `goal_true` true, `replays == "5/5"`, and a non-empty diff. The same checks run on the budget-25 report. |
| REQ-EX1-3 | 3 | No hole is a cancel followed by a rebook for the same user of a reservation created less than 24h before `now`. At least one such chain is under `ambiguities`. Ambiguities are class C. |
| REQ-EX1-4 | 3 | `bylaw.executor.replay` is callable. Each hole chain is run twice on fresh envs through C1 (`fresh_env`/`call`/`snapshot`): every step ok, the after-snapshots are identical, the DB changed, and `Goal.check` is true. A replay does not leak into the next fresh env. |
| REQ-PR1-1 | 1 live | `audit` with the LLM at budget 2000: its hole goals include every goal found by `--no-llm`. Mode `muse`, `llm_calls > 0`. |
| REQ-PR1-2 | 1 live | `bench --budget 30 -o`: stdout names bfs and muse and has columns for holes, tool calls, LLM calls and time. The JSON mentions both modes. |
| REQ-PR1-3 | 9 (1 live) | CLI: `stats.tool_calls` ≤ 2000 by default, and 0 < `tool_calls` ≤ 25 with `--budget 25`. `search(use_llm=False)` at budgets 0/1/7/40: the total chain length stays within the budget, chains are non-empty, depth ≤ 4, and every tool is a WRITE tool. A live variant runs with `use_llm=True`. |

## State on `bylaw/build` (3436f63)

All 24 offline tests are red: 23 error at setup, because `bylaw.domain`, `bylaw.executor`, `bylaw.proposer` and `bylaw/rulesets/airline.json` do not exist yet. One test fails: `executor exposes replay`. The 3 live tests are deselected by default. Output: `.scratch/after/test-01-wave2/acceptance-before.txt`.

## Contract gaps

- **REQ-EX1-4:** the signature of `bylaw.executor.replay` is not in any contract, and C4 does not define the format of `diff`. The tests therefore check reproducibility through C1, and only check that `replay` exists. They do not check that the report's `diff` equals the replay's diff.
- **REQ-PR1-2:** C5 has no offline or `bfs`-only mode for `bench`, and the bench JSON has no schema. The whole bench test is live, and its JSON check is loose: it only looks for the two mode names.
- **REQ-PR1-1:** "the same holes" has no identity key. The test compares the sets of goal ids.
- **REQ-PR1-3 / C6:** the budget is read as the total number of WRITE steps across the yielded chains.
