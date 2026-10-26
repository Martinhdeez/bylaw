"""Hand-written per-tool rules for tau2 airline, transcribed from policy.md.

check(db, step) evaluates the rules for one tool call against the DB state *before* the call.
A step is {"tool": str, "args": dict, "meta": dict}; meta carries facts the agent obtains from the
user and the tool does not take: the cancellation "reason", and for send_certificate the
"reservation_id" and "complaint" ("cancelled" | "delayed").
Not checkable here (conversation-level): explicit user confirmation, "bags the user does not need".
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from bylaw.goals import NOW, allowance, flight_set

READ_ONLY = {
    "get_user_details", "get_reservation_details", "list_all_airports", "search_direct_flight",
    "search_onestop_flight", "get_flight_status", "calculate", "transfer_to_human_agents",
}
INSURANCE_REASONS = {"health", "weather"}  # "full refund ... given health or weather reasons"


@dataclass
class Verdict:
    ok: bool = True
    notes: list[str] = field(default_factory=list)

    def need(self, cond, rule):
        self.notes.append(("PASS " if cond else "FAIL ") + rule)
        self.ok = self.ok and bool(cond)


def _status(db, fn, date):
    f = db.flights.get(fn)
    return f.dates[date].status if f and date in f.dates else None


def _flown(db, r):
    return any(_status(db, f.flight_number, f.date) in ("flying", "landed") for f in r.flights)


def _route_ok(db, flights, origin, destination, flight_type):
    """Segments chain end to end; one way O->D, round trip O->...->D->...->O."""
    legs = [db.flights[f["flight_number"]] for f in flights if f["flight_number"] in db.flights]
    if len(legs) != len(flights) or not legs:
        return False
    if any(x.destination != y.origin for x, y in zip(legs, legs[1:])):
        return False
    if flight_type == "one_way":
        return legs[0].origin == origin and legs[-1].destination == destination
    return legs[0].origin == origin and legs[-1].destination == origin and any(l.destination == destination for l in legs[:-1])


def _payment_ok(v, user, payment_id):
    pm = user.payment_methods.get(payment_id)
    v.need(pm is not None, "payment method is in the user profile")
    v.need(pm is not None and pm.source in ("credit_card", "gift_card"), "single gift card or credit card for change/refund")


def check(db, step) -> Verdict:
    tool, args, meta = step["tool"], step["args"], step.get("meta", {})
    v = Verdict()
    if tool in READ_ONLY:
        v.notes.append("PASS read-only/generic tool")
        return v
    if tool == "book_reservation":
        return _book(db, args, v)

    if tool == "send_certificate":
        return _certificate(db, args, meta, v)

    r = db.reservations.get(args["reservation_id"])
    v.need(r is not None and r.status != "cancelled", "reservation exists and is active")
    if not v.ok:
        return v
    user = db.users[r.user_id]

    if tool == "cancel_reservation":
        reason = meta.get("reason")
        v.need(reason is not None, "cancellation reason obtained")
        v.need(not _flown(db, r), "no portion of the trip has been flown")
        grounds = {
            "booked within 24h": NOW - datetime.fromisoformat(r.created_at) <= timedelta(hours=24),
            "flight cancelled by airline": reason == "airline cancelled flight"
            and any(_status(db, f.flight_number, f.date) == "cancelled" for f in r.flights),
            "business flight": r.cabin == "business",
            "insured + covered reason": r.insurance == "yes" and reason in INSURANCE_REASONS,
        }
        met = [g for g, ok in grounds.items() if ok]
        v.need(met, f"cancel ground: {', '.join(met) or 'none'}")

    elif tool == "update_reservation_flights":
        new = {(f["flight_number"], f["date"]) for f in args["flights"]}
        cabin_change = args["cabin"] != r.cabin
        flights_change = new != flight_set(r)
        # Policy allows a cabin change "without changing the flights" and a flight change; never both at once.
        v.need(not (cabin_change and flights_change), "cabin and flights not changed in the same call")
        if cabin_change:
            v.need(not _flown(db, r), "cabin change: no flight in the reservation has been flown")
        if flights_change:
            v.need(r.cabin != "basic_economy", "flight change: reservation is not basic economy")
            v.need(_route_ok(db, args["flights"], r.origin, r.destination, r.flight_type),
                   "flight change: same origin, destination and trip type")
        _payment_ok(v, user, args["payment_id"])

    elif tool == "update_reservation_baggages":
        total, nonfree = args["total_baggages"], args["nonfree_baggages"]
        v.need(total >= r.total_baggages, "bags: can add but not remove (total)")
        v.need(nonfree >= r.nonfree_baggages, "bags: paid bags are not turned into free ones")
        free_cap = allowance(r.cabin, user.membership) * len(r.passengers)
        v.need(total - nonfree <= free_cap, f"bags: free bags within allowance ({free_cap})")
        v.need(user.payment_methods.get(args["payment_id"]) is not None, "payment method is in the user profile")

    elif tool == "update_reservation_passengers":
        v.need(len(args["passengers"]) == len(r.passengers), "passenger count unchanged")

    else:
        v.need(False, f"unknown tool {tool}")
    return v


def _book(db, args, v):
    user = db.users.get(args["user_id"])
    v.need(user is not None, "user exists")
    if user is None:
        return v
    pax = args["passengers"]
    v.need(1 <= len(pax) <= 5, "at most five passengers")
    v.need(_route_ok(db, args["flights"], args["origin"], args["destination"], args["flight_type"]),
           "flights match origin, destination and trip type")
    sources = [user.payment_methods[p["payment_id"]].source for p in args["payment_methods"] if p["payment_id"] in user.payment_methods]
    v.need(len(sources) == len(args["payment_methods"]), "all payment methods are in the user profile")
    v.need(sources.count("certificate") <= 1 and sources.count("credit_card") <= 1 and sources.count("gift_card") <= 3,
           "at most 1 certificate, 1 credit card, 3 gift cards")
    free_cap = allowance(args["cabin"], user.membership) * len(pax)
    v.need(args["nonfree_baggages"] == max(0, args["total_baggages"] - free_cap), f"bags: free allowance {free_cap} applied")
    return v


def _certificate(db, args, meta, v):
    user = db.users.get(args["user_id"])
    r = db.reservations.get(meta.get("reservation_id"))
    v.need(user is not None and r is not None and r.user_id == args["user_id"], "complaint is about one of the user's reservations")
    if not v.ok:
        return v
    v.need(user.membership in ("silver", "gold") or r.insurance == "yes" or r.cabin == "business",
           "eligible: silver/gold, insured, or flies business")
    statuses = {_status(db, f.flight_number, f.date) for f in r.flights}
    complaint = meta.get("complaint")
    if complaint == "cancelled":
        v.need("cancelled" in statuses, "a flight in the reservation was cancelled")
        v.need(args["amount"] == 100 * len(r.passengers), "amount is $100 x passengers")
    elif complaint == "delayed":
        v.need("delayed" in statuses, "a flight in the reservation is delayed")
        v.need(meta.get("changed_or_cancelled", r.status == "cancelled"), "reservation was changed or cancelled first")
        v.need(args["amount"] == 50 * len(r.passengers), "amount is $50 x passengers")
    else:
        v.need(False, "compensation only for cancelled or delayed flights")
    return v
