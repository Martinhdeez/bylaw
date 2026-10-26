"""Shared helpers for the wave-1 acceptance tests (contracts C1-C3, docs/plan/01-engine)."""
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
