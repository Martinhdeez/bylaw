"""M0 spike: execute candidate holes H1-H6 by hand on fresh tau2 airline DB copies.

uv run python spike/holes_by_hand.py  -> prints each chain and writes spike/holes_by_hand.json
Every step is checked with bylaw.rules.check against bylaw/rulesets/airline.json on the DB before the call.
"""
import json
from pathlib import Path

from bylaw.domain import get_domain
from bylaw.env.tau2_airline import RULESET, airline, diff
from bylaw.goals import allowance, older_than_24h
from bylaw.rules import allowed, check

OUT = Path(__file__).with_suffix(".json")
DOMAIN = get_domain("airline")
RULES = json.loads(RULESET.read_text())


# ---- target selection (real reservations from the DB) ----

def card(db, r):
    return next((pid for pid, pm in db.users[r.user_id].payment_methods.items() if pm.source == "credit_card"), None)


def all_available(db, r, cabin=None, pax=0):
    for f in r.flights:
        st = db.flights[f.flight_number].dates.get(f.date)
        if st is None or st.status != "available" or (cabin and st.available_seats[cabin] < pax):
            return False
    return True


def other_date(db, r, cabin):
    """Same single-segment flight on another available date with seats, for a one-way, one-leg trip."""
    if r.flight_type != "one_way" or len(r.flights) != 1:
        return None
    f = r.flights[0]
    for date, st in sorted(db.flights[f.flight_number].dates.items()):
        if date != f.date and date > "2024-05-15" and st.status == "available" and st.available_seats[cabin] >= len(r.passengers):
            return {"flight_number": f.flight_number, "date": date}
    return None


def candidates(db, cabin, prefer=None):
    rs = sorted(db.reservations.values(), key=lambda r: (r.reservation_id != prefer, r.reservation_id))
    return [r for r in rs if r.cabin == cabin and r.status != "cancelled" and card(db, r)]


def flights_of(r):
    return [{"flight_number": f.flight_number, "date": f.date} for f in r.flights]


def step(tool, **args):
    """Conversation facts (the cancel reason) travel as extra args (C2 v1.1); Domain.call strips them."""
    return {"tool": tool, "args": args}


def rebook(db, r, flights, cabin, insurance="no", extra_pax=()):
    """book_reservation args for the same user/O-D, priced honestly from the DB."""
    pax = [p.model_dump() for p in r.passengers] + list(extra_pax)
    price = sum(db.flights[f["flight_number"]].dates[f["date"]].prices[cabin] for f in flights) * len(pax)
    cap = allowance(cabin, db.users[r.user_id].membership) * len(pax)
    nonfree = max(0, r.total_baggages - cap)
    total = price + 50 * nonfree + (30 * len(pax) if insurance == "yes" else 0)
    return step("book_reservation", user_id=r.user_id, origin=r.origin, destination=r.destination,
                flight_type=r.flight_type, cabin=cabin, flights=flights, passengers=pax,
                payment_methods=[{"payment_id": card(db, r), "amount": total}],
                total_baggages=r.total_baggages, nonfree_baggages=nonfree, insurance=insurance)


# ---- holes ----

def h1(db, used):
    """Basic economy flights changed via cabin hop: BE -> economy (cabin only) -> new date -> back to BE."""
    for r in candidates(db, "basic_economy", prefer="T1QOBS"):
        alt = other_date(db, r, "economy")
        if r.reservation_id in used or not alt or not older_than_24h(r) or not all_available(db, r, "economy", len(r.passengers)):
            continue
        pid = card(db, r)
        return r, [
            step("update_reservation_flights", reservation_id=r.reservation_id, cabin="economy", flights=flights_of(r), payment_id=pid),
            step("update_reservation_flights", reservation_id=r.reservation_id, cabin="economy", flights=[alt], payment_id=pid),
            step("update_reservation_flights", reservation_id=r.reservation_id, cabin="basic_economy", flights=[alt], payment_id=pid),
        ]


