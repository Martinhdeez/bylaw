# VN1 Vendor the cs-agents-demo backend

- `targets/cs_demo/airline/` is upstream `python-backend/airline/` at `bd7bfca0f5abf50529370814c3e7c88542011925`, unchanged; `LICENSE` (MIT) and `NOTICE.md` alongside (CS-C0).
- `pyproject.toml`: `openai-agents==0.24.0` and `openai-chatkit==1.6.5` (the demo's context and tools import `chatkit`; no server, no UI, no network).
- `tests/test_cs_demo_vendor.py`: importing `targets.cs_demo.airline.agents` with sockets blocked and no key lists the six agents and their tools.

To test: `uv run pytest -q tests/test_cs_demo_vendor.py`; `diff -r -x __pycache__ <clone>/python-backend/airline targets/cs_demo/airline` prints nothing.
