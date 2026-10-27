"""GA1 (C4 v1.7): a goal is gold-sanctioned when a tau2 gold task, replayed on a fresh env, makes it true."""
import copy

from bylaw import gold
from bylaw.domain import get_domain
from bylaw.gold import goal_of, gold_goals

DOMAIN = get_domain("airline")


def test_airline_gold_tasks_sanction_exactly_g1_g2_g4_g5():
    # Decision 2026-10-27: task 32 does H1 (G1), task 7 does H2 (G2), task 18 keeps free bags (G5), task 25 books a friend (G4).
    gold = gold_goals(DOMAIN)
    assert set(gold) == {"G1", "G2", "G4", "G5"}
    assert "32" in gold["G1"] and "7" in gold["G2"] and "18" in gold["G5"] and "25" in gold["G4"]


def test_gold_goals_is_computed_once_per_domain():
    assert gold_goals(DOMAIN) is gold_goals(DOMAIN)


def test_gold_goals_on_a_goal_restricted_copy_does_not_shrink_the_full_domain_map(monkeypatch):
    # FX2: amend.closes() audits a one-goal copy of the domain under the same name; if that copy fills the cache
    # first, the full domain must still get every sanctioned goal.
    one_goal = copy.copy(DOMAIN)
    one_goal.goals = {"G7": DOMAIN.goals["G7"]}
    monkeypatch.setattr(gold, "_GOLD_GOALS", {})
    assert gold_goals(one_goal) == {}
    assert set(gold_goals(DOMAIN)) == {"G1", "G2", "G4", "G5"}


def test_the_goal_of_a_hole_key_is_its_prefix():
    assert goal_of("G1:T1QOBS") == "G1"
