"""Executor (EX1): run a chain of tool calls on a fresh DB copy, with per-step rule verdicts (C2) and a C4 diff."""
import copy
import json
from dataclasses import asdict

from bylaw.rules import allowed, check


def canon(record) -> str:
    return json.dumps(record, sort_keys=True, default=str)


def diff(before: dict, after: dict) -> dict:
    """C4 v1.2: {collection: {record_id: {"before": dict|None, "after": dict|None}}}, changed records only."""
    out = {}
    for coll in sorted(before.keys() | after.keys()):
        b, a = before.get(coll) or {}, after.get(coll) or {}
        changed = {rid: {"before": b.get(rid), "after": a.get(rid)}
                   for rid in sorted(b.keys() | a.keys()) if canon(b.get(rid)) != canon(a.get(rid))}
        if changed:
            out[coll] = changed
    return out


def run(domain, chain: list[dict], ruleset: dict | None = None) -> dict:
    """Execute `chain` ([{"tool", "args"}]) on a fresh env.

    With a ruleset, every step is checked on the DB as it is just before the call; the run stops at the
    first step the rules forbid (it is not executed) or the tool rejects. Steps come back in the C4 chain
    shape, plus the StepResults, both snapshots and the diff.
    """
    env = domain.fresh_env()
    before = domain.snapshot(env)
    snap, steps, results = before, [], []
    for s in chain:
        verdicts = check(ruleset, snap, s["tool"], s["args"], domain.now) if ruleset else []
        step = {"tool": s["tool"], "args": copy.deepcopy(s["args"]), "ok": False, "verdicts": [asdict(v) for v in verdicts]}
        steps.append(step)
        if not allowed(verdicts):
            break
        res = domain.call(env, s["tool"], **copy.deepcopy(s["args"]))
        results.append(res)
        snap = domain.snapshot(env)
        step["ok"] = res.ok
        if not res.ok:
            break
    return {"steps": steps, "results": results, "before": before, "after": snap, "diff": diff(before, snap)}


def replay(domain, chain: list[dict]) -> dict:
    """C4 v1.2: re-run a report chain on a fresh env, no rules -> {"steps": [StepResult dict], "diff": C4 diff}."""
    env = domain.fresh_env()
    before = domain.snapshot(env)
    results = [domain.call(env, s["tool"], **copy.deepcopy(s["args"])) for s in chain]
    return {"steps": [asdict(r) for r in results], "diff": diff(before, domain.snapshot(env))}
