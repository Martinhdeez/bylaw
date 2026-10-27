# FX1: Muse failures logged, all-fail warning, bench names model and commit, BYLAW_EFFORT

## Problem

REQ-DM1-1 (docs/plan/03-product/requirements.md): every demo result must name the commit and the model that produced it.
- An audit whose every Muse call failed (for example no `MODEL_API_KEY`) wrote `run.mode: "muse"` and `run.model: "muse-spark-1.3"` and exited 0 without a word. The exception text was dropped.
- The bench JSON (`{domain, budget, rows}`) had no model and no top-level commit.
- Added by the coordinator: testing the app spends tokens at `effort="high"`, which amend, proposer and compiler hard-code. There was no way to lower it.

## Root cause

- `bylaw/report.py:111-116` (`counted`, 2fa9fac): `except Exception:` counts the error and re-raises. The proposer swallows it for the BFS fallback (C6 v1.8), so the class and message are lost.
- `bylaw/report.py:147-149` (2fa9fac): `mode` and `model` come from `use_llm` alone. Whether any call succeeded is never checked.
- `bylaw/__main__.py:175` (2fa9fac): `cmd_bench` writes only `domain`, `budget` and `rows`.
- `bylaw/llm.py:61-66` (2fa9fac): `_call` uses the caller's `effort` with no override.

## Change

- `bylaw/report.py`: each failed Muse call prints `muse call failed, goal falls back to BFS: <Class>: <message>` to stderr. The per-goal BFS fallback is unchanged.
- `bylaw/__main__.py` `cmd_audit`: when `llm_calls > 0` and `llm_errors == llm_calls`, it prints `WARNING: every Muse call failed (n/n); this run is a BFS fallback, ...` to stderr.
- `bylaw/__main__.py` `cmd_bench`: adds top-level `model` (the muse row's `run.model`, or null when muse did not run) and `commit`. The existing fields are kept.
- `bylaw/llm.py` `_call`: `BYLAW_EFFORT` overrides `effort` before the request body is built. The cache key hashes that body, so low and high answers never share a cache entry. When the variable is unset, behaviour is unchanged. It is documented in `.env.example` and in the module docstring.

## Not done (blocked by the contract)

- **`run.mode: "bfs-fallback"` and `run.model: null` on an all-fail run.** C4 (`docs/plan/01-engine/contracts.md:60`) fixes `"mode": "bfs|muse"` and `"model": ""` (a string). `REPORT_SCHEMA` (`bylaw/report.py:31`) has `mode: {"enum": ["bfs", "muse"]}` and `model: string`. The acceptance test `tests/acceptance/test_wave2_audit.py:105-107` asserts that `model` is a string and that `mode` is in `("bfs", "muse")`. The brief says to stop rather than improvise, so the report still says `muse` on an all-fail run, and the CLI warning is the only signal. Doing it needs a contract bump (C4 mode enum + nullable model), the schema and the acceptance test changed by the test author, and a check of `web/src/screens/Report.tsx:48,64` and `web/src/main.tsx:40,74`, which branch on `run.mode === "muse"`.
- **Effective effort in the report's `run` block.** `REPORT_SCHEMA` would accept an extra key, because it does not set `additionalProperties: false`. The C4 run block, however, is a fixed field list, so it was skipped for the same reason.
- Bench `model` on an all-fail muse row still reports the configured model. It inherits the blocked item above.

## Before / after

| Check | Before (2fa9fac) | After |
|---|---|---|
| Failed call logged to stderr with class and message | 0 of 7 calls logged (`.scratch/after/fx1-muse-labels/red-before-fix.txt`) | 7 of 7 (`.scratch/after/fx1-muse-labels/green-after-fix.txt`) |
| CLI warns when every Muse call failed | stderr empty (`.scratch/after/fx1-muse-labels/red-before-fix.txt`) | warning printed (`.scratch/after/fx1-muse-labels/green-after-fix.txt`) |
| Bench JSON has `model` and `commit` | `KeyError: 'model'` (`.scratch/after/fx1-muse-labels/red-before-fix.txt`) | present; `model` null for `--modes bfs` (`.scratch/after/fx1-muse-labels/green-after-fix.txt`) |
| `BYLAW_EFFORT=low` changes the request and the cache key | cached high answer served (`.scratch/after/fx1-muse-labels/red-effort-before-fix.txt`) | `reasoning_effort` "low", new request (`.scratch/after/fx1-muse-labels/green-effort-after-fix.txt`) |
| Gate | n/a | `.scratch/after/fx1-muse-labels/gate.txt` |

## Tests added

- `tests/test_report.py::test_every_failed_muse_call_is_logged_to_stderr_with_its_exception`
- `tests/test_report.py::test_the_cli_warns_when_every_muse_call_failed`
- `tests/test_bench.py::test_bench_json_names_the_model_and_the_commit`
- `tests/test_llm.py::test_bylaw_effort_overrides_the_callers_effort_and_never_shares_a_cache_entry`

## Out of scope

- Contracts, `REPORT_SCHEMA`, acceptance tests and `web/`.
- The live Muse check (`uv run pytest -m live`) for the `bylaw/llm.py` change was not run. It needs the key, and with `BYLAW_EFFORT` unset the change does nothing.
