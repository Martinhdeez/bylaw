# SR1: BFS search for retail, R6 double refund as Class A

## Problem

REQ-SR1-1 requires that `audit --domain retail --no-llm` runs and proves the R6 over-refund (switch a pending order's payment method, then cancel it) as Class A. The search had no retail move set, and the hole key and `money_delta` only knew airline reservations.

## Root cause

- `bylaw/proposer.py:22` (c845d16): `search` raised `NotImplementedError` for every domain except airline.
- `bylaw/report.py:96` (c845d16): the hole key target was `reservation_id` or `user_id`, never `order_id`.
- `bylaw/report.py:51`: `money_delta` read `reservations` only.
- `bylaw/report.py:45`: `classify` indexed `db["reservations"]`.

## Change

- `bylaw/proposer.py`:
  - `DOMAINS` maps each domain to its pool, state and move functions, plus the move kinds that are never repeated back to back. The airline search is unchanged.
  - Retail pool: orders from `domain.targets`, grouped by status. Within a status, orders whose user has two or more payment methods come first.
  - Retail moves for each order, with ids from the DB:
    - cancel ("no longer needed");
    - modify the address;
    - switch payment to each other method of the user;
    - modify items, and exchange items: first item to another available variant, paid with the original method;
    - return the first item to the original method;
    - modify the user's address.
- `bylaw/report.py`:
  - `_target` takes the first `reservation_id` or `order_id` the chain names, else the user.
  - `money_delta` also reads retail orders: a `refund` line counts as paid out, any other line as charged.
  - `classify` tolerates a DB without reservations.
- `tests/test_api.py` (scope added by the orchestrator): the error-event test used retail as its "no move set" domain. It now patches `bylaw.report.search` to raise.
- `tests/acceptance/test_v17_gold.py`: the test author's file (origin/test/03-product 074e75e), brought in unchanged. It holds both the REQ-GA1 and the REQ-SR1-1 tests.

## Before / after

| Check | Before (GA1, PR #16, ab6eeaa) | After |
|---|---|---|
| `audit --domain retail --no-llm` | `NotImplementedError` (`.scratch/after/sr1-retail-search/red.txt`) | 1 Class A hole, `R6:#W1068289`: payment switch then cancel, 5/5, money_delta 10359.84; 1 Class C (R5) (`.scratch/after/sr1-retail-search/audit-retail-stdout.txt`) |
| Retail wall-clock, budget 2000 | n/a | 77.02 s real; 741 chains, 309 executed tool calls (the budget is charged on yielded steps until PR1's v1.8 feedback lands) (`audit-retail-stderr.txt`, `audit-retail-stdout.txt`) |
| Blind `test_v17_gold.py` REQ-SR1-1 tests (local only) | 2 errors on GA1 (`.scratch/after/ga1-gold/acceptance-v17.txt`) | 10 passed (`.scratch/after/sr1-retail-search/acceptance-v17.txt`) |

## Tests added

- `tests/test_retail_search.py`:
  - retail chains are write-only, depth ≤ 4, within budget, and name real orders or users;
  - moves name real payment methods and real product variants;
  - on #W1068289, payment switch then cancel is Class A R6, replays 5/5, is not gold-sanctioned, and has a positive money_delta;
  - every key names the order.

## Out of scope

- Stacked on GA1 (PR #16), which is not merged.
- Dead-prefix pruning (no new chain starting with a prefix that already stopped) was tried and dropped. It needs the search feedback that v1.8 gives to PR1. No evidence of that run is kept.
- The 5 `test_wave2_audit.py` failures from GA1 remain (v1.7 makes the airline holes Class B).
- Retail moves use the first item only and a fixed test address; no move picks a cheaper or dearer variant on purpose.
