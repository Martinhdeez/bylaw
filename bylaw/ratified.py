"""Ratified store (contract C10, ratified/<domain>.json): ratified amendments and the RuleSet they produce."""
import copy
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAND_RULESETS = Path(__file__).parent / "rulesets"
_LOCK = threading.Lock()  # ponytail: one process; several server processes on one store would need a file lock


def _path(domain: str) -> Path:
    """C10 v1.1: env BYLAW_RATIFIED_DIR, read on every call; default ratified/ at the repo root."""
    return ROOT / (os.environ.get("BYLAW_RATIFIED_DIR") or "ratified") / f"{domain}.json"


def _apply(ruleset: dict, amendment: dict) -> dict:
    try:
        from bylaw.amend import apply
    except ImportError:  # AM1 not merged yet: the same C7 behaviour, append the patch, refuse colliding ids
        out = copy.deepcopy(ruleset)
        ids = {r["id"] for r in out["tool_rules"]}
        for rule in amendment["rule_patch"]:
            if rule["id"] in ids:
                raise ValueError(f"rule id {rule['id']!r} already exists in the ruleset")
            ids.add(rule["id"])
            out["tool_rules"].append(copy.deepcopy(rule))
        return out
    return apply(ruleset, amendment)


def load(domain: str) -> dict:
    p = _path(domain)
    return json.loads(p.read_text()) if p.exists() else {"domain": domain, "amendments": []}


def effective_ruleset(domain: str, store: dict | None = None) -> dict:
    """The hand RuleSet with every ratified rule_patch applied in order."""
    rs = json.loads((HAND_RULESETS / f"{domain}.json").read_text())
    for a in (store or load(domain))["amendments"]:
        rs = _apply(rs, a)
    return rs


def ratify(domain: str, hole: dict) -> dict:
    """Append the hole's amendment; a hole already ratified is returned as stored. Raises ValueError when the
    patch does not apply on top of what is already ratified (nothing is written then)."""
    with _LOCK:
        store = load(domain)
        for a in store["amendments"]:
            if a["hole_key"] == hole["key"]:
                return a
        am = hole["amendment"]
        entry = {"id": am["id"], "hole_key": hole["key"], "policy_text": am["policy_text"], "rule_patch": am["rule_patch"],
                 "rationale": am.get("rationale", ""),
                 "ratified_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        _apply(effective_ruleset(domain, store), entry)
        store["amendments"].append(entry)
        p = _path(domain)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(store, indent=2) + "\n")
        return entry
