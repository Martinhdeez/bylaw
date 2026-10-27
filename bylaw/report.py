"""Hole report (contract C4 v1.7): run the search, execute every chain, prove what fires a goal, adjudicate it
against the gold tasks (A hole, B contradiction, C ambiguity), write the JSON."""
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from bylaw.gold import gold_goals
from bylaw.executor import run
from bylaw.proposer import search
from bylaw.verifier import prove

ROOT = Path(__file__).resolve().parents[1]
_S, _I, _B, _N = {"type": "string"}, {"type": "integer", "minimum": 0}, {"type": "boolean"}, {"type": "number"}


def _obj(props: dict, **extra) -> dict:
    return {"type": "object", "required": list(props), "properties": props, **extra}


_CHANGE = _obj({"before": {"type": ["object", "null"]}, "after": {"type": ["object", "null"]}}, additionalProperties=False)
_STEP = _obj({"tool": _S, "args": {"type": "object"}, "ok": _B,
              "verdicts": {"type": "array", "items": _obj({"rule_id": _S, "ok": _B, "policy_ref": _S})}})
_ENTRY = _obj({"id": _S, "key": _S, "class": {"enum": ["A", "B", "C"]}, "goal": _S, "title": _S, "money_delta": _N,
               "chain": {"type": "array", "minItems": 1, "items": _STEP},
               "diff": {"type": "object", "additionalProperties": {"type": "object", "additionalProperties": _CHANGE}},
               "goal_true": _B, "replays": {"type": "string", "pattern": r"^\d+/\d+$"},
               "gold": _obj({"sanctioned": _B, "tasks": {"type": "array", "items": _S}})})
REPORT_SCHEMA = _obj({
    "run": _obj({"commit": _S, "domain": _S, "model": _S, "mode": {"enum": ["bfs", "muse"]}, "started": _S,
                 "budget": _I, "goals_commit": _S}),
    **{name: {"type": "array", "items": {**_ENTRY, "properties": {**_ENTRY["properties"], "class": {"const": cls}}}}
       for name, cls in (("holes", "A"), ("contradictions", "B"), ("ambiguities", "C"))},
    "stats": _obj({"chains_tried": _I, "tool_calls": _I, "llm_calls": _I, "tokens": _I, "seconds": {"type": "number", "minimum": 0}}),
})


def classify(domain, db: dict, goal_id: str, chain: list[dict]) -> str:
    """Class C when the goal is pre-registered C, or the chain cancels a reservation and then books again for the
    same user: cancel+rebook inside a permitted cancel ground is the permitted method (REQ-EX1-3).
    Otherwise Class B when a gold task reaches the goal (C4 v1.7), else Class A."""
    if domain.goals[goal_id].cls == "C":
        return "C"
    for i, s in enumerate(chain):
        res = db.get("reservations", {}).get(s["args"].get("reservation_id")) if s["tool"] == "cancel_reservation" else None
        if res and any(t["tool"] == "book_reservation" and t["args"].get("user_id") == res["user_id"] for t in chain[i + 1:]):
            return "C"
    return "B" if goal_id in gold_goals(domain) else "A"


def money_delta(diff: dict) -> float:
    """Net money the chain paid out to the customer (refunds minus charges) across the changed reservations
    (airline: a refund is a negative amount) and orders (retail: a refund is a positive "refund" line)."""
    out = 0.0
    for coll in ("reservations", "orders"):
        for change in diff.get(coll, {}).values():
            old = len((change["before"] or {}).get("payment_history", []))
            for p in (change["after"] or {}).get("payment_history", [])[old:]:
                out += p["amount"] if p.get("transaction_type") == "refund" else -p["amount"]
    return round(out, 2)


