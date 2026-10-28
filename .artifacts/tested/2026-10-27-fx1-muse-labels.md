# FX1: honest Muse labels (bfs-fallback, null model, run.effort), bench model and commit, BYLAW_EFFORT

## Problem

REQ-DM1-1 (docs/plan/03-product/requirements.md) requires every demo result to name the commit and the model that produced it.
- An audit whose every Muse call failed (for example, with no `MODEL_API_KEY`) wrote `run.mode: "muse"` and `run.model: "muse-spark-1.3"` and exited 0 without a word. The exception text was dropped.
- The bench JSON (`{domain, budget, rows}`) had no model and no top-level commit.
- Added by the coordinator: testing the app spends tokens at `effort="high"`, which amend, proposer and compiler hard-code. There was no way to lower it.

Contract 01 v1.9 (a000e53, last section of `docs/plan/01-engine/contracts.md`) sets the target:
- `mode` is `bfs|muse|bfs-fallback`;
- `model` is a string or null;
- `run.effort` is optional;
- the bench has a top-level `model` and `commit`.

## Root cause

- `bylaw/report.py:111-116` (`counted`, 2fa9fac): `except Exception:` counts the error and re-raises. The proposer swallows the error for the BFS fallback (C6 v1.8), so its class and message are lost.
- `bylaw/report.py:147-149` (2fa9fac): `mode` and `model` come from `use_llm` alone. Nothing checks whether any call succeeded.
- `bylaw/__main__.py:175` (2fa9fac): `cmd_bench` writes only `domain`, `budget` and `rows`.
- `bylaw/llm.py:61-66` (2fa9fac): `_call` sends the caller's `effort` with no override.

## Change

- `bylaw/report.py`:
  - Each failed Muse call prints `muse call failed, goal falls back to BFS: <Class>: <message>` to stderr. The per-goal BFS fallback is unchanged.
  - `run.mode` is `bfs-fallback` when Muse was requested, `llm_calls > 0`, and every call failed. Otherwise it is `muse`, or `bfs` without Muse.
  - `run.model` is null unless the mode is `muse`.
  - `run.effort` is the effort actually sent: the `BYLAW_EFFORT` override applied, and only to a model that takes an effort. It is absent for `bfs`.
  - `REPORT_SCHEMA`: `mode` enum gains `bfs-fallback`, `model` is `string|null`, and `effort` is an optional string.
- `bylaw/__main__.py`:
  - `cmd_audit` prints `WARNING: every Muse call failed (n/n); the report is labelled bfs-fallback, model null` to stderr when the mode is `bfs-fallback`.
  - `cmd_bench` adds top-level `model` (the muse row's `run.model`, so null when muse did not run or every call failed) and `commit`. The existing fields are kept.
- `bylaw/llm.py`: `effective_effort()` returns `BYLAW_EFFORT` or the requested effort. `_call` applies it before the request body is built. The body is the cache key, so low and high answers never share a cache entry. When the variable is unset, behaviour is unchanged. Documented in `.env.example` and in the module docstring.

## Before / after

All evidence files are under `.scratch/after/fx1-muse-labels/`.

| Check | Before | After |
|---|---|---|
| Failed call logged to stderr with class and message | 0 of 7 calls logged (`red-before-fix.txt`) | 7 of 7 (`green-after-fix.txt`) |
| CLI warns when every Muse call failed | stderr empty (`red-before-fix.txt`) | warning printed (`green-v19-after-fix.txt`) |
| All-fail run: `mode` / `model` | `'muse' == 'bfs-fallback'` fails (`red-v19-before-fix.txt`) | `bfs-fallback` / null, schema-valid (`green-v19-after-fix.txt`) |
| `run.effort` with `BYLAW_EFFORT=low` | missing (`red-v19-before-fix.txt`) | `"low"`; absent for bfs (`green-v19-after-fix.txt`) |
| Bench JSON `model` and `commit` | `KeyError: 'model'` (`red-before-fix.txt`) | present; null for `--modes bfs` (`green-after-fix.txt`) |
| Bench `model` when every muse call failed | the configured model (`red-v19-before-fix.txt`) | null (`green-v19-after-fix.txt`) |
| `BYLAW_EFFORT=low` changes the request and the cache key | cached high answer served (`red-effort-before-fix.txt`) | `reasoning_effort` "low", new request (`green-effort-after-fix.txt`) |
| Gate | n/a | `gate.txt` |

## Tests added

- `tests/test_report.py`:
  - `test_every_failed_muse_call_is_logged_to_stderr_with_its_exception`
  - `test_a_run_whose_every_muse_call_failed_is_labelled_bfs_fallback_with_no_model`
  - `test_a_partly_failed_muse_run_is_still_a_muse_run` (a guard: it passes before and after)
  - `test_run_effort_is_the_effort_sent_after_the_override_and_absent_for_bfs`
  - `test_the_cli_warns_when_every_muse_call_failed`
- `tests/test_bench.py`:
  - `test_bench_json_names_the_model_and_the_commit`
  - `test_bench_model_is_null_when_every_muse_call_failed`
- `tests/test_llm.py`:
  - `test_bylaw_effort_overrides_the_callers_effort_and_never_shares_a_cache_entry`

## Out of scope

- Writing acceptance tests. The v1.9 versions of `tests/acceptance/test_wave2_audit.py` and `test_wave2_proposer.py` were brought in unchanged from `test/03-product` 59ea0b9 (7f7cd9d), and the 3600 s amend timeout in `test_iter02_amend.py` came from `bylaw/build` (22731ff).
- `web/`, which still branches on `run.mode === "muse"`. The designer has been told.
- `uv run pytest -m live` was not run. It needs the key, and with `BYLAW_EFFORT` unset the `llm.py` change does nothing.
