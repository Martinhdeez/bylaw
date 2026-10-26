# [SUPERSEDED] Policy Firewall for AI Agents — Product Spec

Superseded by `2026-10-26-bylaw-spec-v3.md`.

Status: draft v1, 2026-10-26. Working name: **Policy Firewall** (final name TBD).
Event: Meta Global AI Developer Hackathon, Indie track. Deadline: Wed 2026-11-04 21:00 ET (Thu 03:00 CET).

## 1. One-liner

Company rules written in plain language, compiled by Muse Spark into tested, deterministic rules, and enforced on every tool call an AI agent makes, through a drop-in MCP proxy.

## 2. Problem

Companies want agents that issue refunds, send emails and touch customer data. Today the rules live in the system prompt, and one prompt injection breaks them. LLM-as-judge guardrails have the same weakness: the decision is still made by a model that can be talked out of it.

## 3. Principle

**The model never makes the allow/block decision.** Models compile rules, write their tests, attack them and explain decisions. A deterministic evaluator enforces them. Same principle as Banana Bank (prompt injection 2/8 → 0/8).

## 4. Core flow

1. **Author.** A policy owner writes a policy in plain language, or uploads a handbook (PDF, image).
2. **Compile.** Muse Spark turns each policy into a rule in the Rule DSL (§6) plus test cases. The compiler validates the rule against the DSL schema and runs the generated tests against the real evaluator. On failure it repairs and retries.
3. **Review and publish.** The owner sees the plain-language policy, the compiled rule (rendered readably) and the tests side by side. Publishing creates an immutable, versioned policy set.
4. **Backtest before publish.** The candidate version is replayed against past tool calls. The UI shows exactly which past decisions would change (allow → block, etc.) and why.
5. **Enforce.** The MCP proxy sits between any MCP agent and its tool servers. Every `tools/call` is evaluated before it runs: `allow` (forward), `block` (return a structured refusal), `escalate` (hold for human approval).
6. **Log.** Every decision records the tool call, the context, the outcome, the rules that fired and the policy version.
7. **Red-team.** A Muse Spark attacker generates adversarial tickets and injections against the protected agent. Every bypass becomes a regression test and a proposed rule fix.

## 5. Components

| # | Component | Responsibility | Model use |
|---|---|---|---|
| C1 | `engine` | Rule DSL schema, deterministic evaluator, fact providers. Pure, no I/O except facts. | none |
| C2 | `store` | SQLite: policies, versions, rules, tests, decisions, approvals, action history. | none |
| C3 | `compiler` | NL / PDF / image → DSL rules + tests, validate, self-repair loop. | Muse Spark (structured output, multimodal) |
| C4 | `proxy` | MCP proxy: wraps upstream MCP servers, evaluates every call, logs, handles escalation. One line in an agent's MCP config. | none on the hot path; optional explanation |
| C5 | `backtest` | Replay history against a candidate version, produce a diff. | none (optional summary) |
| C6 | `demo` | Mock "Acme Shop" support MCP server + support agent. | agent on Muse Spark (and Muse Spark Open via Baseten if credits arrive) |
| C7 | `redteam` | Attacker agent, attack corpus, comparison run (rules-in-prompt vs firewall). | Muse Spark |
| C8 | `api` | FastAPI: policies, compile, publish, decisions (SSE live feed), approvals, backtest, red-team, arena. | — |
| C9 | `web` | React UI: policy editor + compile review, live decision log, approvals inbox, backtest diff, red-team report, public arena. | — |
| C10 | `seed` | ~1,000 synthetic past tool calls for backtesting. | Muse Spark to generate variety, frozen as a fixture |

## 6. Rule DSL (contract — freeze first)

Rules are data, not code. The LLM cannot inject executable code into the firewall.

```json
{
  "id": "refund-limit",
  "policy_id": "pol-refunds",
  "description": "Refunds over 500 EUR need manager approval",
  "applies_to": { "tools": ["issue_refund"] },
  "when": {
    "all": [
      { "fact": "args.amount", "op": ">", "value": 500 },
      { "fact": "args.currency", "op": "==", "value": "EUR" }
    ]
  },
  "effect": "escalate",
  "message": "Refunds over 500 EUR require manager approval."
}
```

