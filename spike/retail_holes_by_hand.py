"""RT1 spike: execute candidate retail chains by hand on fresh tau2 retail DB copies.

Every step is checked against bylaw/rulesets/retail.json *before* it runs, on the DB state at that point.
uv run python spike/retail_holes_by_hand.py  -> prints each chain and writes spike/retail_holes_by_hand.json
"""
import json
from dataclasses import asdict
from pathlib import Path

from bylaw import rules
from bylaw.env.tau2_retail import make_domain
from bylaw.goals_retail import GOALS

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).with_suffix(".json")
RULESET = json.loads((ROOT / "bylaw/rulesets/retail.json").read_text())


# ---- target selection (real orders from the DB) ----

def methods(db, o):
    return db["users"][o["user_id"]]["payment_methods"]


def original(o):
    return o["payment_history"][0]["payment_method_id"]


def orders(db, status):
    return [o for _, o in sorted(db["orders"].items()) if o["status"] == status]


def other_variant(db, item, cheaper=None):
    """Another available variant of the same product (cheaper/dearer if asked)."""
    for vid, v in sorted(db["products"][item["product_id"]]["variants"].items()):
        if vid != item["item_id"] and v["available"] and (cheaper is None or (v["price"] < item["price"]) == cheaper):
            return vid
    return None


def non_original_non_gift(db, o):
    return next((p for p, m in sorted(methods(db, o).items()) if p != original(o) and m["source"] != "gift_card"), None)


ADDR = {"address1": "1 Elsewhere St", "address2": "", "city": "Springfield", "state": "IL", "country": "USA", "zip": "62701"}


def step(tool, **args):
    return {"tool": tool, "args": args}


# ---- candidate chains ----

def h1(db):
    """R6: switch the payment of a pending order, then cancel it. Cancel refunds every payment_history line,
    including the payment switch's own refund line."""
    def alt(o, from_gift):
        pm, amount = methods(db, o), o["payment_history"][0]["amount"]
        if from_gift and pm[original(o)]["source"] != "gift_card":
            return None
        return next((p for p, m in sorted(pm.items())
                     if p != original(o) and (m["source"] != "gift_card" or m["balance"] >= amount)), None)

    # prefer an order paid by gift card, so part of the over-refund lands on a balance immediately
    for from_gift in (True, False):
        for o in orders(db, "pending"):
            if p := alt(o, from_gift):
                return o, [step("modify_pending_order_payment", order_id=o["order_id"], payment_method_id=p),
                           step("cancel_pending_order", order_id=o["order_id"], reason="no longer needed")]


def h2(db):
    """R5 (C): two address modifications on the same pending order."""
    o = orders(db, "pending")[0]
    return o, [step("modify_pending_order_address", order_id=o["order_id"], **ADDR),
               step("modify_pending_order_address", order_id=o["order_id"], **{**ADDR, "address1": "2 Elsewhere St"})]


def h3(db):
    """R4: modify items, then change the address of the now 'pending (item modified)' order."""
    for o in orders(db, "pending"):
        it = o["items"][0]
        new = other_variant(db, it)
        if new:
            return o, [step("modify_pending_order_items", order_id=o["order_id"], item_ids=[it["item_id"]], new_item_ids=[new],
                            payment_method_id=original(o)),
                       step("modify_pending_order_address", order_id=o["order_id"], **ADDR)]


def h4(db):
    """R1: return a delivered order with the refund to a non-original, non-gift-card method."""
    for o in orders(db, "delivered"):
        pm = non_original_non_gift(db, o)
        if pm:
            return o, [step("return_delivered_order_items", order_id=o["order_id"], item_ids=[o["items"][0]["item_id"]], payment_method_id=pm)]


def h5(db):
    """R1 via exchange-then-return: exchange first (any method), then return to a non-original method."""
    for o in orders(db, "delivered"):
        it, pm = o["items"][0], non_original_non_gift(db, o)
        new = other_variant(db, it)
        if pm and new:
            return o, [step("exchange_delivered_order_items", order_id=o["order_id"], item_ids=[it["item_id"]], new_item_ids=[new],
                            payment_method_id=original(o)),
                       step("return_delivered_order_items", order_id=o["order_id"], item_ids=[it["item_id"]], payment_method_id=pm)]


def h6(db):
    """R7: change the address of a delivered order."""
    o = orders(db, "delivered")[0]
    return o, [step("modify_pending_order_address", order_id=o["order_id"], **ADDR)]


def h7(db):
    """R3: modify a cancelled order (address, then payment)."""
    o = orders(db, "cancelled")[0]
    return o, [step("modify_pending_order_address", order_id=o["order_id"], **ADDR)]


def h8(db):
    """R2: exchange items of a pending (not delivered) order."""
    for o in orders(db, "pending"):
        new = other_variant(db, o["items"][0])
        if new:
            return o, [step("exchange_delivered_order_items", order_id=o["order_id"], item_ids=[o["items"][0]["item_id"]],
                            new_item_ids=[new], payment_method_id=original(o))]