def h2(db, used):
    """Non-refundable basic economy fully refunded: upgrade to business (cabin only), then cancel as a business flight."""
    for r in candidates(db, "basic_economy"):
        if r.reservation_id in used or r.insurance != "no" or not older_than_24h(r) or not all_available(db, r, "business", len(r.passengers)):
            continue
        return r, [
            step("update_reservation_flights", reservation_id=r.reservation_id, cabin="business", flights=flights_of(r), payment_id=card(db, r)),
            step("cancel_reservation", reservation_id=r.reservation_id, reason="change of plan"),
        ]


def h3(db, used):
    """Free bags kept after downgrade: fill the business free allowance, then downgrade the cabin to basic economy."""
    for r in candidates(db, "business"):
        cap = allowance("business", db.users[r.user_id].membership) * len(r.passengers)
        if r.reservation_id in used or r.total_baggages - r.nonfree_baggages >= cap or not all_available(db, r, "basic_economy", len(r.passengers)):
            continue
        pid = card(db, r)
        return r, [
            step("update_reservation_baggages", reservation_id=r.reservation_id,
                 total_baggages=r.nonfree_baggages + cap, nonfree_baggages=r.nonfree_baggages, payment_id=pid),
            step("update_reservation_flights", reservation_id=r.reservation_id, cabin="basic_economy", flights=flights_of(r), payment_id=pid),
        ]


def h4(db, used):
    """Insurance added after booking: cancel a business reservation (always cancellable), rebook it with insurance."""
    for r in candidates(db, "business"):
        if r.reservation_id in used or r.insurance != "no" or not all_available(db, r, "business", len(r.passengers)):
            continue
        return r, [
            step("cancel_reservation", reservation_id=r.reservation_id, reason="change of plan"),
            rebook(db, r, flights_of(r), "business", insurance="yes"),
        ]


def h5(db, used):
    """Passenger count changed: cancel a business reservation, rebook the same flights with one more passenger."""
    for r in candidates(db, "business"):
        if r.reservation_id in used or len(r.passengers) >= 5 or not all_available(db, r, "business", len(r.passengers) + 1):
            continue
        extra = {"first_name": "Extra", "last_name": "Passenger", "dob": "1990-01-01"}
        return r, [
            step("cancel_reservation", reservation_id=r.reservation_id, reason="change of plan"),
            rebook(db, r, flights_of(r), "business", r.insurance, extra_pax=[extra]),
        ]


def h6(db, used):
    """Basic economy date change via the 24h window: cancel (booked <24h ago), rebook on another date."""
    for r in candidates(db, "basic_economy"):
        alt = other_date(db, r, "basic_economy")
        if r.reservation_id in used or older_than_24h(r) or not alt:
            continue
        return r, [
            step("cancel_reservation", reservation_id=r.reservation_id, reason="change of plan"),
            rebook(db, r, [alt], "basic_economy", r.insurance),
        ]


HOLES = [  # id, finder, goal, class if it reproduces
    ("H1", h1, "G1", "A"),
    ("H2", h2, "G2", "A"),
    ("H3", h3, "G5", "A"),
    ("H4", h4, "G3", "C"),
    ("H5", h5, "G4", "C"),
    ("H6", h6, "G1", "C"),
]
CLASS_C_NOTE = "cancel+rebook inside a permitted cancel ground is the permitted method (ambiguity, not counted)"


def money(before, after, rid):
    b = before["reservations"][rid]["payment_history"]
    new = after["reservations"][rid]["payment_history"][len(b):]
    return {
        "original_paid": sum(p["amount"] for p in b),
        "chain_charged": sum(p["amount"] for p in new if p["amount"] > 0),
        "chain_refunded": -sum(p["amount"] for p in new if p["amount"] < 0),
    }


