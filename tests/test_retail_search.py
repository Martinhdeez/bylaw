"""SR1: bounded BFS on tau2 retail and the R6 payment-switch-then-cancel over-refund (REQ-SR1-1)."""
import json
from pathlib import Path

import pytest

from bylaw import proposer, report as report_mod
from bylaw.domain import get_domain
from bylaw.proposer import MAX_DEPTH, search
from bylaw.report import audit

DOMAIN = get_domain("retail")
RULES = json.loads((Path(__file__).resolve().parents[1] / "bylaw/rulesets/retail.json").read_text())
ORDER = "#W1068289"  # pending, paid 3453.28 by gift card; the user also has a PayPal account


def test_retail_search_proposes_write_chains_on_real_orders_within_budget():
    chains = list(search(DOMAIN, RULES, 200, use_llm=False))
    db = DOMAIN.snapshot(DOMAIN.fresh_env())
    assert chains and sum(len(c) for c in chains) <= 200
    for chain in chains:
        assert 1 <= len(chain) <= MAX_DEPTH
        for tool, args in chain:
            assert tool in DOMAIN.write_tools
            assert args.get("order_id") in db["orders"] or args.get("user_id") in db["users"]


def test_retail_moves_name_real_items_variants_and_payment_methods():
    db = DOMAIN.snapshot(DOMAIN.fresh_env())
    for tool, args in (c[0] for c in search(DOMAIN, RULES, 300, use_llm=False) if len(c) == 1):
        if "order_id" not in args:
            continue
        order = db["orders"][args["order_id"]]
        user = db["users"][order["user_id"]]
        if "payment_method_id" in args:
            assert args["payment_method_id"] in user["payment_methods"]
        for old, new in zip(args.get("item_ids", []), args.get("new_item_ids", [])):
            item = next(i for i in order["items"] if i["item_id"] == old)
            assert new in db["products"][item["product_id"]]["variants"] and new != old


@pytest.fixture(scope="module")
def r6_report():
    def only_order(*a, **k):
        db = DOMAIN.snapshot(DOMAIN.fresh_env())
        moves = proposer.DOMAINS["retail"]
        for depth in (1, 2):
            yield from proposer._chains(db, ORDER, moves.state(db, ORDER), depth, None, moves)

    mp = pytest.MonkeyPatch()
    mp.setattr(report_mod, "search", only_order)
    yield audit(DOMAIN, RULES, budget=500)
    mp.undo()


def test_payment_switch_then_cancel_over_refund_is_a_class_A_hole(r6_report):
    hole = next(h for h in r6_report["holes"] if h["key"] == "R6:" + ORDER)
    assert [s["tool"] for s in hole["chain"]] == ["modify_pending_order_payment", "cancel_pending_order"]
    assert hole["replays"] == "5/5" and hole["gold"] == {"sanctioned": False, "tasks": []}
    assert hole["money_delta"] > 0  # the customer got back more than they paid


def test_retail_keys_name_the_order(r6_report):
    for e in r6_report["holes"] + r6_report["contradictions"] + r6_report["ambiguities"]:
        assert e["key"].endswith(":" + ORDER), e["key"]
