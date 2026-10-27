# 04 — Requirements

| Id | Requirement | Checked through |
|---|---|---|
| REQ-PX1-1 | `python -m bylaw proxy --domain D` starts an MCP server on stdio exposing every τ² tool of D with its schema. | MCP client `list_tools` |
| REQ-PX1-2 | A call that a rule of the effective RuleSet denies returns a tool result whose text starts with `BLOCKED` and names the rule id and its policy line; the DB is unchanged. | MCP `call_tool` + `Proxy.snapshot()` |
| REQ-PX1-3 | A write call that would make a Class A goal true for the session (from session start) is BLOCKED by the goal monitor and not applied, even when every rule allows it. | MCP `call_tool` |
| REQ-PX1-4 | `python -m bylaw replay --domain airline --hole KEY` (from the latest report) prints one line per step `ALLOWED|BLOCKED <tool> <reason>` and exits 0; with ratified amendment for H1-type G1 hole it is BLOCKED at or before the step that makes the goal true. `--gold` replays the gold tasks through the proxy and prints `blocked: N/43` (target 0). | CLI |
