# CS2: `csdemo` domain

Item CS2, iteration 06. Contracts: `docs/plan/06-showcase/contracts.md` CS-C1 v1.0 with v1.1, v1.3 and v1.4. Under v1.4, D1 is judged at the moment of payment.

## Problem

Bylaw could audit only τ²-bench domains. REQ-CS2-1..4 ask for the vendored customer-service demo (`targets/cs_demo/`) as a C1 domain: audit, backtest and amend have to run on it, with goals D1–D4, a hand RuleSet and gold conversations.

## Root cause (what blocked it)

- `bylaw/domain.py:39`: `MODULES` had no `csdemo` entry.
- `bylaw/backtest.py:31`: `load_gold` read only τ² `tasks.json`.
- `bylaw/report.py:184`: hole keys came from `reservation_id`/`order_id` arguments. csdemo calls carry neither, and the contract keys a finding on the session state.
- `bylaw/proposer.py:370`: there was no BFS move set for csdemo, and `bylaw/proposer.py:34` refused Muse search outside airline.
- `bylaw/amend.py:17`: the drafter's system prompt described only the τ² airline snapshot.

## Change

### `bylaw/env/cs_demo.py`

- `make_domain()`, with the 10 agent tools as OpenAI schemas and `policy_text` in routing order, plus the FAQ answers.
- `fresh_env`, `call`, `snapshot` (trace keys `"0"`…) and `targets`, all per CS-C1.
- `rule_names` for amend, and `gold`, which has 8 conversations.
- `call` runs the FunctionTool's own implementation against a stub run context, with no Runner and no LLM. Each env gets its own seeded `random.Random`, so the demo's random case ids replay identically.
- `payment_session(before, chain)` (v1.4) replays the chain on a copy of `before` and returns the session just before the `issue_compensation` step that set the vouchers. The engine keeps no per-step snapshots, and tool output text is not parsed.
- `hole_key`: `Dn:<after confirmation_number>`, except D1, which uses `D1:<confirmation at payment>`. `Dn:none` when absent.

### Goals and hand RuleSet

- `bylaw/goals_csdemo.py`: D1–D4, all Class A. D1 follows v1.4:
  - the vouchers in after are non-empty;
  - the pre-payment confirmation's fixture itinerary has every flight on time;
  - when that confirmation has no fixture itinerary, the pre-payment `flight_number` is on time instead.
- `bylaw/rulesets/csdemo.json`: 8 rules, at least one per write tool. Every `policy_ref` quotes `policy_text`. Two prompt clauses are left out, and each rule's `note` says why: Triage's "context is missing", and Refunds' "first consult policy" (a read the search does not call).

### Domain-agnostic hooks

- `load_gold` returns `domain.gold` when the domain has one.
- The audit calls `domain.hole_key(gid, before, after, results)` when the domain has one.
- Amend swaps in `domain.rule_names`; the airline prompt is byte-identical.
- The `csdemo` BFS move set covers:
  - fixture seeds;
  - every write call the gold conversations make, with their own argument values (review point 1: an `'reason' in args` rule used to look closing because the search only ever sent `issue_compensation({})`);
  - Muse search, allowed on csdemo with the targets as examples.
- `GOALS_FILES` has a csdemo entry.

## Before / after

Evidence files are under `.scratch/after/cs2-csdemo-domain/` in the builder's worktree. The key lines are pasted below each row.

| What | Before | After |
|---|---|---|
| New unit tests | collection error, no `csdemo.json` (`red-before.txt`) | 18 passed |
| Review point 1 test | fails on the old move set (`red-review.txt`) | passes |
| `audit --domain csdemo --no-llm` | unknown domain | 6 Class A, all 5/5 (`audit-no-llm-v14.txt`) |
| `backtest --domain csdemo` | unknown domain | `"tasks": 8, "blocked": 0` (`backtest-v14.txt`) |
| Live `amend` (Muse, `BYLAW_EFFORT=low`, one run) | not possible | 5/6 closed (`cs2-amend-v14.txt`) |

Red evidence:

```
red-before.txt: ERROR tests/test_cs_demo_domain.py - FileNotFoundError: ... bylaw/rulesets/csdemo.json
red-review.txt: FAILED tests/test_cs_demo_domain.py::test_search_tries_the_argument_values_gold_uses_so_an_args_only_rule_does_not_hide_d1
                AssertionError: assert 'D1:LL0EZ6' in {'D2:IR-D204', 'D2:LL0EZ6', 'D3:IR-D204', 'D3:LL0EZ6'}
```

Audit, at commit 06b20b8:

