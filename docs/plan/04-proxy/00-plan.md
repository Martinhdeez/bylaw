# 04 — MCP proxy enforcement (M4)

## Goal of the increment

An agent talks to the τ² tools through Bylaw's MCP server instead of directly. Every tool call is checked against the ratified RuleSet (C10) and a session goal monitor before it touches the DB. A replay of a proven hole is BLOCKED; a replay of the honest gold tasks is not.

## Starts from

C1, C2, C10 (`effective_ruleset`), executor replay (EX1), backtest gold loader (BT1).

## Items

| Id | Item | Type | Weight | Agent | Depends on | Requirements |
|---|---|---|---|---|---|---|
| PX1 | MCP proxy server + scripted replay client | feature | full | builder | C11 | REQ-PX1-1..4 |
| TA5 | Acceptance tests 04 | tests | full | test-author | contracts | REQ-PX1-* |

## Waves

PX1 and TA5 in parallel; can run alongside iteration 03.

## Out of scope

Networked transports other than stdio, multi-tenant sessions, auth.
