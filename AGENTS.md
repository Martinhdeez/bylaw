# Bylaw

Bylaw audits the policy AI agents run on. It finds chains of individually allowed tool calls that reach outcomes the policy forbids, proves them by execution in the τ²-bench simulator, drafts amendments, backtests them, and enforces the ratified ones through an MCP proxy. Built for the Meta Global AI Developer Hackathon; Muse Spark (Meta Model API) is the reasoning engine.

- Spec: `.artifacts/specs/2026-10-26-bylaw-spec-v3.md`
- Plan: `.artifacts/todo/2026-10-26-bylaw-implementation-plan.md`
- Python via `uv run`. The Meta key lives in `.env` (`MODEL_API_KEY`), loaded with python-dotenv; never read, print or commit it.

## Harness

Work goes through the `harness` plugin: `/harness:iteration`.

- **Integration branch:** `bylaw/build`. `main` is moved only by the user.
- **Gate:** `make check` (offline pytest; plus `npm run build` in `web/` once it exists)
- **Extra checks:** `uv run pytest -m live` when a change touches `bylaw/llm.py` or Muse prompts (needs the key); Playwright smoke test of the web UI from M3 on.
- **Acceptance tests:** `tests/acceptance/`
- **Never touch:** `.env`, `.context/tau2-bench/`
- **Designer owns:** `web/`
- **Extra roles:** none
