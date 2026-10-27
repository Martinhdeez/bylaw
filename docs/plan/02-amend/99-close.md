# 02 — Close

Integration branch at `1198d7a`; gate green on 2026-10-27.

## Delivered

| Id | Item | Pull request | Change note |
|---|---|---|---|
| BT1 | Gold loader + backtest | #7 | `.artifacts/tested/2026-10-26-bt1-backtest.md` |
| AM1 | Muse amendment drafter + closure proof + `amend` CLI | #12 (+ fix #14) | `.artifacts/tested/2026-10-27-am1-amend.md` |
| TA3 | Acceptance tests 02 | merged with #7, #12 | `.artifacts/tested/2026-10-26-ta3-acceptance-02.md` |

## Measured

| What | Value | Command | Output |
|---|---|---|---|
| Airline amendments (one live run, 74fce98) | 15/15 close their goal; 14 block exactly the gold task that sanctions the goal (18, 7 or 32); the broad G1 amendment blocks 5 (7, 17, 22, 32, 44); baseline 0/43 | `python -m bylaw amend report.json` | AM1 evidence `amend-table.md`; reviewer reproduced 3 rows |

## Not measured

- Combined backtest of all amendments together; Muse variance; retail amendments; money saved per amendment.

## Parked

- `amend` writes output only at the end (42-min run); incremental save.
- Retry test does not check the retry message (decoration).

## Findings for the next iteration

- Amendments on Class B findings show the policy-vs-practice trade-off directly: closing the gap blocks the gold task that does it.

## Lessons for the harness

See 01 close (same patterns).

## Open for the user

- None beyond 01.
