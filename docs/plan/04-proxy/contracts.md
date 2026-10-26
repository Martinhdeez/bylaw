# 04 — Contracts (frozen v1)

## C11 Proxy — `bylaw/proxy/`

```python
class Proxy:                       # bylaw/proxy/core.py — transport-free, used by the MCP server and tests
    def __init__(self, domain, ruleset: dict | None = None, monitor: bool = True): ...  # ruleset default: ratified.effective_ruleset(domain.name)
    def tools(self) -> list[dict]          # [{"name", "description", "input_schema"}]
    def call(self, tool: str, args: dict) -> dict   # {"ok": bool, "blocked": bool, "reason": str|None, "rule_id": str|None, "goal": str|None, "result": any}
    def snapshot(self) -> dict             # C1 snapshot of the session env
```

- One `Proxy` = one session = one fresh τ² env. Conversation-fact keys (C2 v1.1) in `args` are read by rules and stripped before the τ² call.
- Goal monitor: before applying a write call, the proxy applies it to a copy of the session env and evaluates the domain's Class A goals on the diff from session start; if one becomes true, the call is BLOCKED with `goal` set and is not applied.
- `bylaw/proxy/mcp_server.py`: MCP stdio server (Python `mcp` SDK) wrapping one `Proxy`; a blocked call returns text `BLOCKED <rule_id|goal>: <policy_ref or goal title>`.
- CLI (in `bylaw/__main__.py`): `proxy --domain D`, `replay --domain D (--hole KEY | --gold) [--report PATH]`.

## v1.1 (2026-10-27, from TA5 findings), binding on PX1

- `Proxy.call` on a blocked call returns `ok: false, blocked: true`.
- Blocked text (MCP and `call` `reason`): rule → `BLOCKED <rule_id>: <policy_ref>`; goal monitor → `BLOCKED <goal_id>: <goal title>`.
- `replay` output: one line per step `<n> ALLOWED|BLOCKED <tool>[ <reason>]`, `n` 0-based; `--gold` ends with `blocked: N/T`.
- `effective_ruleset` reads `BYLAW_RATIFIED_DIR` on every call (03 v1.1).
- `mcp` (official Python SDK) is a project dependency.
