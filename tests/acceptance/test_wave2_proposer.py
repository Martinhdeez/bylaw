"""Acceptance tests for PR1: bounded search (C6) and the bench CLI (C5).

Written blind from docs/plan/01-engine/requirements.md and contracts.md.
C5 gives bench no offline mode, so the whole bench test is @pytest.mark.live.
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


# ---------- REQ-PR1-2 (live: bench always runs muse mode) ----------

@pytest.mark.live
def test_REQ_PR1_2_bench_prints_and_writes_bfs_and_muse_table(tmp_path):
    out = tmp_path / "bench.json"
    proc = subprocess.run(
        [sys.executable, "-m", "bylaw", "bench", "--domain", "airline", "--budget", "30", "-o", str(out)],
        cwd=ROOT, capture_output=True, text=True, timeout=1800,
    )
    assert proc.returncode == 0, proc.stderr[-4000:]
    text = proc.stdout.lower()
    for mode in ("bfs", "muse"):
        assert mode in text, f"no {mode} row in the printed table"
    for column in (r"holes", r"tool[ _-]?calls", r"llm[ _-]?calls", r"wall|seconds|time"):
        assert re.search(column, text), f"no {column!r} column in the printed table"
    data = json.loads(out.read_text())
    dumped = json.dumps(data).lower()
    assert "bfs" in dumped and "muse" in dumped
