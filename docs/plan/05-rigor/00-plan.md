# 05 — Muse breadth and rigor (M5)

Goal: make the Muse claims measurable and the findings independently checked, so the demo can quote them. Builds on 01–04 (all merged or in review).

## Items

| Id | Item | Kind | Weight | Agent | Requirements |
|---|---|---|---|---|---|
| LC1 | Long-context mode + per-audit token counter | feature | full | builder | REQ-LC1-1..2 |
| BR1 | Blind reviewer + agreement rate | feature | full | builder | REQ-BR1-1..2 |
| CV1 | Coverage table | feature | full | builder | REQ-CV1-1 |
| UP1 | Draft of the upstream τ²-bench issue (gold tasks take forbidden chains) | docs | light | assistant | — |
| SO1 | Muse Spark Open via Baseten | — | parked | — | no Baseten key (plan M5a) |

## Requirements

| Id | Requirement | Surface |
|---|---|---|
| REQ-LC1-1 | `audit --long-context` sends the whole policy, the tool schemas and the gold task list in one Muse prompt per proposer call (no truncation), and the report records `run.context_tokens` (prompt tokens of the largest call). | CLI + report JSON |
| REQ-LC1-2 | Every report records `stats.tokens` for that audit only (not process-wide), so two audits in one API process report their own counts. | report JSON, API |
| REQ-BR1-1 | `python -m bylaw review REPORT` gives each finding (chain, DB diff, policy text; no class label, no goal id) to Muse in a fresh context and records its verdict (violation / sanctioned / unclear) with a one-line reason. | CLI + JSON |
| REQ-BR1-2 | The review output reports the agreement rate between the blind verdict and the engine class (A↔violation, B↔sanctioned, C↔unclear), with the run named. | CLI + JSON |
| REQ-CV1-1 | `python -m bylaw coverage REPORT` prints, per forbidden goal, the number of chains tried, executed write steps, and findings by class; output as a Markdown table and JSON. | CLI |

## Out of scope

Video → rules (stretch). Filing the upstream issue (user approval needed). Deploy (user go-ahead).

## Deviation from the harness

No blind test author this iteration: the machine is saturated by parallel gates. Reviewers prove each new test can fail by mutation instead. Recorded for the close note.
