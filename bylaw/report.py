"""Hole report (contract C4): run the search, execute every chain, prove what fires a goal, write the JSON."""
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from bylaw import llm as muse
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
_ENTRY = _obj({"id": _S, "key": _S, "class": {"enum": ["A", "C"]}, "goal": _S, "title": _S, "money_delta": _N,
               "chain": {"type": "array", "minItems": 1, "items": _STEP},
               "diff": {"type": "object", "additionalProperties": {"type": "object", "additionalProperties": _CHANGE}},
               "goal_true": _B, "replays": {"type": "string", "pattern": r"^\d+/\d+$"}})
REPORT_SCHEMA = _obj({
    "run": _obj({"commit": _S, "domain": _S, "model": _S, "mode": {"enum": ["bfs", "muse"]}, "started": _S,
                 "budget": _I, "goals_commit": _S}),
    "holes": {"type": "array", "items": {**_ENTRY, "properties": {**_ENTRY["properties"], "class": {"const": "A"}}}},
    "ambiguities": {"type": "array", "items": {**_ENTRY, "properties": {**_ENTRY["properties"], "class": {"const": "C"}}}},
    "stats": _obj({"chains_tried": _I, "tool_calls": _I, "llm_calls": _I, "tokens": _I, "seconds": {"type": "number", "minimum": 0}}),
})


def classify(domain, db: dict, goal_id: str, chain: list[dict]) -> str:
    """Class C when the goal is pre-registered C, or the chain cancels a reservation and then books again for the
    same user: cancel+rebook inside a permitted cancel ground is the permitted method (REQ-EX1-3)."""
    if domain.goals[goal_id].cls == "C":
        return "C"
    for i, s in enumerate(chain):
        res = db["reservations"].get(s["args"].get("reservation_id")) if s["tool"] == "cancel_reservation" else None
        if res and any(t["tool"] == "book_reservation" and t["args"].get("user_id") == res["user_id"] for t in chain[i + 1:]):
            return "C"
    return "A"


def money_delta(diff: dict) -> float:
    """Net money the chain paid out to the customer (refunds minus charges) across the changed reservations."""
    out = 0.0
    for change in diff.get("reservations", {}).values():
        old = len((change["before"] or {}).get("payment_history", []))
        out -= sum(p["amount"] for p in (change["after"] or {}).get("payment_history", [])[old:])
    return out


def _touched(snapshot: dict, diff: dict) -> dict:
    """The snapshot cut down to the changed records plus the users they name.
    ponytail: relies on goals looking only at the diff (bylaw/goals.py docstring); the verifier re-checks every hit on
    the full DB, so a goal that read untouched records would be missed here, never falsely reported."""
    out = {coll: {rid: recs[rid] for rid in diff.get(coll, {}) if rid in recs} for coll, recs in snapshot.items()}
    for uid in {r.get("user_id") for recs in out.values() for r in recs.values()} - {None}:
        out.setdefault("users", {})[uid] = snapshot["users"][uid]
    return out


def _git(*args) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def audit(domain, ruleset: dict, budget: int = 2000, use_llm: bool = False, model: str = "", llm=None) -> dict:
    """`llm` replaces bylaw.llm.structured (tests script Muse with it). llm_calls counts the requests the search
    made; tokens counts what the API billed for them (0 for a reply served from the disk cache)."""
    t0 = time.monotonic()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db = domain.snapshot(domain.fresh_env())
    entries, chains_tried, tool_calls = {}, 0, 0
    asked, billed_from = [], len(muse.CALLS)

    def counted(*a, **kw):
        asked.append(1)
        return (llm or muse.structured)(*a, **kw)

    for proposal in search(domain, ruleset, budget, use_llm, llm=counted):
        chain = [{"tool": t, "args": a} for t, a in proposal]
        r = run(domain, chain, ruleset)
        chains_tried += 1
        tool_calls += len(r["results"])
        if len(r["results"]) < len(chain) or not all(s["ok"] for s in r["steps"]) or not r["diff"]:
            continue
        before, after = _touched(r["before"], r["diff"]), _touched(r["after"], r["diff"])
        target = chain[0]["args"].get("reservation_id") or chain[0]["args"].get("user_id")
        for gid, goal in domain.goals.items():
            key, cls = f"{gid}:{target}", classify(domain, db, gid, chain)
            if key in entries or not goal.check(before, after, r["results"]):  # one entry per key, shortest chain first
                continue
            replays = prove(domain, ruleset, gid, chain, r["diff"])
            if replays != "5/5":
                continue  # not reproducible: not a proven hole
            entries[key] = {"key": key, "class": cls, "goal": gid,
                            "title": f"{goal.name} on {target}", "money_delta": money_delta(r["diff"]),
                            "chain": r["steps"], "diff": r["diff"], "goal_true": True, "replays": replays}
    holes = [{"id": f"H{i}", **e} for i, e in enumerate((e for e in entries.values() if e["class"] == "A"), 1)]
    ambiguities = [{"id": f"C{i}", **e} for i, e in enumerate((e for e in entries.values() if e["class"] == "C"), 1)]
    return {
        "run": {"commit": _git("rev-parse", "HEAD"), "domain": domain.name,
                "model": model or (muse.model() if use_llm else ""),
                "mode": "muse" if use_llm else "bfs", "started": started, "budget": budget,
                "goals_commit": _git("log", "-1", "--format=%H", "--", "bylaw/goals.py")},
        "holes": holes, "ambiguities": ambiguities,
        "stats": {"chains_tried": chains_tried, "tool_calls": tool_calls, "llm_calls": len(asked),
                  "tokens": sum(c["prompt_tokens"] + c["completion_tokens"] for c in muse.CALLS[billed_from:]),
                  "seconds": round(time.monotonic() - t0, 2)},
    }
