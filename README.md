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

Live report figures (DM1) are pending. Every figure below is from one run, as recorded in the iteration close notes.

| What | Value | Run |
|---|---|---|
| Compiler match rate vs the hand airline RuleSet (28 rules) | 0.643 by parts, 0.607 strict | one live `compile --domain airline`, CP1 evidence `live-compile-v4.txt` (`docs/plan/01-engine/99-close.md`) |
| Hand RuleSet vs airline gold | 0/43 blocked, 1 unknown (task 39) | `backtest --domain airline`, EN2 review (01 close) |
| Blind BFS audit, airline, budget 2000 | 15 findings (classified before v1.7, all as Class A; goals G1, G2, G5), 2 Class C, about 170–210 s | `audit --domain airline --no-llm`, EX1/GA1 reviews (01 close) |
| Muse vs BFS, Class A count per budget 25/50/100/200/2000 | 2/1, 4/4, 8/7, 38/9, 18/15 (Muse ≥ BFS at every budget); about 185k tokens and 7 LLM calls per Muse run | `bench --domain airline --modes bfs,muse` at commit c4c136f, PR1 evidence `bench-summary.txt` (01 close) |
| Airline amendments | 15/15 close their goal; 14 block exactly the gold task that sanctions the goal (18, 7 or 32); the broad G1 amendment blocks 5 (7, 17, 22, 32, 44); baseline 0/43 | one live `amend report.json` at 74fce98, AM1 evidence `amend-table.md` (`docs/plan/02-amend/99-close.md`) |
| Airline gold through the proxy, nothing ratified | 0/43 blocked (1 unknown) | `replay --domain airline --gold`, PX1 review (`docs/plan/04-proxy/99-close.md`) |
| Retail gold through the proxy, nothing ratified | 2/112 blocked (tasks 64, 105; τ² also rejects those actions) | `replay --domain retail --gold`, PX1 `replay-gold-retail.txt` (04 close) |
| Hole `G1:1ERWZ8` with goal G1 monitored | step 0 allowed, step 1 blocked by G1 | PX1 `replay-holes.txt` (04 close) |
| Same hole with a hand-written stand-in amendment | step 0 blocked by the rule | PX1 `replay-holes.txt` (04 close) |

Limits stated in the close notes: one run per budget, so Muse variance is not measured (an earlier sweep gave 147 Class A at budget 2000 against 18 in this one); the compiler target of 90% match is unmet; the gold tasks that sanction G1, G2 and G5 chains (7, 18, 25, 32) make those findings Class B under v1.7.

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
