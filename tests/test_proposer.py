"""EX1: bounded BFS behind the C6 interface: write tools only, depth <= 4, budget = write steps yielded."""
import itertools
import json

import pytest

from bylaw.domain import get_domain
from bylaw.env.tau2_airline import RULESET
from bylaw.proposer import MAX_DEPTH, search

DOMAIN = get_domain("airline")
RULES = json.loads(RULESET.read_text())


@pytest.mark.parametrize("budget", [0, 1, 50])
def test_search_never_yields_more_write_steps_than_the_budget(budget):
    chains = list(itertools.islice(search(DOMAIN, RULES, budget, use_llm=False), budget + 1))
    assert sum(len(c) for c in chains) <= budget
    assert chains or budget == 0


def test_chains_are_write_only_bounded_and_shortest_first():
    chains = list(search(DOMAIN, RULES, 300, use_llm=False))
    assert all(1 <= len(c) <= MAX_DEPTH and all(t in DOMAIN.write_tools for t, _ in c) for c in chains)
    assert [len(c) for c in chains[:5]] == [1] * 5  # BFS: depth 1 comes before deeper chains


def test_search_is_deterministic():
    a = list(search(DOMAIN, RULES, 100, use_llm=False))
    assert a == list(search(DOMAIN, RULES, 100, use_llm=False))
