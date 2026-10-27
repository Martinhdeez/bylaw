# LC1 Long-context mode and per-audit token counter

## Problem

- REQ-LC1-1: no way to give Muse the whole domain context in one prompt. The proposer prompt held the policy, the write tools and 8 sample targets. It had no read tools and no gold tasks. The report did not record prompt size.
- REQ-LC1-2: `stats.tokens` was `sum(muse.CALLS[billed_from:])`. `CALLS` is a process-wide list. When two audits overlap in one process (the API runs each one in a thread), each audit counts the other's calls too.

## Root cause

- `bylaw/report.py:143` (old line, `stats.tokens`): a slice of the global `bylaw.llm.CALLS` from the start of this audit to its end. Any call another thread made in that window counts here too.
- `bylaw/proposer.py:_ask` builds the prompt. Nothing could add context to it.

## Change

- `bylaw/llm.py`: `TALLY`, a `contextvars.ContextVar` holding a list. `_call` appends each billed call record to the list set in the current context. Contextvars are per thread, so concurrent audits never share a list.
- `bylaw/report.py`: `audit(..., long_context=False)`. The `counted` wrapper around the search's LLM calls sets `TALLY` to this audit's own list for each request. It runs inside the proposer's worker thread, so it works even though `ThreadPoolExecutor` does not copy contexts. `stats.tokens` sums that list. New `run.context_tokens` is the largest `prompt_tokens` the API returned for this audit (0 without Muse, or when every reply came from the cache). With `long_context`, each proposer request gets one more user message just before the goal message: `{"tools": domain.tools, "gold_tasks": load_gold(domain), "note": ...}`. The proposer already sends the whole `policy_text`, untruncated. `bylaw/proposer.py` is untouched (no C6 change).
- `bylaw/__main__.py`: `audit --long-context`. The summary line prints the largest prompt.

**Contract proposal (C4/C5):** `run.context_tokens: int >= 0` is added to `REPORT_SCHEMA` `run` as a required field, and `audit --long-context` is added to C5. Reports written before this change lack the field and fail the new schema. Only fresh audits are validated today (`tests/test_report.py`, `tests/acceptance/test_wave2_audit.py`).

## Before / after

Evidence lives under `.scratch/after/lc1-long-context/` in the builder worktree.

| Check | Before (0131546) | After (48951c5) |
|---|---|---|
| Two concurrent audits, 7 goals each, fake client billing 1000 or 7 prompt tokens plus 20 completion | audit A reports 7329 tokens = both audits' calls (`red-on-old-code.txt`) | A 7140, B 189, context_tokens 1000 and 7 (`tests/test_long_context.py`, green in `gate.txt`) |
| Long-context prompt has policy, every tool schema, gold tasks | `TypeError: audit() got an unexpected keyword argument 'long_context'` (`red-on-old-code.txt`) | passes (`gate.txt`) |
| CLI `--long-context` reaches `audit` | fails (`red-on-old-code.txt`) | passes (`gate.txt`) |
| Live `audit --domain airline --long-context`, budget 2000, default effort, `BYLAW_NO_CACHE=1`, **one run** | not measured | context_tokens 25303, tokens 269046, 7 LLM calls, 0 errors, 1999 tool calls, audit 569.41 s, wall-clock 587 s; 18 Class A, 123 Class C (`live-audit.txt`, `live-report.json`) |
| Live `pytest -m live tests/test_llm.py` | — | 1 passed (`live-pytest-llm.txt`) |

## Tests added

`tests/test_long_context.py`:
- each proposer request in long-context mode carries the exact `policy_text`, `domain.tools` and `load_gold(domain)`, with the goal message last; one request per goal;
- without the flag, no gold tasks are sent (control; it passes on old code too);
- `audit --long-context` passes `long_context=True` and `use_llm=True` to `audit`;
- two audits in threads through the real `bylaw.llm.structured` path. A barrier holds every request until all 14 are in flight, so the overlap is certain. Each audit reports its own tokens and context_tokens.

## Out of scope

- The C9 progress events (`api.py` `Job.emit`) still read the process-wide `llm.USAGE` (existing `ponytail:` note). Only the report's `stats.tokens` is per audit now.
- No `long_context` field on the C9 `AuditRequest`: REQ-LC1-1 names CLI + report only.
- Not measured: the prompt size without `--long-context` on the same run, and a second live run (variance).
- `BYLAW_EFFORT` (FX1) is not merged, so the live run used the default effort (`high` in `_ask`).
