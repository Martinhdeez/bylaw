"""EX1: executor runs chains on fresh DB copies with per-step rule verdicts (REQ-EX1-4)."""
import json

from bylaw.domain import get_domain
from bylaw.env.tau2_airline import RULESET
from bylaw.executor import replay, run

DOMAIN = get_domain("airline")
RULES = json.loads(RULESET.read_text())
# T1QOBS: basic economy, uninsured, booked 2024-05-09 (>24h before the clock), paid with credit_card_9875103.
CANCEL = {"tool": "cancel_reservation", "args": {"reservation_id": "T1QOBS", "reason": "change of plan"}}
UPGRADE = {"tool": "update_reservation_flights", "args": {
    "reservation_id": "T1QOBS", "cabin": "business",
    "flights": [{"flight_number": "HAT060", "date": "2024-05-26"}], "payment_id": "credit_card_9875103"}}


def test_replay_reports_only_the_changed_record_with_before_and_after():
    out = replay(DOMAIN, [UPGRADE])
    assert [s["ok"] for s in out["steps"]] == [True]
    assert list(out["diff"]) == ["reservations"]
    change = out["diff"]["reservations"]["T1QOBS"]
    assert (change["before"]["cabin"], change["after"]["cabin"]) == ("basic_economy", "business")
    assert list(out["diff"]["reservations"]) == ["T1QOBS"]


def test_replay_starts_from_a_fresh_db_each_time():
    first, second = replay(DOMAIN, [UPGRADE]), replay(DOMAIN, [UPGRADE])
    assert first["diff"] == second["diff"]  # the second run did not see the first one's upgrade


def test_run_stops_at_a_step_the_rules_forbid_and_does_not_execute_it():
    out = run(DOMAIN, [CANCEL, UPGRADE], RULES)
    assert [s["ok"] for s in out["steps"]] == [False]
    assert any(not v["ok"] and v["rule_id"] == "R-cancel-ground" for v in out["steps"][0]["verdicts"])
    assert out["diff"] == {}


def test_run_lets_the_upgrade_then_cancel_chain_through():
    out = run(DOMAIN, [UPGRADE, CANCEL], RULES)
    assert [s["ok"] for s in out["steps"]] == [True, True]
    assert out["diff"]["reservations"]["T1QOBS"]["after"]["status"] == "cancelled"
