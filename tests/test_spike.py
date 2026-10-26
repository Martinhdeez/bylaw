import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spike"))
import holes_by_hand  # noqa: E402

from bylaw.domain import get_domain  # noqa: E402
from bylaw.rules import allowed, check  # noqa: E402

DOMAIN = get_domain("airline")


@pytest.fixture(scope="module")
def holes(tmp_path_factory):
    return holes_by_hand.main(tmp_path_factory.mktemp("spike") / "holes.json")


def test_at_least_three_class_a(holes):
    class_a = [h for h in holes if h["class"] == "A"]
    assert [h["id"] for h in class_a] == ["H1", "H2", "H3"]
    for h in class_a:
        assert h["goal_true"]
        assert all(s["allowed"] and s["error"] is None for s in h["chain"])


def test_cancel_rebook_is_never_counted(holes):
    assert all(h["class"] != "A" for h in holes if h["id"] in ("H4", "H5", "H6"))


def test_goals_false_on_untouched_db():
    snap = DOMAIN.snapshot(DOMAIN.fresh_env())
    assert {g: goal.check(snap, snap, []) for g, goal in DOMAIN.goals.items()} == {g: False for g in DOMAIN.goals}


def test_rules_block_the_direct_route():
    """Negative control: the one-step versions of H1/H2 must fail the JSON rules."""
    db = holes_by_hand.airline.base_db
    r = db.reservations["T1QOBS"]  # basic economy, no insurance, booked >24h ago
    pid = holes_by_hand.card(db, r)
    alt = holes_by_hand.other_date(db, r, "basic_economy")
    snap = DOMAIN.snapshot(DOMAIN.fresh_env())
    change = {"reservation_id": "T1QOBS", "cabin": "basic_economy", "flights": [alt], "payment_id": pid}
    cancel = {"reservation_id": "T1QOBS", "reason": "change of plan"}
    assert not allowed(check(holes_by_hand.RULES, snap, "update_reservation_flights", change, DOMAIN.now))
    assert not allowed(check(holes_by_hand.RULES, snap, "cancel_reservation", cancel, DOMAIN.now))


def test_spike_output_is_deterministic_and_leaves_the_tracked_file_alone(tmp_path):
    tracked = holes_by_hand.OUT.read_bytes()
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    holes_by_hand.main(a)
    holes_by_hand.main(b)
    assert a.read_text() == b.read_text()
    assert holes_by_hand.OUT.read_bytes() == tracked
    assert json.loads(a.read_text())["class_a_count"] == 3
