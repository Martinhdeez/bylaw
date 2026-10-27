# 01 — Requirements and verification

| Id | Requirement | Checked through |
|---|---|---|
| REQ-EN1-1 | Given a RuleSet (C2) and a tool call, `bylaw.rules.check` returns one verdict per rule of that tool. The call is allowed iff all verdicts are ok. | `bylaw.rules.check` |
| REQ-EN1-2 | Expressions that use names or syntax outside the C2 whitelist (imports, attribute access to dunders, calls to non-whitelisted functions) are rejected with `RuleError`, never executed. | `bylaw.rules.validate` |
| REQ-EN1-3 | The airline hand RuleSet (`bylaw/rulesets/airline.json`) rejects a cancellation of a basic-economy, uninsured reservation booked more than 24h before `now`, with reason "change of plan", and allows it within 24h. | `bylaw.rules.check` with `get_domain("airline")` |
| REQ-CP1-1 | `compile_policy(domain)` returns a dict valid against the C2 JSON schema. | `bylaw.compiler.compile_policy` (live) |
| REQ-CP1-2 | `match_rate(compiled, hand)` returns a float in [0,1]. It is 1.0 when called with the hand RuleSet on both sides. | `bylaw.compiler.match_rate` |
| REQ-CP1-3 | `uv run python -m bylaw compile --domain airline -o X.json` writes a valid RuleSet and prints the match rate. | CLI |
| REQ-RT1-1 | `get_domain("retail")` returns a Domain (C1) whose `fresh_env()` gives independent DB copies: a write in one does not change another. | `bylaw.domain.get_domain` |
| REQ-RT1-2 | Retail goals are registered with ids, policy references and class. Every goal is false on the untouched DB. | `Domain.goals` |
| REQ-RT1-3 | `bylaw/rulesets/retail.json` is valid against C2. | `bylaw.rules.validate` |
| REQ-EX1-1 | `audit --domain airline --no-llm` writes a report valid against C4 with ≥3 Class A holes. | CLI + report schema |
| REQ-EX1-2 | Every Class A hole in a report has all step verdicts ok, `goal_true` true, and replays "5/5". | report JSON |
| REQ-EX1-3 | Cancel+rebook chains through the 24h window are reported under `ambiguities` (Class C), not `holes`. | report JSON |
| REQ-EX1-4 | Re-running a hole's chain on a fresh env reproduces the same DB diff. | `bylaw.executor.replay` |
| REQ-PR1-1 | `audit --domain airline` (LLM on) finds at least the holes `--no-llm` finds, at the default budget (2000; see contracts v1.8). | CLI |
| REQ-PR1-2 | `bench --domain airline --budget N` prints a table with holes found, tool calls, LLM calls and wall time, for `bfs` and `muse` modes, and writes it to JSON. | CLI |
| REQ-PR1-3 | Search is bounded: no run exceeds `--budget` tool calls. | report `stats.tool_calls` |

## What is verified, and how

| Surface | Items | Check | Test branch |
|---|---|---|---|
| Python API + CLI | EN1, CP1, RT1 | `tests/acceptance/test_wave1_*.py` | `test/01-wave1` |
| CLI + report JSON | EX1, PR1 | `tests/acceptance/test_wave2_*.py` | `test/01-wave2` |

Live-API checks are marked `@pytest.mark.live`.

## Closed to the test author

`bylaw/*.py` implementations, `bylaw/env/`, `spike/`, `tests/test_*.py` (unit tests). Readable: this plan folder, `contracts.md`, the spec, `bylaw/rulesets/*.json` once merged, and `.context/tau2-bench` (the simulator).

## Added with contracts v1.7 (gold adjudication)

| Id | Requirement | Checked through |
|---|---|---|
| REQ-GA1-1 | `bylaw.gold.gold_goals(domain)` returns `{goal_id: [task_id, ...]}` for every goal some gold task makes true (airline: G1←32, G2←7, G4←25, G5←18). | `bylaw.gold` |
| REQ-GA1-2 | Every report entry carries `class` and `gold: {sanctioned, tasks}`; `holes` holds Class A only (no gold-sanctioned goal), gold-sanctioned findings go to `contradictions` (Class B); C entries keep their list and carry `sanctioned` for their goal. | `audit` report JSON |
| REQ-GA1-3 | The goal of a ratified amendment is the goal prefix of its `hole_key` (`G1:T1QOBS` → `G1`). | `bylaw.ratified`, proxy |
| REQ-SR1-1 | `audit --domain retail --no-llm` runs and proves the R6 payment-switch-then-cancel over-refund as Class A. | CLI + report |
