"""Policy compiler (contract C3): Muse turns a domain's policy + tool schemas into a RuleSet (C2)."""
import ast
import json
import random

from bylaw.domain import get_domain
from bylaw.llm import structured
from bylaw.rules import FUNCS, RULESET_SCHEMA, RuleError, check, hours_between, validate

SYSTEM = f"""You compile a customer-service agent policy into machine-checkable rules.

Return a RuleSet with:
1. tool_rules: preconditions on WRITE tool calls, checked on the DB as it is before the call. A call is
   allowed iff every rule for that tool evaluates truthy; a rule that raises (e.g. res is None) denies.
   - id: "R-<tool>-<n>"; tool: the exact tool name from the schemas.
   - allow_if: a Python expression, using ONLY:
     names: args (the call's arguments, dict), db (the whole DB snapshot, dict), now (ISO time string),
            res (the reservation/order named by args["reservation_id"] / args["order_id"], a dict, or None),
            user (the user named by args["user_id"] or by res["user_id"], a dict, or None);
     literals, and/or/not, comparisons, in / not in, subscripts and slices, d.get(key[, default]) on dicts,
     list/dict/set displays, comprehensions and generator expressions, arithmetic (no **), x if c else y;
     functions: {", ".join(sorted(FUNCS))}; keyword arguments are fine, *args/**kwargs are not.
     hours_between(a, b) = absolute hours between two ISO strings.
     No other names, attributes or methods (no .items(), .values(), .keys(), .lower(), ...), no imports.
     Use the exact field names and values shown in the DB record shapes and tool schemas.
   - Conversation facts: facts the policy needs but the tool signature lacks arrive as extra args keys:
     args["reason"] on cancel_reservation, exactly one of "change of plan" | "airline cancelled flight" |
     "health" | "weather" | "other"; on send_certificate, args["reservation_id"] (the
     reservation the complaint is about) and args["complaint"] ("cancelled" | "delayed").
     A fact the policy says the agent must obtain gets its own rule that it is present.
   - policy_ref: the policy sentence(s) the rule enforces, quoted verbatim from the policy.
   - note: one line on how the expression encodes the sentence, or "".
   How to write the rules:
   - One rule per policy condition. Do not merge conditions from different sentences into one rule, and
     do not add conditions the sentence does not state. Alternatives the policy lists as "any of the
     following" form one rule joined with `or`.
   - Every tool that acts on an existing record starts with its own rule that the record exists and is
     not cancelled.
   - A condition that applies only to some calls of a tool is an implication: `not (<trigger>) or <condition>`.
     For example a flight change is `{{(f['flight_number'], f['date']) for f in args['flights']}} !=
     {{(f['flight_number'], f['date']) for f in res['flights']}}` and a cabin change is `args['cabin'] != res['cabin']`.
   - Read DB facts from the DB: whether a flight segment was flown, delayed or cancelled is the status of
     db['flights'][number]['dates'][date]. Cover every status the condition means: a segment that has
     taken off has status 'flying' or 'landed'.
   - Where the policy says the API does not check a condition, encode it completely: e.g. new flights
     form one itinerary segment by segment (each segment's destination is the next one's origin) with the
     required origin, destination and trip type, looked up in db['flights'].
   - Size limits keep the bounds the domain implies (a reservation has at least one passenger).
   - Prefer plain subscripts (res['cabin']) to .get with invented defaults; a missing key denies anyway.
   Encode only what the tool call and the DB can show. Skip duties the DB cannot see (asking the user,
   confirmations, tone).
2. forbidden_goals: the outcomes the policy forbids, as end states of the database or money flows
   (e.g. "a basic economy reservation ends with different flights"), never as actions or tool calls.
   - id: "G1", "G2", ...; name: snake_case; policy_ref: the verbatim policy line; description: the end state.
Set domain to the domain name."""


def _db(domain) -> dict:
    return domain.snapshot(domain.fresh_env())


def _shape(v, depth=0):
    """A record trimmed to show field names and value shapes, not every entry."""
    if isinstance(v, list):
        return [_shape(x, depth + 1) for x in v[:2]]
    if isinstance(v, dict):
        items = list(v.items())
        if len(items) > 6 and depth and all(isinstance(x, dict) for _, x in items):
            items = items[:2]
        return {k: _shape(x, depth + 1) for k, x in items}
    return v


