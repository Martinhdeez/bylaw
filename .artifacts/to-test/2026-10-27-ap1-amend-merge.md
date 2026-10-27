# AP1 follow-up — conform the API to merged AM1 and contract 03 v1.3

## Problem

`bylaw/build` at 672ed41 is red. `tests/test_api.py::test_muse_audit_with_amend_drafts_backtests_and_counts_llm_calls` fails (`tokens 10653 == 100`).

- Since AM1 (#12) merged, the real `bylaw.amend` module is imported before the test runs. The test's stand-in in `sys.modules` is therefore bypassed, and the real Muse `draft` runs. That breaks the requirement that offline tests make no calls to the real model.
- Contract 03 v1.3 was not implemented:
  - Ratified rule ids must be namespaced as `<hole_key>/<rule_id>`.
  - `closes` must come from `bylaw.amend.closes`, the re-audit of the goal.

## Root cause

- `tests/test_api.py:192-194` (on 672ed41): the test replaces the module in `sys.modules` instead of patching the attributes of the module that is already loaded.
- `bylaw/api.py:122-124`: `closes` is the chain-only approximation.
- `bylaw/ratified.py:45-56`: `rule_patch` ids are stored unchanged, so two amendments that reuse an id collide in `effective_ruleset`.

## Change

- `bylaw/api.py`:
  - `_amend` imports `bylaw.amend` directly. The "not available" skip is gone because the module is now always there.
  - `closes = amend.closes(domain, patched, hole, budget)`, using the audit's own budget, as the CLI does.
- `bylaw/ratified.py`:
  - Uses `bylaw.amend.apply`. The fallback copy is deleted.
  - `ratify` stores each patch rule id as `<hole_key>/<rule_id>`, and the ratify response returns those ids. A patch with a duplicate id inside itself is still refused, which gives 409.
- Tests:
  - The Muse test patches `bylaw.amend.draft`. The real `apply` and `closes` run.
  - The fake search counts LLM usage only when `use_llm` is set, because `closes` re-audits offline.

## Before / after

| Check | Before | After |
|---|---|---|
| Updated tests on the old code | 5 fail, `.scratch/after/ap1-amend-merge/01-red.txt` | 24 pass, `.scratch/after/ap1-amend-merge/02-gate.txt` |
| Gate | RED on 672ed41 (reported by the reviewer) | `.scratch/after/ap1-amend-merge/02-gate.txt` |

## Tests added or changed

- `tests/test_ratified.py`:
  - `test_two_amendments_reusing_a_rule_id_both_apply` (new): two holes whose patches share a rule id both apply, under namespaced ids.
  - `test_a_patch_with_a_duplicate_rule_id_is_refused_and_not_stored` (new): replaces the old hand-id collision test, which namespacing makes impossible.
  - The other ratified tests now expect namespaced ids.
- `tests/test_api.py`:
  - The ratify response returns the namespaced `rule_ids`.
  - The Muse test runs the real `amend.closes`.

## Out of scope

- No live Muse run.
- Ratified stores written before v1.3 keep their un-namespaced ids. None are committed.