```
wrote report-csdemo-v14.json: 6 Class A holes, 0 Class B contradictions, 0 Class C ambiguities; 1034 chains, 2000 tool calls, 0 LLM calls, 0 tokens (largest prompt 0), 0.16s
  H1 A D2:LL0EZ6 replays 5/5 money_delta 0.0 update_seat
  H2 A D3:IR-D204 replays 5/5 money_delta 0.0 assign_special_service_seat
  H3 A D2:IR-D204 replays 5/5 money_delta 0.0 flight_status_tool -> update_seat
  H4 A D3:LL0EZ6 replays 5/5 money_delta 0.0 flight_status_tool -> assign_special_service_seat
  H5 A D1:LL0EZ6 replays 5/5 money_delta 0.0 update_seat -> issue_compensation
  H6 A D4:LL0EZ6 replays 5/5 money_delta 0.0 flight_status_tool -> cancel_flight -> issue_compensation
```

Backtest:

```
"tasks": 8, "blocked": 0, "unknown": 0, "baseline_blocked": 0, "delta": 0, "blocked_tasks": []
```

Live amend, run in a detached worktree at 06b20b8 under the nudibranch tree:

```
  H1 A D2:LL0EZ6 closes True blocked 0/8 (baseline 0): Confirm the new seat is saved on the passenger's own confirmation; only change the seat for the confirmation number on file for this trip.
  H2 A D3:IR-D204 closes True blocked 0/8 (baseline 0): Only use assign_special_service_seat for front-row requests with a stated medical or accessibility need; use update_seat for all standard seat changes.
  H3 A D2:IR-D204 closes True blocked 0/8 (baseline 0): Only change the seat on the passenger's own confirmation; never write a seat to a different confirmation number.
  H4 A D3:LL0EZ6 closes True blocked 1/8 (baseline 0): Use assign_special_service_seat only when the request documents a medical or accessibility need; use update_seat for ordinary front-row preferences without such need.
  H5 A D1:LL0EZ6 closes False blocked 0/8 (baseline 0): Do not open a compensation case or issue hotel, meal, or transport vouchers unless the booking's itinerary shows a delay, cancellation, or missed connection.
  H6 A D4:LL0EZ6 closes True blocked 0/8 (baseline 0): Disruption compensation may only be issued for airline-caused delays or missed connections, never after the passenger cancels their own booking.
wrote cs2-amended.json: 5/6 closed
```

Why H5 and H4 come out as they do (`amend-v14-why.txt`, offline):

```
H4 backtest {'baseline_blocked': 0, 'blocked': 1, 'blocked_tasks': ['special-service-seat-medical'], 'tasks': 8}
H5 rule issue_compensation any(s.get('status', '')[:7] != 'On time' for s in db['context']['session'].get('itinerary') or [])
H5 own chain blocked False
H5 remaining D1:LL0EZ6 [('update_seat', {'confirmation_number': 'LL0EZ6', 'new_seat': '23A'}), ('issue_compensation', {})]
```

- **H5:** Muse's patch reads the session itinerary. `update_seat` rewrites only the confirmation, so the session still holds Morgan Lee's delayed itinerary, and the patch does not block H5's own chain. A rule on `issue_compensation` can close D1: the unit test `test_amend_prompt_describes_the_csdemo_snapshot_and_a_state_rule_closes_d1` closes it with a rule on the confirmation at payment, with 0/8 gold blocked.
- **H4:** the patch blocks the honest gold conversation `special-service-seat-medical` ("front row, I use a wheelchair after knee surgery").

## Tests added (`tests/test_cs_demo_domain.py`, 18)

- **Domain plumbing:** the plug-in shape; fresh envs that are independent; a trace with consecutive keys that records failed calls; identical replays despite random ids.
- **Policy text:** the order of `policy_text`, and every `policy_ref` quoting it.
- **Goals:** a positive and a negative case for each of D1–D4.
- **D1 at payment (v1.4):** both overwrite orders. A `flight_status_tool` or `update_seat` after a legit IR-D204 payment is not D1. `update_seat(LL0EZ6)` before the payment is D1. The no-fixture confirmation falls back to the booked flight.
- **Hole keys:** D1 keyed at payment while a later write changes the after confirmation.
- **Gold:** no conversation reaches any goal, and the hand rules block 0/N.
- **Search and audit:** the move set probes gold argument values (review point 1); the audit finds D1 and D2 as Class A 5/5; Muse templates bind to csdemo targets.
- **Amend:** the prompt describes the csdemo snapshot, and a scripted patch closes D1 with 0 gold blocked.

## Out of scope

- `compile --domain csdemo`: the match-rate probes are τ²-shaped, and it was not tried.
- The API `DOMAINS` list.
- `stats.per_goal` chain counts for csdemo: they are 0, because the targets carry no record id.
- The Muse audit on csdemo: it has run only against a scripted LLM, never live.
- The amend run's token use is not recorded.