def compile_policy(domain, model: str | None = None, llm=None) -> dict:
    """RuleSet (C2) for `domain`. `llm` replaces `bylaw.llm.structured` (same signature), e.g. in tests."""
    llm = llm or structured
    db = _db(domain)
    shapes = {coll: _shape(next(iter(recs.values()))) for coll, recs in db.items() if isinstance(recs, dict) and recs}
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Domain: {domain.name}\nnow = {domain.now!r}\n\n# Policy\n{domain.policy_text}\n\n"
                                    f"# Tool schemas\n{json.dumps(domain.tools, indent=1)}\n\n"
                                    f"# DB record shapes (db[collection][id] = record)\n{json.dumps(shapes, indent=1)}"},
    ]
    tools = {t["function"]["name"] for t in domain.tools}
    for attempt in range(2):
        ruleset = llm(messages, RULESET_SCHEMA, "ruleset", effort="high", max_tokens=64000, model=model)
        try:
            validate(ruleset)
            unknown = {r["tool"] for r in ruleset["tool_rules"]} - tools
            if unknown:
                raise RuleError(f"unknown tools {sorted(unknown)}; use only {sorted(tools)}")
            return {**ruleset, "domain": domain.name}
        except RuleError as e:
            if attempt:
                raise
            messages += [{"role": "assistant", "content": json.dumps(ruleset)},
                         {"role": "user", "content": f"The RuleSet was rejected: {e}\nReturn the whole corrected RuleSet."}]


# --- match_rate ---------------------------------------------------------------------------------
#
# Probes are calls built from the tool's parameter schema and real DB records: the record's own values
# (flights, passengers, cabin, bags, payments from the user's profile), then one-key variants and random
# multi-key combinations. Conversation facts (C2 v1.1) are the args keys the rules read that the schema
# lacks; their candidates are "absent" plus the literals the rules compare with.

SAMPLE = 60      # records taken by stride over the collection, plus every record booked within RECENT_H of now
RECENT_H = 72
COMBOS = 12      # random multi-key variants per record
ABSENT = object()
CABINS = ["basic_economy", "economy", "business"]
NEW_PAX = {"first_name": "Ann", "last_name": "Lee", "dob": "1990-01-01"}


def _arg_keys_and_literals(exprs):
    keys, lits = set(), set()
    for e in exprs:
        try:
            tree = ast.parse(e, mode="eval")
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Subscript) and getattr(n.value, "id", None) == "args" and isinstance(n.slice, ast.Constant):
                keys.add(n.slice.value)
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                    and getattr(n.func.value, "id", None) == "args" and n.args and isinstance(n.args[0], ast.Constant):
                keys.add(n.args[0].value)
            elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                lits.add(n.value)
            elif isinstance(n, ast.Name) and n.id == "res":
                keys.add("reservation_id")  # ponytail: airline key; retail needs "order_id" when RT1 lands
    return keys, sorted(lits)


def _legs(r):
    return [{"flight_number": f["flight_number"], "date": f["date"]} for f in r.get("flights", [])]


def _own_first(own, values):
    return [own, *sorted({v for v in values if v != own})]


def _candidates(key, rid, r, db, lits, others):
    """Values to try for args[key] on a call about record `r`; the first one is the record's own value."""
    users = db.get("users", {})
    uid = r.get("user_id")
    pm = users.get(uid, {}).get("payment_methods", {})
    pays = sorted(pm)
    n = len(r.get("passengers", []))
    pax = r.get("passengers", [])
    route = (r.get("origin"), r.get("destination"), r.get("flight_type"))
    same_route = [o for o in others if (o.get("origin"), o.get("destination"), o.get("flight_type")) == route and o is not r]
    if key == "reservation_id":
        return [rid, "ZZZZZZ", *[o["reservation_id"] for o in others[:2] if o.get("reservation_id") != rid]]
    if key == "user_id":
        return [uid, next((k for k in sorted(users) if k != uid), "nobody"), "nobody"]
    if key == "flights":
        return [_legs(r), *[_legs(o) for o in same_route[:2]], *[_legs(o) for o in others[:2] if o is not r],
                _legs(r)[:1], list(reversed(_legs(r)))]
    if key == "cabin":
        return [r.get("cabin"), *[c for c in CABINS if c != r.get("cabin")]]
    if key == "passengers":
        return [pax, pax + [NEW_PAX], pax[:-1], [NEW_PAX] * 6]
    if key == "payment_id":
        return [*(pays or ["none"]), "credit_card_0000000"]
    if key == "payment_methods":
        hist = [{"payment_id": p["payment_id"], "amount": p["amount"]} for p in r.get("payment_history", [])[:1]]
        return [hist, *[[{"payment_id": p, "amount": 100}] for p in pays],
                [{"payment_id": p, "amount": 10} for p in pays], [{"payment_id": "credit_card_0000000", "amount": 100}]]
    if key in ("total_baggages", "nonfree_baggages"):
        own = r.get(key, 0)
        return _own_first(own, [max(0, own + d) for d in (-1, 1, 2, 3, 8)])
    if key == "amount":
        return [100 * n, 50 * n, 100, 37]
    if key in ("origin", "destination"):
        return [r.get(key), r.get("destination" if key == "origin" else "origin")]
    if key == "flight_type":
        return [r.get(key), "one_way" if r.get(key) == "round_trip" else "round_trip"]
    if key == "insurance":
        return [r.get(key), "no" if r.get(key) == "yes" else "yes"]
    return [ABSENT, *lits, True, False]


