"""RT1 unit tests: retail domain plug-in (C1), pre-registered goals, hand RuleSet (C2)."""
import copy
import json
import sys
from pathlib import Path

import pytest

from bylaw import rules
from bylaw.domain import StepResult, get_domain

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spike"))
import retail_holes_by_hand as spike  # noqa: E402

PENDING = "#W5918442"  # pending order in the tau2 retail DB


@pytest.fixture(scope="module")
def retail():
    return get_domain("retail")


def test_fresh_envs_are_independent(retail):
    e1, e2 = retail.fresh_env(), retail.fresh_env()
    before = retail.snapshot(e2)
    frozen = copy.deepcopy(before)
    r = retail.call(e1, "cancel_pending_order", order_id=PENDING, reason="no longer needed")
    assert r.ok and r.error is None
    assert retail.snapshot(e1)["orders"][PENDING]["status"] == "cancelled"
    assert retail.snapshot(e2) == before == frozen
    assert retail.snapshot(retail.fresh_env())["orders"][PENDING]["status"] == "pending"
    json.dumps(retail.snapshot(e1))


def test_call_strips_conversation_facts_and_reports_rejections(retail):
    env = retail.fresh_env()
    ok = retail.call(env, "get_order_details", order_id=PENDING, user_said="hi")
    assert ok.ok and ok.output["order_id"] == PENDING
    assert ok.args == {"order_id": PENDING, "user_said": "hi"}  # the step keeps what was proposed
    bad = retail.call(env, "cancel_pending_order", order_id=PENDING, reason="too expensive")
    assert not bad.ok and "Invalid reason" in bad.error


def test_surface(retail):
    names = {t["function"]["name"] for t in retail.tools}
    assert retail.name == "retail" and "Retail agent policy" in retail.policy_text
    assert retail.write_tools == {
        "cancel_pending_order", "exchange_delivered_order_items", "modify_pending_order_address",
        "modify_pending_order_items", "modify_pending_order_payment", "modify_user_address",
        "return_delivered_order_items",
    }
    assert retail.write_tools <= names and "get_order_details" in names
    assert retail.now
    seeds = retail.targets("R6")
    assert seeds and all(retail.base_db.orders[s["order_id"]].status == "pending" for s in seeds)
    assert all(s["user_id"] == retail.base_db.orders[s["order_id"]].user_id for s in seeds)
    assert {s["order_id"] for s in retail.targets("R7")} <= {k for k, o in retail.base_db.orders.items() if o.status == "delivered"}


# ---------- goals: false when untouched, true on the forbidden outcome, false on the permitted one ----------

DELIVERED = "#W1519594"  # delivered, paid with gift_card_1711656; user also has paypal_7729105
CANCELLED = "#W1106948"


@pytest.fixture
def snap(retail):
    return retail.snapshot(retail.fresh_env())


def step(tool, **args):
    return StepResult(tool, args, True, None, None)


def test_goals_registered_and_false_on_untouched_db(retail, snap):
    assert set(retail.goals) == {f"R{i}" for i in range(1, 9)}
    policy = " ".join(retail.policy_text.replace("*", "").split())
    for gid, g in retail.goals.items():
        assert g.id == gid and g.cls in {"A", "C"}
        for frag in g.policy_ref.split("\n"):
            assert " ".join(frag.split()) in policy, (gid, frag)
        assert g.check(snap, copy.deepcopy(snap), []) is False, gid


def test_R1_return_refund_must_go_to_original_or_gift_card(retail, snap):
    for pm, expected in [("paypal_7729105", True), ("gift_card_1711656", False)]:
        after = copy.deepcopy(snap)
        after["orders"][DELIVERED].update(status="return requested", return_items=["x"], return_payment_method_id=pm)
        assert retail.goals["R1"].check(snap, after, []) is expected, pm


def test_R2_return_on_pending_and_R7_address_on_delivered(retail, snap):
    after = copy.deepcopy(snap)
    after["orders"][PENDING].update(status="return requested", return_items=["x"], return_payment_method_id="p")
    assert retail.goals["R2"].check(snap, after, []) is True
    after = copy.deepcopy(snap)
    after["orders"][DELIVERED]["address"]["city"] = "Elsewhere"
    assert retail.goals["R7"].check(snap, after, []) is True
    after = copy.deepcopy(snap)
    after["orders"][PENDING]["address"]["city"] = "Elsewhere"  # permitted: pending order address change
    assert retail.goals["R7"].check(snap, after, []) is False


def test_R3_cancelled_order_touched(retail, snap):
    after = copy.deepcopy(snap)
    after["orders"][CANCELLED]["address"]["city"] = "Elsewhere"
    assert retail.goals["R3"].check(snap, after, []) is True