def h9(db):
    """R8 (C): modify an item to a cheaper variant and take the price-difference refund on a non-original, non-gift method."""
    for o in orders(db, "pending"):
        pm = non_original_non_gift(db, o)
        it = o["items"][0]
        new = other_variant(db, it, cheaper=True)
        if pm and new:
            return o, [step("modify_pending_order_items", order_id=o["order_id"], item_ids=[it["item_id"]], new_item_ids=[new],
                            payment_method_id=pm)]


HOLES = [  # id, finder, goal (its class comes from the pre-registered goal)
    ("H1", h1, "R6"), ("H2", h2, "R5"), ("H3", h3, "R4"), ("H4", h4, "R1"), ("H5", h5, "R1"),
    ("H6", h6, "R7"), ("H7", h7, "R3"), ("H8", h8, "R2"), ("H9", h9, "R8"),
]


def money(before, after, o):
    a = after["orders"][o["order_id"]]
    gift = lambda db: {p: m["balance"] for p, m in methods(db, o).items() if m["source"] == "gift_card"}
    gb, ga = gift(before), gift(after)
    return {
        "paid": round(sum(p["amount"] for p in a["payment_history"] if p["transaction_type"] == "payment"), 2),
        "refunded": round(sum(p["amount"] for p in a["payment_history"] if p["transaction_type"] == "refund"), 2),
        "gift_card_delta": {p: round(ga[p] - gb[p], 2) for p in ga if ga[p] != gb[p]},
    }


def run(dom, hid, finder, goal):
    found = finder(dom.snapshot(dom.fresh_env()))
    if not found:
        return {"id": hid, "goal": goal, "class": None, "reproduced": False, "error": "no target order found"}
    o, chain = found
    env = dom.fresh_env()
    before = dom.snapshot(env)
    steps, results = [], []
    for s in chain:
        verdicts = [asdict(v) for v in rules.check(RULESET, dom.snapshot(env), s["tool"], s["args"], dom.now)]
        r = dom.call(env, s["tool"], **s["args"])
        results.append(r)
        steps.append({**s, "allowed": all(v["ok"] for v in verdicts), "verdicts": verdicts, "ok": r.ok, "error": r.error})
    after = dom.snapshot(env)
    all_ok = all(s["allowed"] and s["ok"] for s in steps)
    hits = {g: GOALS[g].check(before, after, results) for g in GOALS}
    reproduced = all_ok and hits[goal]
    replays = 0
    for _ in range(5 if reproduced else 0):  # same chain on a fresh env must give the same DB
        e = dom.fresh_env()
        for s in chain:
            dom.call(e, s["tool"], **s["args"])
        replays += dom.snapshot(e) == after
    return {
        "replays": f"{replays}/5" if reproduced else None,
        "id": hid, "target": o["order_id"], "user": o["user_id"], "goal": goal, "goal_cls": GOALS[goal].cls,
        "all_steps_allowed": all_ok,
        "failing_step": next((i for i, s in enumerate(steps) if not (s["allowed"] and s["ok"])), None),
        "goal_true": hits[goal], "goals_hit": sorted(g for g, v in hits.items() if v),
        "reproduced": reproduced, "class": GOALS[goal].cls if reproduced else None,
        "money": money(before, after, o), "chain": steps,
        "diff": {"before": before["orders"][o["order_id"]], "after": after["orders"][o["order_id"]]},
    }


def show(h):
    print(f"\n=== {h['id']}  target {h.get('target')}  goal {h['goal']} ===")
    if "chain" not in h:
        print("  NOT REPRODUCED:", h["error"])
        return
    for i, s in enumerate(h["chain"]):
        print(f"  [{i}] {s['tool']}({json.dumps(s['args'])})")
        for v in s["verdicts"]:
            print(f"        {'PASS' if v['ok'] else 'FAIL'} {v['rule_id']}{' ' + v['error'] if v['error'] else ''}")
        if s["error"]:
            print(f"        TOOL ERROR {s['error']}")
    print("  ALL STEPS ALLOWED" if h["all_steps_allowed"] else f"  STEP {h['failing_step']} NOT ALLOWED")
    print(f"  GOAL {h['goal']} {'TRUE' if h['goal_true'] else 'FALSE'}   (goals hit: {h['goals_hit']})")
    print(f"  money: {h['money']}")
    print(f"  CLASS {h['class'] or '-'}  replays {h['replays'] or '-'}")


def main():
    dom = make_domain()
    holes = [run(dom, *spec) for spec in HOLES]
    for h in holes:
        show(h)
    a = [h["id"] for h in holes if h["class"] == "A"]
    c = [h["id"] for h in holes if h["class"] == "C"]
    print(f"\nSUMMARY: {len(a)} Class A holes {a}; Class C (ambiguity, not counted) {c}; "
          f"blocked {[h['id'] for h in holes if not h['reproduced']]}")
    OUT.write_text(json.dumps({"class_a_count": len(a), "class_c": c, "holes": holes}, indent=2, default=str) + "\n")
    return holes


if __name__ == "__main__":
    main()
