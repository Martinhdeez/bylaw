# DM1 demo reports (2026-10-28)

Item DM1 (`docs/advance/checklist-03.md`), REQ-DM1-1. Each file is a single run, never a rate. Run sequentially in the worktree `.scratch/dm1wt`, model `muse-spark-1.3`, `BYLAW_EFFORT=low` (the user asked for low effort to save tokens; the README's documented efforts are higher).

## Files

| File | Command | Commit in `run` |
|---|---|---|
| `reports/airline.json` | `BYLAW_EFFORT=low uv run python -m bylaw audit --domain airline -o reports/airline.json`, then `BYLAW_EFFORT=low uv run python -m bylaw amend reports/airline.json -o reports/airline.json` | 05bd65c |
| `reports/retail.json` | `uv run python -m bylaw audit --domain retail --no-llm -o reports/retail.json` | 9f13ae2 (CV1) |
| `reports/airline.bench.json` | `BYLAW_EFFORT=low uv run python -m bylaw bench --domain airline --budget 200 -o reports/airline.bench.json` | 9f13ae2 (CV1) |

The airline audit ran before CV1 (#29) and FX3 (#31) merged, so it has no `stats.per_goal` and its coverage table shows `n/a` for chains and executed. It was not re-run for that. FX3 changes only how the G7 key is derived; the coordinator ruled no re-run was needed.

## Airline audit (`reports/airline.json`)

- `run`: mode `muse`, model `muse-spark-1.3`, effort `low`, budget 2000, goals_commit 00535e7, context_tokens 14427.
- `stats`: 924 chains, 1997 tool calls, 7 LLM calls, 0 llm_errors, 120756 tokens, 425.05 s.
- Class A 0, Class B 15 (G5 12, G1 2, G2 1), Class C 102 (G7 100, G1 2).
- Class B gold tasks: G5 → task 18 (12 entries), G1 → task 32 (2), G2 → task 7 (1). No G4 entry, so task 25 is not cited.
- Class C G1 entries C101 (G1:1KUOX2) and C102 (G1:PIM2PK), both `cancel_reservation -> book_reservation`, carry `gold.sanctioned: true, tasks: ["32"]`.

## Airline amend (same file)

- 15/15 entries got an amendment with `closes: true`. Baseline blocks 0/43 gold tasks.
- Backtest: 14 amendments block exactly one gold task (18 for the 12 G5 entries, 7 for B6 G2:1ERWZ8, 32 for B7 G1:01WQQ7). B5 G1:1ERWZ8 (no cabin change out of basic economy) blocks 5/43: 7, 17, 22, 32, 44.
- Wall time 1:22:03 (`time`). The amend CLI does not print Muse token usage, so amend tokens are not recorded.

## Retail audit (`reports/retail.json`)

- `run`: mode `bfs`, model null, budget 2000, goals_commit 02889fd.
- `stats`: 4509 chains, 1997 tool calls, 0 LLM calls, 0 tokens, 372.28 s.
- Class A 1 (H1 R6:#W1068289, `modify_pending_order_payment -> cancel_pending_order`, money_delta 10359.84), Class B 0, Class C 1 (C1 R5:#W1068289).
- Not amended. The brief asked for an offline audit only, because the Muse search is airline-only. REQ-DM1-1 names retail with amendments; that part is still open.

## Airline bench (`reports/airline.bench.json`, budget 200)

| mode | A | B | C | tool calls | LLM calls | tokens | seconds |
|---|---|---|---|---|---|---|---|
| bfs | 0 | 9 | 2 | 200 | 0 | 0 | 68.36 |
| muse | 0 | 7 | 48 | 199 | 7 | 0 | 117.4 |

The muse row shows 0 tokens because all 7 proposer requests matched the disk cache (`.cache/llm/`) from the audit above. Per v1.14 these are still counted calls, but nothing was billed. At this budget BFS found more Class B entries than Muse (9 vs 7).

## Coverage (`python -m bylaw coverage reports/<d>.json`)

Airline: chains and executed `n/a` (no per_goal). A/B/C per goal are G1 0/2/2, G2 0/1/0, G5 0/12/0, G7 0/0/100; G3, G4 and G6 are 0/0/0.

Retail:

| goal | chains | executed | A | B | C |
|---|---|---|---|---|---|
| R1 | 1812 | 962 | 0 | 0 | 0 |
| R2 | 2693 | 1031 | 0 | 0 | 0 |
| R3 | 2112 | 300 | 0 | 0 | 0 |
| R4 | 581 | 731 | 0 | 0 | 0 |
| R5 | 581 | 731 | 0 | 0 | 1 |
| R6 | 581 | 731 | 1 | 0 | 0 |
| R7 | 1812 | 962 | 0 | 0 | 0 |
| R8 | 2393 | 1693 | 0 | 0 | 0 |

## Against the gold-adjudication decision (2026-10-27)

- Tasks 7 and 32 appear only as Class B (G2, G1) and in two G1 Class C entries. This is consistent with the decision.
- G4 and task 25 do not appear. Consistent.
- Task 18 sanctions 12 Class B G5 entries. The addendum calls task 18 a policy gap, not a contradiction. The report still labels these entries Class B, so the demo wording must follow the addendum.

## Previous report

The untracked `reports/airline.json` (commit 2fa9fac, Muse, 18 B, 123 C) is kept for comparison in `.scratch/dm1wt/.scratch/old-reports/` and is not committed.