def _records(db, now):
    coll = db.get("reservations") or db.get("orders") or {}
    items = sorted(coll.items())
    sample = items[::max(1, len(items) // SAMPLE)]
    seen = {k for k, _ in sample}
    if now:
        sample += [(k, r) for k, r in items if k not in seen and r.get("created_at")
                   and hours_between(r["created_at"], now) <= RECENT_H]
    return sample


def probes(db: dict, now: str, params: set[str], exprs: list[str]) -> list[dict]:
    """Argument dicts for one tool, built from its parameters, DB records and the args keys the rules read."""
    keys, lits = _arg_keys_and_literals(exprs)
    keys = sorted(params | keys)
    records = _records(db, now)
    others = [r for _, r in records]
    rng = random.Random(0)
    out = []
    for rid, r in records:
        cands = {k: _candidates(k, rid, r, db, lits, others) for k in keys}
        base = {k: c[0] for k, c in cands.items()}
        calls = [base] + [{**base, k: v} for k, c in cands.items() for v in c[1:]]
        calls += [{k: rng.choice(c) for k, c in cands.items()} for _ in range(COMBOS)]
        out += [{k: v for k, v in a.items() if v is not ABSENT} for a in calls]
    return out


def _table(rule, db, now, calls):
    """Verdicts on the probes as C2 `check` gives them: a rule that raises denies."""
    return tuple(check({"tool_rules": [rule]}, db, rule["tool"], a, now)[0].ok for a in calls)


def _status(t, tables):
    """matched: one compiled rule has the hand rule's truth table. by_parts: no single rule does, but the
    compiled rules the hand rule implies (each allows wherever it allows), ANDed, have its truth table."""
    if t in tables:
        return "matched"
    implied = [x for x in tables if all(a or not b for a, b in zip(x, t))]
    return "by_parts" if tuple(map(all, zip(*implied))) == t else "unmatched"


def match_report(compiled: dict, hand: dict, domain=None) -> dict:
    """How many hand rules a compiled RuleSet reproduces, judged by truth tables on DB-built probes.

    A hand rule counts as matched when one compiled rule on the same tool has its truth table, or when
    the compiled rules on that tool that it implies, ANDed, have it (a policy condition the compiled set
    splits into several rules). A hand rule that does not validate is unmatched.
    rate = (matched + by_parts) / hand rules; strict_rate counts single-rule matches only.
    A hand rule whose verdict is the same on every probe is not discriminable: any compiled rule with the
    same constant verdict matches it. The report counts those, so a high rate can be checked against them."""
    domain = domain or get_domain(hand["domain"])
    db, now = _db(domain), domain.now
    params = {t["function"]["name"]: set(t["function"]["parameters"].get("properties", {})) for t in domain.tools}
    rows = []
    for tool in sorted({r["tool"] for r in hand["tool_rules"]}):
        h = [r for r in hand["tool_rules"] if r["tool"] == tool]
        c = [r for r in compiled["tool_rules"] if r["tool"] == tool]
        calls = probes(db, now, params.get(tool, set()), [r["allow_if"] for r in h + c])
        tables = list(dict.fromkeys(_table(r, db, now, calls) for r in c))
        for r in h:
            try:
                validate({"domain": hand["domain"], "tool_rules": [r], "forbidden_goals": []})
            except RuleError as e:
                rows.append({"id": r["id"], "status": "invalid", "discriminable": False, "error": str(e)})
                continue
            t = _table(r, db, now, calls)
            rows.append({"id": r["id"], "status": _status(t, tables), "discriminable": len(set(t)) > 1})
    n = len(rows)
    count = {s: sum(x["status"] == s for x in rows) for s in ("matched", "by_parts", "unmatched", "invalid")}
    hits = [x for x in rows if x["status"] in ("matched", "by_parts")]
    return {"rate": len(hits) / n if n else 1.0, "strict_rate": count["matched"] / n if n else 1.0,
            "hand_rules": n, **count, "discriminable": sum(x["discriminable"] for x in rows),
            "matched_discriminable": sum(x["discriminable"] for x in hits), "rules": rows}


def match_rate(compiled: dict, hand: dict, domain=None) -> float:
    """C3: share of hand rules that a compiled rule reproduces (see `match_report`)."""
    return match_report(compiled, hand, domain)["rate"]