def test_R4_nothing_after_items_modified(retail, snap):
    after = copy.deepcopy(snap)
    after["orders"][PENDING]["address"]["city"] = "Elsewhere"
    items = step("modify_pending_order_items", order_id=PENDING, payment_method_id="p")
    addr = step("modify_pending_order_address", order_id=PENDING)
    assert retail.goals["R4"].check(snap, after, [items, addr]) is True
    assert retail.goals["R4"].check(snap, after, [addr, items]) is False


def test_R6_refunds_exceed_payments(retail, snap):
    after = copy.deepcopy(snap)
    paid = after["orders"][PENDING]["payment_history"][0]
    after["orders"][PENDING]["payment_history"].append({**paid, "transaction_type": "refund"})
    assert retail.goals["R6"].check(snap, after, []) is False  # one full refund: permitted
    after["orders"][PENDING]["payment_history"].append({**paid, "transaction_type": "refund"})
    assert retail.goals["R6"].check(snap, after, []) is True


# ---------- retail.json against C2 ----------

RULESET = json.loads((Path(__file__).resolve().parents[1] / "bylaw/rulesets/retail.json").read_text())


def test_ruleset_c2_shape_and_tools(retail):
    assert RULESET["domain"] == "retail" and set(RULESET) == {"domain", "tool_rules", "forbidden_goals"}
    ids = [r["id"] for r in RULESET["tool_rules"]]
    assert ids and len(ids) == len(set(ids))
    policy = " ".join(retail.policy_text.replace("*", "").split())
    for r in RULESET["tool_rules"]:
        assert all(isinstance(r[k], str) and r[k] for k in ("id", "tool", "allow_if", "policy_ref")), r
        assert r["tool"] in retail.write_tools, r["tool"]
        assert " ".join(r["policy_ref"].split()) in policy, r["id"]
    assert [(g["id"], g["policy_ref"]) for g in RULESET["forbidden_goals"]] == [(g.id, g.policy_ref) for g in retail.goals.values()]
    rules.validate(RULESET)


def test_item_rules_pair_old_and_new_items_by_position(retail, snap):
    """A swap that is valid as a set but pairs an item with another product's variant is rejected."""
    o = next(o for o in snap["orders"].values() if o["status"] == "pending" and len({i["product_id"] for i in o["items"]}) > 1)
    a, b = o["items"][0], next(i for i in o["items"] if i["product_id"] != o["items"][0]["product_id"])
    va = spike.other_variant(snap, a)
    vb = spike.other_variant(snap, b)
    args = {"order_id": o["order_id"], "item_ids": [a["item_id"], b["item_id"]], "payment_method_id": spike.original(o)}
    good = rules.check(RULESET, snap, "modify_pending_order_items", {**args, "new_item_ids": [va, vb]}, retail.now)
    crossed = rules.check(RULESET, snap, "modify_pending_order_items", {**args, "new_item_ids": [vb, va]}, retail.now)
    assert {v.rule_id: v.ok for v in good}["R-items-4"] is True
    assert {v.rule_id: v.ok for v in crossed}["R-items-4"] is False


def test_rules_block_the_direct_routes(retail, snap):
    """Negative controls: one-step versions of the forbidden outcomes are rejected by retail.json."""
    blocked = [
        ("cancel_pending_order", {"order_id": PENDING, "reason": "too expensive"}),
        ("modify_pending_order_address", {"order_id": DELIVERED}),
        ("modify_pending_order_address", {"order_id": CANCELLED}),
        ("return_delivered_order_items", {"order_id": DELIVERED, "item_ids": [snap["orders"][DELIVERED]["items"][0]["item_id"]],
                                          "payment_method_id": "paypal_7729105"}),
        ("return_delivered_order_items", {"order_id": PENDING, "item_ids": [], "payment_method_id": "x"}),
    ]
    for tool, args in blocked:
        assert not rules.allowed(rules.check(RULESET, snap, tool, args, retail.now)), (tool, args)
    ok = rules.check(RULESET, snap, "cancel_pending_order", {"order_id": PENDING, "reason": "no longer needed"}, retail.now)
    assert ok and rules.allowed(ok)


# ---------- spike ----------

def test_spike_payment_switch_then_cancel_overrefunds(retail):
    """H1: every step passes retail.json, yet the cancelled order refunds more than was paid (R6), reproducibly."""
    h = spike.run(retail, "H1", spike.h1, "R6")
    assert h["all_steps_allowed"] and h["goal_true"] and h["class"] == "A" and h["replays"] == "5/5"
    assert h["money"]["refunded"] > h["money"]["paid"]


def test_spike_counts_only_class_a_goals_and_reports_blocked_chains(retail):
    for hid, finder, goal in spike.HOLES:
        h = spike.run(retail, hid, finder, goal)
        if h["class"] is not None:
            assert h["all_steps_allowed"] and h["goal_true"] and h["class"] == retail.goals[goal].cls
        else:
            assert not h["reproduced"]
