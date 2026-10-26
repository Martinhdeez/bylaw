# Spike output determinism (EN1 split-off)

## Problem

`make check` rewrote the tracked `spike/holes_by_hand.json`, and the content changed between runs. Every gate run left the tree dirty, so `harness-gate` could not stamp any branch. Rule broken: the gate must run on a clean tree and leave it clean.

## Root cause

- `tests/test_spike.py:16` called `holes_by_hand.main()`, which always wrote to the tracked `OUT` (`spike/holes_by_hand.py:233`).
- `bylaw/env/tau2_airline.py:66` built the diff from a set union of record keys, so the order of the reservation keys in the diff changed between processes (hash seed). `json.dumps` did not sort keys either.

## Change

- `main(out=OUT)` writes to the path it is given. The test passes a `tmp_path`.
- `diff()` iterates collections and record keys in sorted order. The JSON is written with `sort_keys=True`.
- `spike/holes_by_hand.json` is regenerated once.

## Before / after

| Check | Before | After |
|---|---|---|
| Two spike runs, diff lines | 77 (`.scratch/after/spike-determinism/old-two-runs-diff.txt`) | 0 (`.scratch/after/spike-determinism/new-two-runs-diff.txt`) |
| New test on the old code | fails (`.scratch/after/spike-determinism/red.txt`) | passes (`.scratch/after/spike-determinism/make-check.txt`) |
| Spike result | 3 Class A (committed JSON) | 3 Class A (`.scratch/after/spike-determinism/spike-output.txt`) |

## Tests added

`tests/test_spike.py::test_spike_output_is_deterministic_and_leaves_the_tracked_file_alone`

## Out of scope

The EN1 rules work (separate branch `feat/en1-rules`).
