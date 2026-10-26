"""Acceptance tests for RT1: the retail domain plug-in (C1) and its hand RuleSet (C2).

Written blind from docs/plan/01-engine/requirements.md and contracts.md.
Fixture facts come from the τ² retail DB (.context/tau2-bench/data/tau2/domains/retail/db.json).
"""
import copy
import importlib
import json
import re

import pytest

from conftest import assert_c2_shape, load_ruleset, tool_names

# τ² retail DB: order #W5918442 (user sofia_rossi_8776) is "pending", so it can be cancelled.
PENDING_ORDER = "#W5918442"


@pytest.fixture(scope="module")
def retail():
    return importlib.import_module("bylaw.domain").get_domain("retail")


@pytest.fixture(scope="module")
def rules():
    return importlib.import_module("bylaw.rules")


# ---------- REQ-RT1-1 ----------

def test_REQ_RT1_1_get_domain_retail_has_the_C1_surface(retail):
    assert retail.name == "retail"
    assert isinstance(retail.policy_text, str) and retail.policy_text.strip()
    names = tool_names(retail)
    assert {"cancel_pending_order", "get_order_details", "return_delivered_order_items"} <= names
    assert retail.write_tools <= names
    assert "cancel_pending_order" in retail.write_tools
    assert "get_order_details" not in retail.write_tools
    assert isinstance(retail.now, str) and retail.now
    assert isinstance(retail.goals, dict) and retail.goals


def test_REQ_RT1_1_fresh_envs_are_independent_copies(retail):
    env1, env2 = retail.fresh_env(), retail.fresh_env()
    before = retail.snapshot(env2)
    assert retail.snapshot(env1) == before

    result = retail.call(env1, "cancel_pending_order", order_id=PENDING_ORDER, reason="no longer needed")
    assert result.ok is True, result.error
    assert result.tool == "cancel_pending_order"

    after1 = retail.snapshot(env1)
    assert after1 != before, "the write must change its own env"
    assert retail.snapshot(env2) == before, "a write in one env must not change another"
    assert retail.snapshot(retail.fresh_env()) == before, "a new env must start from the untouched DB"
    json.dumps(after1)


def test_REQ_RT1_1_snapshot_is_a_copy_not_a_live_view(retail):
    env = retail.fresh_env()
    before = retail.snapshot(env)
    frozen = copy.deepcopy(before)
    assert retail.call(env, "cancel_pending_order", order_id=PENDING_ORDER, reason="ordered by mistake").ok
    assert before == frozen


# ---------- REQ-RT1-2 ----------

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("*", "").replace("`", "")).strip().lower()


def test_REQ_RT1_2_goals_have_ids_policy_refs_and_class(retail):
    policy = _norm(retail.policy_text)
    for key, g in retail.goals.items():
        assert g.id == key
        assert re.fullmatch(r"R\d+", g.id), g.id
        assert isinstance(g.name, str) and g.name
        assert g.cls in {"A", "C"}, (g.id, g.cls)
        assert callable(g.check)
        assert isinstance(g.policy_ref, str) and g.policy_ref.strip()
        # policy_ref quotes the policy: every quoted fragment occurs in the policy text.
        for frag in re.split(r"\n|\.\.\.|…", g.policy_ref):
            frag = _norm(frag).strip(" \"'“”-")
            if frag:
                assert frag in policy, (g.id, frag)


def test_REQ_RT1_2_every_goal_is_false_on_the_untouched_db(retail):
    snap = retail.snapshot(retail.fresh_env())
    for g in retail.goals.values():
        assert g.check(copy.deepcopy(snap), copy.deepcopy(snap), []) is False, g.id


# ---------- REQ-RT1-3 ----------

def test_REQ_RT1_3_retail_ruleset_is_valid(rules, retail):
    rs = load_ruleset("retail")
    assert_c2_shape(rs)
    assert rs["domain"] == "retail"
    rules.validate(rs)
    assert {r["tool"] for r in rs["tool_rules"]} <= tool_names(retail)


def test_REQ_RT1_3_validate_rejects_a_ruleset_that_breaks_C2(rules):
    rs = load_ruleset("retail")
    broken = {k: v for k, v in rs.items() if k != "tool_rules"}
    with pytest.raises(rules.RuleError):
        rules.validate(broken)
