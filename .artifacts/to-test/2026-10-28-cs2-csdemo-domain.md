# CS2: `csdemo` domain

Item CS2, iteration 06. Contracts: `docs/plan/06-showcase/contracts.md` CS-C1 v1.0 with the v1.1 clarifications.

## Problem

Bylaw could audit only τ²-bench domains. REQ-CS2-1..4 ask for the vendored customer-service demo (`targets/cs_demo/`) as a C1 domain: audit, backtest and amend have to run on it, with goals D1–D4, a hand RuleSet and gold conversations.

## Root cause (what blocked it)

- `bylaw/domain.py:39`: `MODULES` had no `csdemo` entry.
- `bylaw/backtest.py:31`: `load_gold` read only τ² `tasks.json`.
- `bylaw/report.py:184`: hole keys came from `reservation_id`/`order_id` arguments. csdemo calls carry neither, and v1.1 keys a finding on the after state's confirmation.
- `bylaw/proposer.py:370`: there was no BFS move set for csdemo, and `bylaw/proposer.py:34` refused Muse search outside airline.
- `bylaw/amend.py:17`: the drafter's system prompt described only the τ² airline snapshot.

## Change

- `bylaw/env/cs_demo.py`, a new module. It holds `make_domain()`, the 10 agent tools as OpenAI schemas, `policy_text` in routing order with the FAQ answers, and `fresh_env`, `call`, `snapshot` and `targets`, all per CS-C1. It also holds the `hole_key` hook (v1.1), `rule_names` for amend, and `gold`, which has 8 conversations.
- `call` runs the FunctionTool's own implementation against a stub run context, with no Runner and no LLM. Each env gets a seeded `random.Random`, swapped into the demo's `tools.random` under a lock, so the random case ids and confirmations replay identically (5/5).
- `bylaw/goals_csdemo.py`: D1–D4, all Class A.
- `bylaw/rulesets/csdemo.json`: 8 rules, at least one per write tool. Every `policy_ref` quotes `policy_text`. Two prompt clauses are left out on purpose, and each rule's `note` says why: Triage's "context is missing" and Refunds' "first consult policy".
- Domain-agnostic hooks:
  - `load_gold` returns `domain.gold` when the domain has one.
  - The audit uses `domain.hole_key` when the domain has one.
  - Amend swaps in `domain.rule_names`; the airline prompt is byte-identical.
  - The proposer has the `csdemo` BFS move set, and Muse search is allowed on csdemo, with the targets as examples.
  - `GOALS_FILES` has a csdemo entry.

## Before / after

| What | Before | After |
|---|---|---|
| New unit tests | collection error, no `csdemo.json` (`.scratch/after/cs2-csdemo-domain/red-before.txt`) | 16 passed (`tests/test_cs_demo_domain.py`) |
| `audit --domain csdemo --no-llm` | unknown domain | 8 Class A, all 5/5, including D1:LL0EZ6 (the spike chain), D1:IR-D204, D2:LL0EZ6 and D2:IR-D204 (`.scratch/after/cs2-csdemo-domain/audit-no-llm.txt`, `report-csdemo.json`) |
| `backtest --domain csdemo` | unknown domain | `"tasks": 8, "blocked": 0` (`.scratch/after/cs2-csdemo-domain/backtest.txt`) |
| Live `amend` (Muse, `BYLAW_EFFORT=low`) | not possible | 8 amendments, each blocks 0/8 gold; 7/8 `closes` True; H6 D1:LL0EZ6 `closes` False (`.scratch/after/cs2-csdemo-domain/cs2-amend.txt`, `cs2-amended.json`) |

H6: its patch blocks its own chain. The D1 re-audit still finds D1:IR-D204, where `flight_status_tool(FLT-123)` rewrites the booked flight after the vouchers were issued. One amendment that sees only one chain does not close the whole goal.

## Tests added

`tests/test_cs_demo_domain.py`:
- the plug-in shape, fresh envs that are independent, and a trace with consecutive keys that records failed calls;
- identical replays despite random ids;
- the order of `policy_text`, and every `policy_ref` quoting it;
- a positive and a negative case for each of D1–D4, including the v1.1 rule that a booked NY950 is not on time;
- the v1.1 hole key;
- gold: no conversation reaches any goal, and the hand rules block 0/N;
- the audit finds D1 and D2 as Class A 5/5;
- the amend prompt describes the csdemo snapshot, and a scripted two-rule patch closes D1 with 0 gold blocked;
- Muse templates bind to csdemo targets.

## Out of scope

- `compile --domain csdemo`: the match-rate probes are τ²-shaped, and it was not tried.
- The API `DOMAINS` list, and `stats.per_goal` chain counts for csdemo (0, because the targets carry no record id).
- The Muse audit on csdemo has run only against a scripted LLM, never live.
