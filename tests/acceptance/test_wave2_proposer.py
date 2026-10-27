"""Acceptance tests for PR1: bounded search (C6) and the bench CLI (C5).

Written blind from docs/plan/01-engine/requirements.md and contracts.md.
v1.2: `bench --modes bfs` runs offline and the bench JSON has a schema; the muse row is live.
"""
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAX_DEPTH = 4  # C6


@pytest.fixture(scope="module")
def domain():
    return importlib.import_module("bylaw.domain").get_domain("airline")


@pytest.fixture(scope="module")
def ruleset():
    return json.loads((ROOT / "bylaw" / "rulesets" / "airline.json").read_text())


@pytest.fixture(scope="module")
def search():
    return importlib.import_module("bylaw.proposer").search


def drain(gen, budget: int) -> list:
    """Collect chains, stopping as soon as the budget is overrun (guards an endless generator)."""
    chains, spent = [], 0
    for chain in gen:
        chains.append(chain)
        spent += len(chain)
        if spent > budget:
            break
    return chains


def assert_chain_shape(chain, domain) -> None:
    assert isinstance(chain, list)
    assert 1 <= len(chain) <= MAX_DEPTH, len(chain)
    for step in chain:
        tool, args = step
        assert tool in domain.write_tools, f"{tool} is not a WRITE tool"
        assert isinstance(args, dict)


# ---------- REQ-PR1-3 ----------

@pytest.mark.parametrize("budget", [0, 1, 7, 40])
def test_REQ_PR1_3_search_never_exceeds_budget(search, domain, ruleset, budget):
    chains = drain(search(domain, ruleset, budget, use_llm=False), budget)
    assert sum(len(c) for c in chains) <= budget


@pytest.mark.parametrize("budget", [1, 40])
def test_REQ_PR1_3_search_yields_write_only_chains_of_depth_at_most_4(search, domain, ruleset, budget):
    chains = drain(search(domain, ruleset, budget, use_llm=False), budget)
    assert chains, "search yielded nothing within a positive budget"
    for chain in chains:
        assert_chain_shape(chain, domain)


@pytest.mark.live
def test_REQ_PR1_3_llm_search_never_exceeds_budget(search, domain, ruleset):
    budget = 30
    chains = drain(search(domain, ruleset, budget, use_llm=True), budget)
    assert chains
    assert sum(len(c) for c in chains) <= budget
    for chain in chains:
        assert_chain_shape(chain, domain)


# ---------- REQ-PR1-2 ----------

BENCH_BUDGET = 30
ROW_KEYS = {"mode", "holes", "hole_keys", "tool_calls", "llm_calls", "tokens", "seconds"}


def bench(tmp_path, modes: str):
    out = tmp_path / "bench.json"
    proc = subprocess.run(
        [sys.executable, "-m", "bylaw", "bench", "--domain", "airline", "--budget", str(BENCH_BUDGET),
         "--modes", modes, "-o", str(out)],
        cwd=ROOT, capture_output=True, text=True, timeout=1800,
    )
    assert proc.returncode == 0, proc.stderr[-4000:]
    return proc.stdout, json.loads(out.read_text())


def assert_bench_shape(data: dict, modes: list[str]) -> dict:
    assert data["domain"] == "airline"
    assert data["budget"] == BENCH_BUDGET
    rows = {r["mode"]: r for r in data["rows"]}
    assert sorted(rows) == sorted(modes) and len(data["rows"]) == len(modes)
    for r in rows.values():
        assert ROW_KEYS <= set(r), ROW_KEYS - set(r)
        assert isinstance(r["hole_keys"], list) and all(isinstance(k, str) for k in r["hole_keys"])
        assert len(set(r["hole_keys"])) == len(r["hole_keys"])
        assert r["holes"] == len(r["hole_keys"])
        assert isinstance(r["tool_calls"], int) and 0 <= r["tool_calls"] <= BENCH_BUDGET
        assert isinstance(r["llm_calls"], int) and isinstance(r["tokens"], int)
        assert isinstance(r["seconds"], (int, float)) and r["seconds"] >= 0
    return rows


def assert_table_printed(stdout: str, modes: list[str]) -> None:
    text = stdout.lower()
    for mode in modes:
        assert mode in text, f"no {mode} row in the printed table"
    for column in (r"holes", r"tool[ _-]?calls", r"llm[ _-]?calls", r"wall|seconds|time"):
        assert re.search(column, text), f"no {column!r} column in the printed table"


def test_REQ_PR1_2_bench_bfs_runs_offline_and_writes_the_table(tmp_path):
    stdout, data = bench(tmp_path, "bfs")
    rows = assert_bench_shape(data, ["bfs"])
    assert rows["bfs"]["llm_calls"] == 0
    assert rows["bfs"]["tokens"] == 0
    assert rows["bfs"]["tool_calls"] > 0
    assert_table_printed(stdout, ["bfs"])


def test_C5_v19_bench_json_has_top_level_model_and_commit(tmp_path):
    _, data = bench(tmp_path, "bfs")
    assert "model" in data and (data["model"] is None or isinstance(data["model"], str)), data.get("model")
    assert isinstance(data.get("commit"), str) and data["commit"], data.get("commit")


@pytest.mark.live
def test_REQ_PR1_2_bench_prints_and_writes_bfs_and_muse_table(tmp_path):
    stdout, data = bench(tmp_path, "bfs,muse")
    rows = assert_bench_shape(data, ["bfs", "muse"])
    assert rows["bfs"]["llm_calls"] == 0
    assert rows["muse"]["llm_calls"] > 0
    assert_table_printed(stdout, ["bfs", "muse"])
