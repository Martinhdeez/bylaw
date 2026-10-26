# 02 — Amendments + backtest (M2)

## Goal of the increment

For every Class A hole in a report, Muse Spark drafts an amendment: a policy sentence plus a C2 rule patch. Bylaw then proves the amendment closes the hole (re-auditing with the patched RuleSet finds 0 holes for that goal) and measures what it costs: the τ² gold tasks are replayed through the patched checker and counted as blocked when an honest gold action would be rejected. The output is an amended report.

## Starts from

Iteration 01 contracts C1–C6 (frozen v1.1). Items run against the contracts while 01 finishes; merge order follows dependencies.

## Items

| Id | Item | Type | Weight | Agent | Depends on | Requirements |
|---|---|---|---|---|---|---|
| BT1 | Gold-task loader + backtest | feature | full | builder | C1, C2 | REQ-BT1-1..3 |
| AM1 | Amendment drafter (Muse) + closure proof | feature | full | builder | C2, C4, EX1 | REQ-AM1-1..3 |
| TA3 | Acceptance tests 02 | tests | full | test-author | contracts | all |

## Waves

BT1, AM1 and TA3 in parallel. AM1's closure proof needs EX1 merged; it may stub the call until then.

## Out of scope

The UI for amendments (iteration 03), proxy enforcement (iteration 04).
