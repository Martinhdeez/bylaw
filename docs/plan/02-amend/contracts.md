# 02 — Contracts (frozen v1)

## C7 Amendment — `bylaw/amend.py`

```python
def draft(domain, ruleset: dict, hole: dict, model=None, llm=None) -> dict
# -> {"id": "A1", "hole_id": "H1", "policy_text": str, "rule_patch": [C2 tool_rule], "rationale": str}
def apply(ruleset: dict, amendment: dict) -> dict   # appends rule_patch (ids must not collide); pure
```

CLI: `python -m bylaw amend REPORT.json [-o OUT.json] [--no-backtest]`. It writes the C4 report with, per hole, `"amendment": {...}, "closes": bool, "backtest": {"tasks": int, "blocked": int, "baseline_blocked": int, "blocked_tasks": [ids]}`.

## C8 Backtest — `bylaw/backtest.py`

```python
def load_gold(domain) -> list[dict]          # [{"id": str, "actions": [{"tool": str, "args": dict}]}]
def backtest(domain, ruleset: dict) -> dict  # {"tasks": int, "blocked": int, "results": [{"id", "blocked", "rule_id", "step"}]}
```

- Gold actions run on a fresh env per task, in order. Each one is checked with `rules.check` against the snapshot before the call, then executed.
- Conversation facts (C2 v1.1) are inferred from the gold task when possible (e.g. the cancel reason from the task's instructions or user scenario). If it cannot be inferred, the task counts as `unknown`, not blocked, and the total of unknowns is reported.

## v1.1 (2026-10-26, from TA3 findings), binding on BT1 and AM1

- **C8 `domain`:** the C1 Domain object (as in C3 and C6), not a name.
- **C8 `step`:** 0-based index into the task's `load_gold` action list; `null` when not blocked.
- **C8 unknown:** `backtest` returns `"unknown": int` at top level, and each result carries `"unknown": bool`. An unknown task has `"blocked": false`.
- **C7 model output:** `draft` asks the model (`bylaw.llm.structured`, `effort="high"`) for `{"policy_text", "rule_patch", "rationale"}` at the top level; `draft` adds `id` and `hole_id`. `draft` validates the patch with `rules.validate` and checks `policy_text` is 1–2 sentences; on failure it retries once, then raises `ValueError`. Never passes an invalid amendment through.
- **C7 offline hook:** `draft` calls `bylaw.llm.structured` through the module attribute (or the `llm=` argument), so tests can replace it before `python -m bylaw` runs.
- **C7 id collision:** `apply` raises `ValueError` if a patch rule id already exists in the ruleset.
- **C7 `blocked_tasks`:** ids of every task the patched ruleset blocks (not only new ones). `baseline_blocked` is the count for the unpatched ruleset.
