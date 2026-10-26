# CP1 Policy compiler (Muse → RuleSet JSON)

- **Branch:** `feat/cp1-compiler` · **Pull request:** #1
- **Measured against:** REQ-CP1-1, REQ-CP1-2, REQ-CP1-3; contracts C2, C3 (v1.1), C5 (`compile`)

## Problem

Bylaw claims "Muse writes the law into checks", but nothing turned a policy into checks. There was no `bylaw.compiler`, no C2 `RULESET_SCHEMA`/`validate`, and no `python -m bylaw` entry point. REQ-CP1-1..3 had no implementation.

## Root cause

New feature. `bylaw/rules.py` on `bylaw/build` (M0) is a hand-coded Python checker. It does not provide the C2 `RULESET_SCHEMA`, `validate()` or the expression evaluator, so the brief's fallback applies: they live in `bylaw/ruleset_schema.py`.

## Change

1. `bylaw/ruleset_schema.py`: `RULESET_SCHEMA` (strict-mode compatible), `RuleError` and `validate()`. `parse()` checks expressions with a whitelist AST walker: C2 names, comprehension variables, the C2 functions and only `.get(...)` as an attribute. `evaluate()` runs an expression with empty builtins. `context()` resolves `res` and `user` from `args` (C2). `hours_between` returns absolute hours.
2. `bylaw/compiler.py`:
   - `compile_policy(domain, model=None, llm=None)` (C3 v1.1). One prompt carries the policy, the tool schemas and trimmed DB record shapes. It asks Muse to quote `policy_ref` verbatim, to use only the whitelisted names and functions, to read conversation facts from `args["reason"]` / `args["reservation_id"]`, and to state forbidden goals as end states. The call uses `structured(..., RULESET_SCHEMA, effort="high")`. A result that fails `validate()` or names an unknown tool goes back to Muse once, with the error (`bylaw/compiler.py:82`).
   - `load_domain()` uses `bylaw.domain.get_domain` if it exists. Otherwise it falls back to the M0 airline env (`bylaw.env.tau2_airline`) for the policy, tool schemas, DB and clock.
   - `match_rate(compiled, hand, db=None, now=None)` (`bylaw/compiler.py:153`) is the share of hand rules for which some compiled rule on the same tool has the same truth table. Probes (`bylaw/compiler.py:123`) are built from the domain DB: a stride sample of records, plus every record created within 72h of `now`, plus argument-value variants. The variants set each `args` key the rules read to each literal the rules compare with (±1 for numbers). An expression that raises evaluates as deny.
3. `bylaw/__main__.py`: argparse dispatcher with only `compile --domain D -o PATH`. It prints the rule counts and the match rate against `bylaw/rulesets/<domain>.json`, or says that no hand RuleSet exists.
4. `tests/test_compiler.py`: 35 offline tests and 1 live test.

## Before / after

| Check | Before | After |
|---|---|---|
| Schema and whitelist validation tests | `.scratch/after/cp1-compiler/red-1-validate.txt` (no module) | `.scratch/after/cp1-compiler/make-check.txt` |
| `match_rate` tests (identity 1.0, DB probes) | `.scratch/after/cp1-compiler/red-2-match-rate.txt` (no module) | `.scratch/after/cp1-compiler/make-check.txt` |
| `compile` CLI tests | `.scratch/after/cp1-compiler/red-3-cli.txt` (no module) | `.scratch/after/cp1-compiler/make-check.txt` |
| Tests fail when behaviour breaks (6 mutations) | n/a | `.scratch/after/cp1-compiler/mutations.txt` |
| Live compile of airline policy (REQ-CP1-1, -3) | no command | `.scratch/after/cp1-compiler/live-compile.txt`, `airline.compiled.json` |
| Compiled rules, goals, verbatim quotes | n/a | `.scratch/after/cp1-compiler/live-summary.txt` |
| `pytest -m live tests/test_compiler.py` | n/a | `.scratch/after/cp1-compiler/live-pytest.txt` |

Live result (`live-compile.txt`, `live-summary.txt`): 18 tool rules and 12 forbidden goals. 29 of 30 `policy_ref`s appear verbatim in the policy (whitespace normalised). No match rate yet, because `bylaw/rulesets/airline.json` (EN1) does not exist.

## Tests added

All in `tests/test_compiler.py`:

- **Validation (REQ-CP1-1, C2):** `test_validate_accepts_a_well_formed_ruleset`, `test_validate_rejects_expressions_outside_the_whitelist` (8 cases: import, dunder, open, eval, lambda, unknown name, statements, non-`.get` method), `test_validate_accepts_the_c2_expression_language` and `test_validate_rejects_a_ruleset_that_breaks_the_c2_shape`.
- **`match_rate` (REQ-CP1-2, C3):**
  - Identity is 1.0 on a fixture DB and on the airline DB.
  - An equivalent rewrite matches.
  - A 48h-vs-24h rule is told apart, both on DB probes and in a 1000-record DB where only one record separates them.
  - `<` vs `<=` is told apart through argument variants.
  - A different tool does not match, and an empty compiled set scores 0.
- **`compile_policy` (C3 v1.1, `llm=` injection):**
  - A valid reply is returned.
  - The call uses `effort="high"` and `RULESET_SCHEMA`, and the prompt carries the policy, the tools, `hours_between` and `args["reason"]`.
  - A rejected reply goes back once, with the reason.
  - A second invalid reply raises `RuleError`.
- **CLI (REQ-CP1-3, C5):** writes a valid RuleSet and prints `match rate: 0.67 (2/3 hand rules)`. Without a hand set, it prints the rule count.
- **Live:** `test_live_compile_airline_policy` (`@pytest.mark.live`).

Each test file ran red before the module existed (the `red-*.txt` files). The `compile_policy` tests were written after the module draft, so their red evidence is the mutation run in `mutations.txt` (effort and repair-loop mutations), not a pre-code failure.

## Out of scope and not measured

- **Match rate against a hand RuleSet:** not measured. EN1 has not written `bylaw/rulesets/airline.json`. The M1 target of ≥90% is unverified.
- **Probe coverage limits:**
  - Probes vary `args` only over literals that appear in the rules.
  - `now` is fixed.
  - Every probe names a DB record as its target, including tools such as `send_certificate`.
  - Two rules that both raise on every probe count as a match.
- **Retail:** there is no `bylaw.domain` yet, so `load_domain` supports only airline.
- **Live run cache:** the live pytest run was served from the on-disk LLM cache. It used the same request as the CLI run, so only one real Muse call was made.
- **Precision:** extra compiled rules and forbidden goals are not scored. `match_rate` is recall over hand rules, as C3 defines it.
- **Pre-existing on `bylaw/build`:** running `make check` rewrites `spike/holes_by_hand.json` (`tests/test_spike.py`) with a different order. That file is not part of this change.
