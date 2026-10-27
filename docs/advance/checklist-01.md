# Checklist 01 — Engine core

Plan: `docs/plan/01-engine/00-plan.md`. Progress: 5 / 8.

- [x] **Fix** Spike output determinism (tree clean after gate) — builder — PR #3
- [x] **OP1** Reproducible tau2 setup (`make setup`, README Quickstart) — devops, light — PR #6
- [x] **CP1** Policy compiler — builder — PR #1 (live airline match rate 0.643 by parts / 0.607 strict, 18/28 hand rules, one live compile; M1 ≥0.90 not met)
- [x] **RT1** Retail domain plug-in — builder — PR #5
- [x] **EN1** Rule checker + airline RuleSet — builder — PR #4
- [x] **Fix EN2 — PR #8** Rule evaluation budget (C2 v1.5, thread-safe), cross-process spike determinism, hand RuleSet blocks 0/43 gold — builder — PR #8
- [x] **EX1** Executor, verifier, report, audit CLI — builder — PR #9 (wave-2 `test_wave2_audit.py` in, 25/26 wave-2 pass, bench is PR1)
- [ ] **PR1** Proposer + bench — builder — PR #
- [x] **TA1** Acceptance tests wave 1 — test-author — PRs #4, #5, #1
  - [x] EN1 part (`conftest.py`, `test_wave1_rules.py`, 44 passed) — merged with PR #4
  - [x] RT1 part (`test_wave1_retail.py`, 7 passed) — merged with PR #5
  - [x] CP1 part (`test_wave1_compiler.py`, 7 passed offline, 2 live not run by the reviewer) — merged with PR #1
- [ ] **TA2** Acceptance tests wave 2 — test-author — PR #
- [ ] **UI1** Web UI prototype → implementation — designer — PR #
  - [x] Prototype on fixtures — PR #2