- **Conditions:** `all` / `any` / `not`, comparison ops `== != > >= < <= in not_in contains matches(regex)`.
- **Facts:**
  - `args.*`: tool-call arguments.
  - `ctx.*`: caller context (agent id, user/session, channel).
  - Named fact providers (deterministic, read from `store` or the mock backend), for example `customer.region`, `customer.tier`, `history.refund_total(customer_id, days=30)`, `history.count(tool, customer_id, days=1)`, `email.recipient_domain_is_internal`.
- **Effects and precedence:** `block` > `escalate` > `allow`. If no rule matches, the per-tool default applies (default `allow`; `deny-unknown-tools` is a setting).
- **Decision record:** `{decision_id, ts, tool, args, ctx, outcome, fired_rules[{rule_id, version}], policy_version, latency_ms, explanation?}`.
- **Test case:** `{rule_id, name, call{tool, args, ctx}, facts_override?, expected_outcome}`.

## 7. Demo vertical

Acme Shop customer support. Agent tools (mock MCP server):

- `lookup_customer(customer_id | email)`
- `get_order(order_id)`
- `issue_refund(order_id, amount, currency, reason)`
- `send_email(to, subject, body)`
- `export_customer_data(customer_id, destination)`
- `update_shipping_address(order_id, address)`

Seed policies (6–8):

1. Never refund more than 500 EUR without manager approval.
2. No more than one refund per order; total refunds per customer over 1,000 EUR in 30 days are blocked.
3. Customer data of EU customers never leaves the EU (`export_customer_data` destination region).
4. Emails with customer personal data only go to the customer's own address on file.
5. Shipping address changes after an order ships need escalation.
6. Refund amount can never exceed the order total.
7. No outbound email to external domains containing internal ticket notes.

## 8. Differentiators (what judges must see)

1. **Numbers, not claims.** Red-team corpus of ~200 attacks: rules-in-prompt agent vs. firewall-protected agent. Report the bypass rate of each.
2. **Meta models in several real roles:** compiler (text + PDF/image), test writer, attacker, protected agent, explainer.
3. **Drop-in.** Protect an off-the-shelf MCP agent by changing one line of config.
4. **Backtest diff** before every publish.
5. **Public "Break my agent" arena:** live product for judges, X challenge, community vote, and real attack data.

## 9. Stack

- Python 3.12, `uv`, FastAPI, Pydantic v2, SQLite, `mcp` (official Python SDK), `openai` SDK pointed at the Meta Model API (`https://api.meta.ai/v1`, `MODEL_API_KEY`, model `muse-spark-1.3`), pytest.
- React + TypeScript + Vite, Tailwind.
- Deploy: VPS (Docker compose) behind a public URL.

## 10. Out of scope (for now)

Multi-tenant auth, real payment or email providers, policy languages other than English, non-MCP agent frameworks.

## 11. Plan

| Days | Dates | Goal |
|---|---|---|
| 0 | Oct 26 | Spec, frozen contracts (DSL, decision record, API), repo skeleton, credits claimed |
| 1–3 | Oct 27–29 | Wave 1 in parallel: C1 engine, C2 store, C4 proxy, C6 demo server + agent, C3 compiler, C8/C9 shells. End: injected refund is blocked end to end |
| 4–6 | Oct 30–Nov 1 | Wave 2: C5 backtest + C10 seed, C7 red-team, approvals, arena, deploy |
| 7–8 | Nov 2–3 | Iterate on new ideas, polish, numbers for the pitch |
| 9 | Nov 4 | Demo video (3 min, real app footage), README, submission before 21:00 ET |

## 12. Open questions

- Final product name.
- Muse Spark Open via Baseten for the protected agent (depends on credits).
- Escalation UX: proxy blocks and waits vs. returns "pending" and the agent continues.