def _touched(snapshot: dict, diff: dict) -> dict:
    """The snapshot cut down to the changed records plus the users they name.
    ponytail: relies on goals looking only at the diff (bylaw/goals.py docstring); the verifier re-checks every hit on
    the full DB, so a goal that read untouched records would be missed here, never falsely reported."""
    out = {coll: {rid: recs[rid] for rid in diff.get(coll, {}) if rid in recs} for coll, recs in snapshot.items()}
    for uid in {r.get("user_id") for recs in out.values() for r in recs.values()} - {None}:
        out.setdefault("users", {})[uid] = snapshot["users"][uid]
    return out


def _target(chain: list[dict]) -> str:
    """The primary record of a chain (C4 v1.2 hole key): the first reservation or order it names, else its user."""
    for k in ("reservation_id", "order_id", "user_id"):
        if ids := [s["args"][k] for s in chain if k in s["args"]]:
            return ids[0]
    return ""


def _extends(chain: list[dict], key: str, entries: dict) -> bool:
    calls = [(s["tool"], s["args"]) for s in chain]
    return any(e["key"] == key and calls[:len(e["chain"])] == [(s["tool"], s["args"]) for s in e["chain"]] for e in entries.values())


GOALS_FILES = {"airline": "bylaw/goals.py", "retail": "bylaw/goals_retail.py"}


def _commit() -> str:
    """Short HEAD, with "-dirty" when tracked files differ from it; "" without git."""
    head = _git("rev-parse", "--short", "HEAD")
    return head + "-dirty" if head and _git("status", "--porcelain", "--untracked-files=no") else head


def _git(*args) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def audit(domain, ruleset: dict, budget: int = 2000, use_llm: bool = False, model: str = "") -> dict:
    t0 = time.monotonic()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db = domain.snapshot(domain.fresh_env())
    entries, chains_tried, tool_calls = {}, 0, 0
    for proposal in search(domain, ruleset, budget, use_llm):
        chain = [{"tool": t, "args": a} for t, a in proposal]
        r = run(domain, chain, ruleset)
        chains_tried += 1
        tool_calls += len(r["results"])
        if len(r["results"]) < len(chain) or not all(s["ok"] for s in r["steps"]) or not r["diff"]:
            continue
        before, after = _touched(r["before"], r["diff"]), _touched(r["after"], r["diff"])
        target = _target(chain)
        for gid, goal in domain.goals.items():
            key, cls = f"{gid}:{target}", classify(domain, db, gid, chain)
            # One entry per key across the three lists. A Class A hole takes the key from a B or C entry: it is never
            # shadowed. Otherwise the first, shortest chain wins (so the 24h cancel+rebook stays a Class C ambiguity,
            # REQ-EX1-3), and a chain that extends one already listed for the key adds nothing.
            if (key in entries and not (cls == "A" and entries[key]["class"] != "A")) or _extends(chain, key, entries) \
                    or not goal.check(before, after, r["results"]):
                continue
            replays = prove(domain, ruleset, gid, chain, r["diff"])
            if replays != "5/5":
                continue  # not reproducible: not a proven hole
            tasks = gold_goals(domain).get(gid, [])
            entries[key] = {"key": key, "class": cls, "goal": gid, "gold": {"sanctioned": bool(tasks), "tasks": tasks},
                            "title": f"{goal.name} on {target}", "money_delta": money_delta(r["diff"]),
                            "chain": r["steps"], "diff": r["diff"], "goal_true": True, "replays": replays}
    lists = {cls: [{"id": f"{prefix}{i}", **e} for i, e in enumerate((e for e in entries.values() if e["class"] == cls), 1)]
             for cls, prefix in (("A", "H"), ("B", "B"), ("C", "C"))}
    return {
        "run": {"commit": _commit(), "domain": domain.name, "model": model,
                "mode": "muse" if use_llm else "bfs", "started": started, "budget": budget,
                "goals_commit": _git("log", "-1", "--format=%h", "--", GOALS_FILES.get(domain.name, ""))},
        "holes": lists["A"], "contradictions": lists["B"], "ambiguities": lists["C"],
        "stats": {"chains_tried": chains_tried, "tool_calls": tool_calls, "llm_calls": 0, "tokens": 0,
                  "seconds": round(time.monotonic() - t0, 2)},
    }
