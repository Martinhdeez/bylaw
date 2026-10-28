# Notice

`targets/cs_demo/airline/` is vendored from the OpenAI Customer Service Agents Demo.

- Origin: https://github.com/openai/openai-cs-agents-demo, directory `python-backend/airline/`
- Commit: `bd7bfca0f5abf50529370814c3e7c88542011925` (2025-12-11)
- Vendored: 2026-10-28
- Licence: MIT, "Copyright 2025 OpenAI", in `LICENSE` (verbatim)

## Changes

- Copied `__init__.py`, `agents.py`, `context.py`, `demo_data.py`, `guardrails.py` and `tools.py` byte for byte. The package's imports are relative, so `targets.cs_demo.airline` imports without edits.
- Not copied: the ChatKit server (`server.py`, `main.py`, `memory_store.py`) and the Next.js UI.
- Added the empty packages `targets/__init__.py` and `targets/cs_demo/__init__.py`.
- No OpenAI branding was present in the copied files; the model names (`gpt-5.2`, `gpt-4.1-mini`) stay as upstream.
- Dependencies pinned in `pyproject.toml`: `openai-agents==0.24.0`, and `openai-chatkit==1.6.5` because `context.py` and `tools.py` import `chatkit.agents.AgentContext` and `chatkit.types.ProgressUpdateEvent` (a local library, no network).

The demo's behaviour is unchanged on purpose: Bylaw audits it as found.
