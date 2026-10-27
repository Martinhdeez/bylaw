"""GA1 (C4 v1.7): a goal is gold-sanctioned when a tau2 gold task, replayed on a fresh env, makes it true."""
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


def test_the_goal_of_a_hole_key_is_its_prefix():
    assert goal_of("G1:T1QOBS") == "G1"
