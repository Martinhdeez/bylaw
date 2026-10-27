"""Shared helpers for the acceptance tests (contracts C1-C3, docs/plan/01-engine; C9-C11, 03 and 04)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULESETS = ROOT / "bylaw" / "rulesets"


def load_ruleset(domain: str) -> dict:
    return json.loads((RULESETS / f"{domain}.json").read_text())


def tool_names(domain) -> set[str]:
    """Names from the OpenAI function schemas in Domain.tools."""
    return {t.get("function", t)["name"] for t in domain.tools}


def assert_c2_shape(rs: dict) -> None:
    """The C2 JSON shape, field by field, independent of bylaw.rules.validate."""
    assert isinstance(rs, dict)
    assert isinstance(rs["domain"], str) and rs["domain"]
    assert isinstance(rs["tool_rules"], list) and rs["tool_rules"]
    for r in rs["tool_rules"]:
        for key in ("id", "tool", "allow_if", "policy_ref"):
            assert isinstance(r[key], str) and r[key], (key, r)
    assert isinstance(rs["forbidden_goals"], list)
    for g in rs["forbidden_goals"]:
        for key in ("id", "name", "policy_ref"):
            assert isinstance(g[key], str) and g[key], (key, g)
    ids = [r["id"] for r in rs["tool_rules"]]
    assert len(ids) == len(set(ids)), "rule ids must be unique"


# ---------- iterations 03/04: the G1 basic-economy cabin hop (τ² airline DB) ----------
# T1QOBS (harper_lopez_1489) is basic_economy, one way JFK-MIA on HAT060 2024-05-26, 4 passengers.
# Step 0 upgrades the cabin with the same flights (the hand RuleSet allows a cabin-only change);
# step 1 then moves the now-economy reservation to HAT060 2024-05-18 (allowed: no longer basic).
# From session start a basic economy reservation's flights changed (G1), yet no single step is a G1
# step on the snapshot before it.
HOP_RES = "T1QOBS"
HOP_PAY = "credit_card_9875103"
HOP_OLD = [{"flight_number": "HAT060", "date": "2024-05-26"}]
HOP_NEW = [{"flight_number": "HAT060", "date": "2024-05-18"}]
HOP_CHAIN = [
    {"tool": "update_reservation_flights",
     "args": {"reservation_id": HOP_RES, "cabin": "economy", "flights": HOP_OLD, "payment_id": HOP_PAY}},
    {"tool": "update_reservation_flights",
     "args": {"reservation_id": HOP_RES, "cabin": "economy", "flights": HOP_NEW, "payment_id": HOP_PAY}},
]
HOP_KEY = "G1:" + HOP_RES
NO_AMEND_KEY = "G1:34XLFT"

AMEND_RULE = {
    "id": "A1-basic-cabin-locked", "tool": "update_reservation_flights",
    "allow_if": "res['cabin'] != 'basic_economy' or args['cabin'] == 'basic_economy'",
    "policy_ref": "Basic economy flights cannot be modified.", "note": "",
}
AMENDMENT = {
    "id": "A1", "hole_id": "H1",
    "policy_text": "A basic economy reservation cannot change cabin; its flights stay as booked.",
    "rule_patch": [AMEND_RULE],
    "rationale": "The cabin upgrade is the first step of every basic economy flight change.",
}


def report_fixture() -> dict:
    """A minimal C4 report (v1.2 key and diff) for airline: H1 carries a C7 amendment, H2 does not."""
    hole = {"id": "H1", "key": HOP_KEY, "class": "A", "goal": "G1",
            "title": "Basic economy flights changed through a cabin hop", "money_delta": 116.0,
            "chain": [dict(s, ok=True, verdicts=[]) for s in HOP_CHAIN],
            "diff": {"reservations": {HOP_RES: {"before": {"cabin": "basic_economy", "flights": HOP_OLD},
                                                "after": {"cabin": "economy", "flights": HOP_NEW}}}},
            "goal_true": True, "replays": "5/5",
            "amendment": AMENDMENT, "closes": True,
            "backtest": {"tasks": 43, "blocked": 0, "baseline_blocked": 0, "blocked_tasks": []}}
    bare = {"id": "H2", "key": NO_AMEND_KEY, "class": "A", "goal": "G1", "title": "Second G1 hole",
            "money_delta": 0.0, "chain": [], "diff": {}, "goal_true": True, "replays": "5/5"}
    return {"run": {"commit": "test", "domain": "airline", "model": "none", "mode": "bfs",
                    "started": "2026-10-27T00:00:00", "budget": 10, "goals_commit": "test"},
            "holes": [hole, bare], "ambiguities": [],
            "stats": {"chains_tried": 1, "tool_calls": 2, "llm_calls": 0, "tokens": 0, "seconds": 0.1}}


def write_ratified(dir_: Path, domain: str, *rules_, goal: str = "G6") -> None:
    """A C10 store holding one ratified amendment per given C2 tool_rule, each on a hole of `goal`.

    01 v1.7: the proxy monitor enforces the goals of ratified amendments, so `goal` is monitored.
    G6 (compensation_ineligible) is reached by no airline gold task and by no test chain here.
    """
    dir_.mkdir(parents=True, exist_ok=True)
    amendments = [{"id": f"A{i + 1}", "hole_key": f"{goal}:X{i}", "policy_text": "t.", "rule_patch": [r],
                   "rationale": "", "ratified_at": "2026-10-27T00:00:00+00:00"} for i, r in enumerate(rules_)]
    (dir_ / f"{domain}.json").write_text(json.dumps({"domain": domain, "amendments": amendments}))
