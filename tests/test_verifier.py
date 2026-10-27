"""EX1: a hole is proven only if every step passes the rules, the goal holds, and N replays agree (REQ-EX1-2)."""
import json

from bylaw.domain import get_domain
from bylaw.env.tau2_airline import RULESET
from bylaw.executor import run
from bylaw.verifier import prove

DOMAIN = get_domain("airline")
RULES = json.loads(RULESET.read_text())
CANCEL = {"tool": "cancel_reservation", "args": {"reservation_id": "T1QOBS", "reason": "change of plan"}}
UPGRADE = {"tool": "update_reservation_flights", "args": {
    "reservation_id": "T1QOBS", "cabin": "business",
    "flights": [{"flight_number": "HAT060", "date": "2024-05-26"}], "payment_id": "credit_card_9875103"}}


def test_upgrade_then_cancel_refunds_a_nonrefundable_ticket_and_is_proven_5_of_5():
    chain = [UPGRADE, CANCEL]
    assert prove(DOMAIN, RULES, "G2", chain, run(DOMAIN, chain, RULES)["diff"]) == "5/5"


def test_a_chain_the_rules_forbid_is_never_proven():
    chain = [CANCEL]
    assert prove(DOMAIN, RULES, "G2", chain, run(DOMAIN, chain, RULES)["diff"]) == "0/5"


def test_a_goal_that_does_not_hold_is_not_proven():
    chain = [UPGRADE]  # allowed, but nothing was refunded
    assert prove(DOMAIN, RULES, "G2", chain, run(DOMAIN, chain, RULES)["diff"], n=2) == "0/2"


def test_a_diff_that_the_replays_do_not_reproduce_is_not_proven():
    chain = [UPGRADE, CANCEL]
    assert prove(DOMAIN, RULES, "G2", chain, {}, n=2) == "0/2"
