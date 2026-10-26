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
