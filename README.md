# Bylaw

Bylaw audits the policy an AI agent runs on. It finds chains of tool calls, each one allowed by the policy, that together reach an outcome the policy forbids, and it proves each chain by executing it in the [τ²-bench](https://github.com/sierra-research/tau2-bench) simulator. Muse Spark (Meta Model API) compiles the policy into rules, proposes the chains to try and drafts amendments. Each amendment is backtested against the benchmark's gold tasks, ratified by a human and enforced at runtime by an MCP proxy.

Built for the Meta Global AI Developer Hackathon. Domains: τ²-bench `airline` (full pipeline) and `retail` (rules, goals, backtest and proxy; the chain search is airline-only).

## How it works

```
policy text ─► compile ─► search ─► verify ─► classify ─► amend ─► backtest ─► ratify ─► proxy
               (Muse)    (Muse vs   (τ² env,  (A / B / C) (Muse)   (gold      (human,   (MCP stdio,
                          blind BFS) 5 replays)                     tasks)     API/UI)   enforces)
```

1. **Compile.** Muse turns the policy text into a RuleSet: per-tool rules plus forbidden goals. Its output is scored against a hand-written RuleSet (`match_rate`).
2. **Search.** Chains of write tool calls, up to a budget. With Muse, the proposer first writes chain templates per forbidden goal and gets at most half the budget; a bounded BFS fills the rest. Without Muse (`--no-llm`), BFS alone.
3. **Verify.** Each candidate runs in a fresh τ² environment. A finding counts only if every step is allowed by the rules, the forbidden goal becomes true, and it replays 5/5.
4. **Classify** (contract 01 v1.7, decision `docs/plan/decisions-2026-10-27-gold-adjudication.md`):
   - **Class A** (hole): goal reached and no gold task reaches it.
   - **Class B** (contradiction): a gold task reaches the same goal, so the policy text and the benchmark's own practice disagree. Reported and amended, never counted as a hole.
   - **Class C** (ambiguity): pre-registered as ambiguous, e.g. 24h cancel and rebook.
5. **Amend.** Muse drafts a policy sentence and a rule patch for each Class A and B finding. The patch is checked to close the chain.
6. **Backtest.** The patched RuleSet replays every gold task; the output says which gold tasks it would now block.
7. **Ratify.** A human ratifies an amendment through the API or the web UI; it is stored in `ratified/<domain>.json`.
8. **Proxy.** An MCP stdio server checks every tool call against the effective RuleSet (hand rules plus ratified amendments) and a goal monitor before it reaches the environment.

## Where Muse Spark is used

Muse Spark is the reasoning engine in three places. Without it, Bylaw has a hand-written RuleSet, a blind BFS and no amendments.

| Role | Code | Call |
|---|---|---|
| Policy compiler | `bylaw/compiler.py` | structured output (JSON schema `ruleset`), `reasoning_effort="high"`, `max_tokens=64000` |
| Chain proposer | `bylaw/proposer.py` | one structured call per forbidden goal (`chain_templates`), `reasoning_effort="high"`, `max_tokens=32000` |
| Amendment drafter | `bylaw/amend.py` | structured call (`amendment`), `reasoning_effort="high"`, `max_tokens=32000`; an invalid answer is sent back once with the reason, then rejected |

Client: `bylaw/llm.py`, the `openai` SDK pointed at `https://api.meta.ai/v1`, default model `muse-spark-1.3`. Muse output is untrusted: rule and template expressions run in a whitelisted, work-bounded evaluator.

Caching: every reply is stored on disk in `.cache/llm/`, keyed by the SHA-256 of the full request body, so a repeated run makes no new calls. `BYLAW_NO_CACHE=1` disables it.

## Quickstart

Needs `git`, `make`, [uv](https://docs.astral.sh/uv/) and Node.js with npm.

```sh
git clone https://github.com/Martinhdeez/meta-hackathon.git
cd meta-hackathon
make setup                # clones tau2-bench at the pinned commit, runs uv sync and npm ci in web/
cp .env.example .env      # then set MODEL_API_KEY in .env
make check                # offline tests (no key needed) and the web build
uv run python -m bylaw.llm --ping   # optional: one live call to check the key
```

`.env.example` also sets `MODEL_BASE_URL`, `MODEL` and `TAU2_DATA_DIR`; the defaults work.

### CLI

`uv run python -m bylaw <command>`; `--help` on each command lists its options.

| Command | What it does |
|---|---|
| `audit --domain airline [--no-llm] [--budget 2000] [-o report.json]` | search, verify and classify; writes the report |
| `compile --domain airline -o compiled.json` | compile the policy with Muse; prints the match rate against the hand RuleSet |
| `amend report.json [-o amended.json] [--no-backtest]` | draft, prove and backtest one amendment per Class A and B finding |
| `bench --domain airline --budget 200 [--modes bfs,muse] [-o bench.json]` | Muse-guided vs blind BFS search at one budget |
| `backtest --domain airline [--ruleset file.json]` | replay the gold tasks through a RuleSet (default: the hand RuleSet) |
| `proxy --domain airline` | MCP stdio server enforcing the effective RuleSet and the goal monitor |
| `replay --domain airline --gold` or `--hole G1:T1QOBS [--report report.json]` | replay the gold tasks, or one finding, through the proxy |

`audit --no-llm`, `backtest`, `replay` and `proxy` make no Muse calls.

### API and web UI

```sh
uv run uvicorn bylaw.api:app          # API on http://localhost:8000; also serves web/dist once built
cd web && npm run dev                 # dev UI (Vite), proxies /api to :8000
```

For a single server, run `cd web && npm run build` (also part of `make check`) and open http://localhost:8000. The UI covers audit (with live progress), report, finding, amendment and ratification, and bench.

## Results

Every figure below is from one run. It is not a rate, and a second run may differ. The demo reports are `reports/airline.json`, `reports/retail.json` and `reports/airline.bench.json` (DM1); their runs:

- Airline audit and amend: commit 05bd65c, `muse-spark-1.3`, `BYLAW_EFFORT=low`, budget 2000.
- Retail audit: commit 9f13ae2, `--no-llm` (blind BFS, no Muse calls), budget 2000.
- Airline bench: commit 9f13ae2, `muse-spark-1.3`, `BYLAW_EFFORT=low`, budget 200.

| What | Value | Source |
|---|---|---|
| Retail Class A `R6:#W1068289` | `modify_pending_order_payment` then `cancel_pending_order`; replays 5/5; money_delta $10,359.84; the order ends with 2 payments and 4 refunds of $3,453.28 | `reports/retail.json` `holes[0]` |
| Cause of `R6:#W1068289` | a τ² tool bug: `cancel_pending_order` refunds every `payment_history` entry, refund entries included (τ² `tools.py` L191, loop L218); reproduced with plain τ² code. An upstream issue is drafted, not filed | decision `docs/plan/decisions-2026-10-27-gold-adjudication.md` (addendum) |
| Retail audit totals | Class A 1, Class B 0, Class C 1; 1997 tool calls, 372 s | `reports/retail.json` `holes`, `contradictions`, `ambiguities`, `stats` |
| Airline audit | Class A 0, Class B 15 (G5 12, G1 2, G2 1), Class C 102 (G7 100, G1 2); 1997 tool calls, 7 Muse calls, 120,756 tokens, 425 s | `reports/airline.json` `holes`, `contradictions`, `ambiguities`, `stats` |
| Gold tasks that take the Class B chains | task 18 (12 entries), task 32 (2), task 7 (1) | `reports/airline.json` `contradictions[].gold.tasks` |
| Airline amendments | 15/15 close their goal; each blocks the gold task that takes its chain; 14 block that task only; B5 (`G1:1ERWZ8`) blocks 5 (7, 17, 22, 32, 44); baseline 0/43 | `reports/airline.json` `contradictions[].closes`, `.backtest` |
| Muse vs BFS, budget 200 | Class B: BFS 9, Muse 7. Class A 0 and 0; Class C 2 and 48; tool calls 200 and 199; Muse 7 calls | `reports/airline.bench.json` `rows` |
| Airline gold through the proxy, nothing ratified | 0/43 blocked (1 unknown) | `replay --domain airline --gold` at bada101 |
| `G1:1ERWZ8` from the DM1 report, goal G1 monitored | step 0 allowed, step 1 blocked by G1 | `Proxy(domain, monitor_goals=["G1"])` on the chain, at bada101 |
| Compiler match rate vs the hand airline RuleSet (28 rules) | 0.643 by parts, 0.607 strict | one live `compile --domain airline`, CP1 evidence `live-compile-v4.txt` (`docs/plan/01-engine/99-close.md`) |
| Retail gold through the proxy, nothing ratified | 2/112 blocked (tasks 64, 105; τ² also rejects those actions) | `replay --domain retail --gold`, PX1 `replay-gold-retail.txt` (`docs/plan/04-proxy/99-close.md`) |

What the figures say and do not say:

- The airline Class B chains are not holes. On tasks 7 and 32 the policy is ambiguous: basic economy cannot be cancelled or changed (policy L110, L143-147), but L117 allows the cabin upgrade first, and the gold tasks read it permissively. On task 18 the policy is silent on bags after a cabin change (L83-86), a gap.
- At budget 200, BFS found more Class B chains than Muse (9 against 7). One run per mode, so this does not rank the two.
- The bench Muse row shows 0 tokens because all 7 proposer replies came from the cache the airline audit wrote. That is not Muse's cost; the audit's 7 calls and 120,756 tokens are.
- The amend run does not record its Muse tokens. The compiler target of 90% match is unmet.

## Built during the event

Everything in this repository was written during the hackathon (2026-10-26 onward), with Claude Code:

- Rule language and checker with a work-bounded evaluator; hand RuleSets for airline and retail; pre-registered forbidden goals (airline G-goals, retail R1–R8).
- τ²-bench environment adapters, executor and 5/5 verifier, report with Class A/B/C.
- Muse Spark policy compiler with match rate, Muse chain proposer and the `bench` comparison against blind BFS.
- Muse amendment drafter with closure proof, gold loader and backtest.
- MCP stdio proxy with goal monitor, `replay`, ratified-amendment store.
- FastAPI server (audits with SSE progress, ratify, bench) and React web UI with Playwright tests.

Meta tooling: Muse Spark `muse-spark-1.3` through the Meta Model API (`https://api.meta.ai/v1`, OpenAI-compatible), using structured JSON-schema output and `reasoning_effort`.

## Repo layout

```
bylaw/            Python package: CLI (__main__), compiler, proposer, rules, executor, verifier,
                  report, amend, backtest, ratified, api, llm
  env/            τ²-bench airline and retail adapters
  proxy/          MCP proxy and goal monitor
  rulesets/       hand RuleSets (airline.json, retail.json)
web/              React + Vite UI, Playwright tests in web/e2e
tests/            offline unit tests; tests/acceptance/ written from the contracts
docs/plan/        per-iteration plans, contracts and close notes with measurements
.artifacts/specs/ product spec
```
