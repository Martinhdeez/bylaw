"""Ratified store (contract C10, ratified/<domain>.json): ratified amendments and the RuleSet they produce."""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from bylaw.amend import apply

ROOT = Path(__file__).resolve().parents[1]
HAND_RULESETS = Path(__file__).parent / "rulesets"
_LOCK = threading.Lock()  # ponytail: one process; several server processes on one store would need a file lock


def _path(domain: str) -> Path:
    """C10 v1.1: env BYLAW_RATIFIED_DIR, read on every call; default ratified/ at the repo root."""
    return ROOT / (os.environ.get("BYLAW_RATIFIED_DIR") or "ratified") / f"{domain}.json"


def load(domain: str) -> dict:
    p = _path(domain)
    return json.loads(p.read_text()) if p.exists() else {"domain": domain, "amendments": []}


def effective_ruleset(domain: str, store: dict | None = None) -> dict:
    """The hand RuleSet with every ratified rule_patch applied in order."""
    rs = json.loads((HAND_RULESETS / f"{domain}.json").read_text())
    for a in (store or load(domain))["amendments"]:
        rs = apply(rs, a)
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
        patch = [{**r, "id": f"{hole['key']}/{r['id']}"} for r in am["rule_patch"]]  # 03 v1.3: no cross-hole clash
        entry = {"id": am["id"], "hole_key": hole["key"], "policy_text": am["policy_text"], "rule_patch": patch,
                 "rationale": am.get("rationale", ""),
                 "ratified_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        apply(effective_ruleset(domain, store), entry)
        store["amendments"].append(entry)
        p = _path(domain)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(store, indent=2) + "\n")
        return entry