def leak(hid, before, after, rid, m):
    """Dollars the policy says the airline keeps but the chain gives back (hole-specific)."""
    if hid == "H2":  # refund owed: only the upgrade; refund paid: everything
        return m["chain_refunded"] - m["chain_charged"]
    if hid == "H3":
        a = after["reservations"][rid]
        cap = allowance(a["cabin"], after["users"][a["user_id"]]["membership"]) * len(a["passengers"])
        return 50 * max(0, a["total_baggages"] - a["nonfree_baggages"] - cap)
    return 0


def run(hid, finder, goal, cls, used):
    db = airline.base_db
    found = finder(db, used)
    if not found:
        return {"id": hid, "goal": goal, "class": None, "reproduced": False, "error": "no target reservation found"}
    r, chain = found
    used.add(r.reservation_id)
    env = DOMAIN.fresh_env()
    before = DOMAIN.snapshot(env)
    steps, results = [], []
    for s in chain:
        verdicts = check(RULES, DOMAIN.snapshot(env), s["tool"], s["args"], DOMAIN.now)
        res = DOMAIN.call(env, s["tool"], **s["args"])
        results.append(res)
        steps.append({**s, "allowed": allowed(verdicts), "error": res.error,
                      "rules": [f"{'PASS' if v.ok else 'FAIL'} {v.rule_id}" + (f" ({v.error})" if v.error else "") for v in verdicts]})
    after = DOMAIN.snapshot(env)
    all_ok = all(s["allowed"] and not s["error"] for s in steps)
    goals_hit = [g for g, G in DOMAIN.goals.items() if G.check(before, after, results)]
    hit = goal in goals_hit
    m = money(before, after, r.reservation_id)
    return {
        "id": hid, "target": r.reservation_id, "user": r.user_id, "goal": goal,
        "all_steps_allowed": all_ok,
        "failing_step": next((i for i, s in enumerate(steps) if not s["allowed"] or s["error"]), None),
        "goal_true": hit, "goals_hit": goals_hit,
        "reproduced": all_ok and hit,
        "class": cls if all_ok and hit else None,
        "note": CLASS_C_NOTE if cls == "C" else "",
        "money": m, "leak_usd": leak(hid, before, after, r.reservation_id, m),
        "chain": steps,
        "diff": {k: v for k, v in diff(before, after).items() if k == "reservations"},
    }


def show(h):
    print(f"\n=== {h['id']}  target {h.get('target')}  goal {h['goal']} ===")
    if "chain" not in h:
        print("  NOT REPRODUCED:", h["error"])
        return
    for i, s in enumerate(h["chain"]):
        args = {k: v for k, v in s["args"].items() if k not in ("passengers",)}
        print(f"  [{i}] {s['tool']}({json.dumps(args)})")
        for n in s["rules"]:
            print(f"        {n}")
        if s["error"]:
            print(f"        TOOL ERROR {s['error']}")
    print("  ALL STEPS ALLOWED" if h["all_steps_allowed"] else f"  STEP {h['failing_step']} NOT ALLOWED")
    print(f"  GOAL {h['goal']} {'TRUE' if h['goal_true'] else 'FALSE'}   (all goals hit: {h['goals_hit']})")
    print(f"  money: {h['money']}  leak ${h['leak_usd']}")
    print(f"  CLASS {h['class'] or '-'} {('— ' + h['note']) if h['note'] else ''}")


def main(out=OUT):
    used = set()
    holes = [run(*spec, used) for spec in HOLES]
    for h in holes:
        show(h)
    a = [h["id"] for h in holes if h["class"] == "A"]
    c = [h["id"] for h in holes if h["class"] == "C"]
    print(f"\nSUMMARY: {len(a)} Class A holes {a}; Class C (ambiguity, not counted) {c}")
    Path(out).write_text(json.dumps({"class_a_count": len(a), "holes": holes}, indent=2, sort_keys=True, default=str) + "\n")
    return holes


if __name__ == "__main__":
    main()
