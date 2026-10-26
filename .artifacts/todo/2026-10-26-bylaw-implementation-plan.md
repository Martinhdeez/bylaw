# Bylaw — Implementation Plan

Spec: `.artifacts/specs/2026-10-26-bylaw-spec-v3.md`. Deadline: Wed 2026-11-04 9:00 PM ET. Builders run in parallel only where noted. At most 6–8 agents at once.

## Repo layout

```
bylaw/                     # Python package (uv, Python 3.12)
  env/tau2_airline.py      # load env, snapshot/diff DB, call tools
  goals.py                 # G1–G7 predicates (frozen)
  rules.py                 # tool_rules expression eval + checker
  compiler.py              # Muse: policy -> RuleSet (JSON schema)
  proposer.py              # Muse chains + bounded BFS
  executor.py  verifier.py # run chain on fresh DB, prove hole
  amend.py  backtest.py    # Muse amendment + replay 43 gold tasks
  llm.py                   # OpenAI-compatible client + capability table
  report.py                # hole report JSON
  api.py                   # FastAPI: /audit, /holes, /holes/{id}, /ratify
  proxy/mcp_server.py      # MCP proxy enforcing ratified rules
web/                       # Vite + React + TS, dark style (Archivo / JetBrains Mono, #ff4d2e, #2be3a0, N3 logo)
tests/                     # pytest
spike/                     # M0 scripts (kept as evidence)
pyproject.toml  .env.example  README.md
```

tau2-bench is a dependency: `uv add "tau2 @ git+https://github.com/sierra-research/tau2-bench"`, with `TAU2_DATA_DIR` pointing at a checkout's `data/`. Fallback: `uv pip install -e .context/tau2-bench`.

## Decisions (user, 2026-10-26)

- Domains: τ² **airline + retail**. The engine is domain-agnostic, and every domain is a plug-in: env loader, goals and hand-written rules.
- **Muse must be essential and measured.**
  - Muse compiles the policy into rules and goals. Without it there is no engine for a new policy.
  - Muse proposes chains and drafts amendments.
  - Measure Muse-guided search against blind BFS: holes found per tool-call budget and per wall-clock. Show the result in the UI.
- Deploy: the user's OVH VPS via docker compose, only after the user gives the go-ahead.
- Git: commit and push to `bylaw/build` per milestone. Never touch `main`. No PRs unless asked.
- Order: M0 → M1 → M2 → M3 → M4. Each milestone closes with a green acceptance check, a commit and a push.

## M0 — Spike gate (no LLM)

- `spike/holes_by_hand.py` executes H1, H2 and H3 on fresh DB copies, using real target reservations from the DB (e.g. T1QOBS for H1). These are the money-leaking and no-excuse holes.
- H4, H5 and H6 (cancel+rebook) run too, but they are reported as Class C. Muse itself judged the 24h cancel+rebook to be the permitted method. They count only if a chain breaks the 24h condition, e.g. a business-hop cancel after 24h.
- Acceptance:
  - `uv run python spike/holes_by_hand.py` prints at least 3 **Class A** holes from H1/H2/H3 (or new non-cancel+rebook ones) with `ALL STEPS ALLOWED` and `GOAL Gx TRUE`.
  - `uv run pytest tests/test_spike.py` is green.
  - Goals G1–G7 are committed *before* this runs (pre-registration).
- **Gate:** fewer than 3 Class A holes means stop, and fall back to Acme Shop (our own toy policy + tools, same engine).
- Parallel: 1 builder (spike) + 1 builder (`llm.py` + a live Muse "hello" check: `uv run python -m bylaw.llm --ping`).
- `llm.py` facts (verified live):
  - The key loads via python-dotenv from `.env` and is never printed.
  - Default model `muse-spark-1.3`. `max_tokens` ≥ 2000, because it is a reasoning model and below that the content comes back empty.
  - `reasoning_effort="high"` and `json_schema` with strict are supported.
  - Expect 3–6 s per call, so cache responses on disk.
  - Muse Spark Open has no Baseten key yet, so it stays M5 stretch.

## M1 — Engine core

- Items, which can run in parallel: (a) `rules.py` + a hand-written RuleSet for airline; (b) `executor.py` + `verifier.py`; (c) `compiler.py` with Muse structured output, checked against the hand-written RuleSet; (d) `proposer.py` BFS (depth ≤4, WRITE tools, targets drawn from the DB) + Muse proposals.
- Acceptance:
  - `uv run python -m bylaw audit --domain airline --no-llm` finds H1–H3 by BFS.
  - With the LLM, the compiler's RuleSet matches ≥90% of the hand-written rules (`pytest tests/test_compiler.py -m live`).
  - `report.json` validates against its schema.

## M2 — Amendments + backtest

- Items, in parallel: (a) `amend.py` (Muse drafts a policy sentence + rule patch); (b) `backtest.py` (replay gold actions for the 43 tasks through the patched checker).
- Acceptance:
  - After patching, `audit` re-run finds 0 holes for the patched goals.
  - The backtest reports blocked gold tasks per amendment, with a target of 0.
  - These numbers replace the video placeholders.

## M3 — Web UI

- Items, in parallel: (a) FastAPI `api.py`; (b) web screens: report list, hole detail (animated trace replay, policy lines highlighted, rule verdict per step), amendment diff + backtest numbers, Ratify button, Muse capability labels + token counter.
- Acceptance:
  - `uv run pytest tests/test_api.py` is green.
  - Playwright smoke test: open → run audit → open H1 → ratify.
  - Screenshots in `.artifacts/reports/`.

## M4 — MCP proxy

- `proxy/mcp_server.py` exposes the 14 τ² tools. It enforces the ratified rules and a session goal monitor.
- Acceptance: a scripted MCP client replaying H1 gets `BLOCKED` at step 2. Replaying the 43 gold tasks gets 0 blocks.
- Parallel with M3.

## M5 — Muse breadth + rigor

- Items: (a) Muse Spark Open switch (Baseten) via the capability table; (b) 1M-context prompt (policy + tasks + schemas) with a token counter; (c) blind-reviewer script + agreement rate; (d) coverage table; (e) draft of the upstream GitHub issue (filed only with the user's approval); (f) stretch: video → rules.

## M6 — Deploy + demo

- Deploy the API + web as a live product (the user's VPS or Fly/Render; deploy only with the user's go-ahead).
- README covers: what was built during the event, Meta tooling, and how to run.
- Final 3-minute video: the v8 hook (≈50 s) + real product screens + real numbers.
- Acceptance: the public URL runs an audit end to end. The repo is public.

## Risks

- **Holes judged as intended slack** (24h window). This is already confirmed by Muse for cancel+rebook. Mitigation: count only H1/H2/H3-type holes; cancel+rebook goes in as Class C; pre-registration; blind reviewer.
- **Spike gate fails.** Fallback: Acme Shop domain.
- **Meta API key missing or rate-limited.** The engine works `--no-llm`; Muse is used for compile/propose/amend only, and we cache responses.
- **tau2 install/data path issues.** Pin a commit and set `TAU2_DATA_DIR`.
- **Time.** M0–M2 are the product. M3–M4 make it demoable. M5 is score polish.
