"""Search (contract C6): bounded BFS over chains of WRITE tool calls, arguments instantiated from domain.targets.

The budget counts executed write steps (C6 v1.2). A consumer that executes the chains sends back how many steps
of each one ran (`gen.send(n)`); plain iteration charges the whole chain. A chain is only proposed if it fits in
what is left, so the executed total never exceeds the budget.
Muse-guided proposals (`use_llm=True`) arrive with PR1.
"""
from datetime import date, datetime, timedelta
from itertools import groupby

from bylaw.goals import allowance

MAX_DEPTH = 4
CABINS = ("basic_economy", "economy", "business")
REASON = "change of plan"
MAX_SHIFT_DAYS = 30


def search(domain, ruleset: dict, budget: int, use_llm: bool):
    if use_llm:
        raise NotImplementedError("Muse-guided search is PR1; use --no-llm")
    if domain.name != "airline":
        raise NotImplementedError(f"no BFS move set for domain {domain.name!r}")
    db = domain.snapshot(domain.fresh_env())
    spent = 0
    pool = _pool(domain, db)
    # ponytail: batches of one target per stratum, BFS depth-major inside a batch; a smarter order is PR1's job.
    for batch in _batches(pool):
        for depth in range(1, MAX_DEPTH + 1):
            for rid in batch:
                for chain in _chains(db, rid, _state(db, rid), depth, None):
                    if spent + len(chain) > budget:
                        return
                    executed = yield chain
                    spent += len(chain) if executed is None else executed


def _pool(domain, db) -> list[list[str]]:
    """Target reservations from domain.targets, one list per stratum (cabin, insurance, booked within 24h).
    Only reservations whose user has a credit card: every money-moving write needs one. Inside a stratum,
    reservations whose legs are all still bookable, with seats in every cabin, come first: the rules
    block most writes on flown trips and a cabin change needs seats."""
    now = datetime.fromisoformat(domain.now)
    rids = {t["reservation_id"] for g in domain.goals for t in domain.targets(g)}
    rids = [rid for rid in sorted(rids) if _card(db, db["reservations"][rid]["user_id"])]

    def stratum(rid):
        r = db["reservations"][rid]
        return r["cabin"], r["insurance"], abs((now - datetime.fromisoformat(r["created_at"])).total_seconds()) <= 86400

    def blocked(rid):
        r = db["reservations"][rid]
        days = [db["flights"][f["flight_number"]]["dates"].get(f["date"], {}) for f in r["flights"]]
        return not all(d.get("status") == "available" and min(d["available_seats"].values()) >= len(r["passengers"]) for d in days)

    return [list(g) for _, g in groupby(sorted(rids, key=lambda rid: (stratum(rid), blocked(rid), rid)), key=stratum)]


def _batches(strata: list[list[str]]):
    """Round-robin over strata: batch i holds the i-th reservation of every stratum that has one."""
    for i in range(max(map(len, strata), default=0)):
        yield [s[i] for s in strata if i < len(s)]


def _card(db, user_id):
    return next((pid for pid, pm in sorted(db["users"][user_id]["payment_methods"].items()) if pm["source"] == "credit_card"), None)


def _state(db, rid) -> dict:
    r = db["reservations"][rid]
    return {"cabin": r["cabin"], "flights": [{"flight_number": f["flight_number"], "date": f["date"]} for f in r["flights"]],
            "total": r["total_baggages"], "nonfree": r["nonfree_baggages"], "cancelled": False, "booked": False}


def _shift(db, flights, cabin, pax):
    """The same flights moved by the smallest number of days that keeps every leg available with seats, or None."""
    for k in sorted(range(-MAX_SHIFT_DAYS, MAX_SHIFT_DAYS + 1), key=lambda k: (abs(k), k)):
        if k == 0:
            continue
        moved = [{"flight_number": f["flight_number"], "date": (date.fromisoformat(f["date"]) + timedelta(days=k)).isoformat()} for f in flights]
        days = [db["flights"][f["flight_number"]]["dates"].get(f["date"]) for f in moved]
        if all(d and d["status"] == "available" and d["available_seats"][cabin] >= pax for d in days):
            return moved
    return None


def _moves(db, rid, st):
    """(kind, tool, args, next_state) for every write the BFS tries from abstract state `st`."""
    r = db["reservations"][rid]
    user = db["users"][r["user_id"]]
    pid, pax = _card(db, r["user_id"]), len(r["passengers"])
    if st["cancelled"]:
        if st["booked"]:
            return
        flights = _shift(db, st["flights"], st["cabin"], pax)
        if flights:  # rebook the cancelled trip on another date, priced honestly
            cap = allowance(st["cabin"], user["membership"]) * pax
            nonfree = max(0, st["total"] - cap)
            price = sum(db["flights"][f["flight_number"]]["dates"][f["date"]]["prices"][st["cabin"]] for f in flights) * pax
            total = price + 50 * nonfree + (30 * pax if r["insurance"] == "yes" else 0)
            yield "book", "book_reservation", {
                "user_id": r["user_id"], "origin": r["origin"], "destination": r["destination"],
                "flight_type": r["flight_type"], "cabin": st["cabin"], "flights": flights, "passengers": r["passengers"],
                "payment_methods": [{"payment_id": pid, "amount": total}], "total_baggages": st["total"],
                "nonfree_baggages": nonfree, "insurance": r["insurance"]}, {**st, "booked": True}
        return
    for cabin in CABINS:
        if cabin != st["cabin"]:
            yield "cabin", "update_reservation_flights", {"reservation_id": rid, "cabin": cabin, "flights": st["flights"],
                                                          "payment_id": pid}, {**st, "cabin": cabin}
    flights = _shift(db, st["flights"], st["cabin"], pax)
    if flights:
        yield "shift", "update_reservation_flights", {"reservation_id": rid, "cabin": st["cabin"], "flights": flights,
                                                      "payment_id": pid}, {**st, "flights": flights}
    free_cap = st["nonfree"] + allowance(st["cabin"], user["membership"]) * pax
    if free_cap > st["total"]:  # fill the free allowance of the current cabin
        yield "bags", "update_reservation_baggages", {"reservation_id": rid, "total_baggages": free_cap,
                                                      "nonfree_baggages": st["nonfree"], "payment_id": pid}, {**st, "total": free_cap}
    yield "cancel", "cancel_reservation", {"reservation_id": rid, "reason": REASON}, {**st, "cancelled": True}


def _chains(db, rid, st, depth, last):
    """Every move sequence of exactly `depth` from `st`. Two cabin changes or two date shifts in a row are
    pruned: they collapse into one call of the same kind."""
    for kind, tool, args, nxt in _moves(db, rid, st):
        if kind == last and kind in ("cabin", "shift"):
            continue
        if depth == 1:
            yield [(tool, args)]
        else:
            for rest in _chains(db, rid, nxt, depth - 1, kind):
                yield [(tool, args), *rest]
