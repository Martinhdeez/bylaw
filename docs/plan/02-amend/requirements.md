# 02 — Requirements

| Id | Requirement | Checked through |
|---|---|---|
| REQ-BT1-1 | `load_gold(domain)` returns the τ² tasks of that domain that have gold actions (airline: 43). Each task has an id and an ordered list of (tool, args). | `bylaw.backtest.load_gold` |
| REQ-BT1-2 | `backtest(domain, ruleset)` replays every gold action of every task on a fresh env through `rules.check`. It returns per-task `blocked: bool` plus the first blocking rule, and totals `{tasks, blocked}`. | `bylaw.backtest.backtest` |
| REQ-BT1-3 | The unpatched hand RuleSet's backtest result is reported as the baseline, and amendment costs are reported as the delta from it, so pre-existing disagreements between our rules and τ²'s gold actions are not blamed on the amendment. | `backtest` output `baseline_blocked` |
| REQ-AM1-1 | `draft(domain, ruleset, hole)` returns `{id, hole_id, policy_text, rule_patch: [tool_rule...], rationale}`, where `rule_patch` is valid C2 and `policy_text` is one or two sentences. | `bylaw.amend.draft` (live; `llm=` injectable) |
| REQ-AM1-2 | `apply(ruleset, amendment)` returns a new RuleSet. Re-running the hole's chain with it blocks at least one step. | `bylaw.amend.apply` + `rules.check` |
| REQ-AM1-3 | `python -m bylaw amend report.json -o amended.json` adds per hole: amendment, `closes: true/false` (re-audit of that goal with the patched RuleSet finds 0 holes) and the `backtest: {tasks, blocked, baseline_blocked}`. | CLI + JSON |
