# TA2: acceptance tests, wave 2 (C4 to C6)

- Branch: `test/01-wave2` (rebased on `bylaw/build` 36cbefa, contracts v1.2)
- Files: `tests/acceptance/test_wave2_audit.py`, `tests/acceptance/test_wave2_proposer.py`. There is no conftest change, so this branch does not conflict with `test/01-wave1`.
- Written blind from `docs/plan/01-engine/requirements.md` and `contracts.md` (v1.2). Domain facts come from `.context/tau2-bench`: clock 2024-05-15T15:00:00, 41 reservations created in the last 24h, and deterministic reservation and payment ids.

## Tests per requirement (29: 26 offline, 3 live)

| Req | Tests | Notes |
|---|---|---|
| REQ-EX1-1 | 7 | Validates against `REPORT_SCHEMA`, and the schema rejects broken reports. The C4 shape is checked field by field: each entry has `key == goal:target_id`, keys are unique, and `diff` has the v1.2 shape. The run has mode `bfs`, budget 2000, and 0 LLM calls and tokens. At least 3 Class A holes, all on Class A goals, including G1, G2 and G5. |
| REQ-EX1-2 | 3 | Every step and every verdict is ok, `goal_true` is true, `replays == "5/5"`, and the diff is not empty. The same checks run on the budget-25 run. |
| REQ-EX1-3 | 3 | No hole is a cancel then rebook (same user) of a reservation created less than 24h before `now`. At least one such chain is under `ambiguities`. Ambiguities are class C. |
| REQ-EX1-4 | 4 | `replay(domain, chain)`: every step ok, and the diff equals the report's `diff` on two replays. The report diff equals the diff computed from C1 snapshots before and after the chain. Two runs on fresh C1 envs give the same result, and `Goal.check` holds. A replay does not leak into the next fresh env. |
| REQ-PR1-1 | 1 live | `audit` with the LLM at budget 2000: its hole keys include every key found by `--no-llm`. |
| REQ-PR1-2 | 1 offline + 1 live | Offline: `bench --modes bfs --budget 30` follows the v1.2 JSON schema, has a single bfs row with `holes == len(hole_keys)`, 0 LLM calls, 0 tokens and `0 < tool_calls <= 30`, and prints the table. Live: `--modes bfs,muse` writes both rows, and the muse row has `llm_calls > 0`. |
| REQ-PR1-3 | 9 (1 live) | CLI: `stats.tool_calls <= 2000` by default, and `0 < tool_calls <= 25` with `--budget 25`. `search(use_llm=False)` at budgets 0, 1, 7 and 40: the summed write steps stay within the budget, depth is at most 4, and only WRITE tools appear. A live variant runs with `use_llm=True`. |

## State on `bylaw/build` (36cbefa)

All 26 offline tests are red. 25 error at setup because `bylaw.domain`, `bylaw.executor`, `bylaw.report`, `bylaw.proposer` and `bylaw/rulesets/airline.json` do not exist yet. The offline bench test fails because there is no `bylaw` CLI. Output: `.scratch/after/test-01-wave2/acceptance-before.txt`. Every EX1 and PR1 requirement is named by a test (`trace.txt`).

## Contract gaps

All gaps found in the first pass are closed by v1.2. Two readings remain:
- A bench row's `holes` is taken to be the count of `hole_keys`.
- The tests require at least one cancel+rebook chain inside the 24h window under `ambiguities`. The REQ-EX1-3 text implies this rather than stating it.
