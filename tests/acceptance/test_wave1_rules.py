"""Acceptance tests for EN1: the rule checker (C2) and the airline hand RuleSet.

Written blind from docs/plan/01-engine/requirements.md and contracts.md.
Fixture facts come from the τ² airline DB (.context/tau2-bench/data/tau2/domains/airline/db.json).
"""
import importlib

import pytest

from conftest import assert_c2_shape, load_ruleset, tool_names


@pytest.fixture(scope="module")
def rules():
    return importlib.import_module("bylaw.rules")


@pytest.fixture(scope="module")
def airline():
    return importlib.import_module("bylaw.domain").get_domain("airline")


@pytest.fixture(scope="module")
def snap(airline):
    return airline.snapshot(airline.fresh_env())


def ruleset(*rules_, domain="airline"):
    return {
        "domain": domain,
        "tool_rules": [
            {"id": rid, "tool": tool, "allow_if": expr, "policy_ref": f"ref {rid}", "note": ""}
            for rid, tool, expr in rules_
        ],
        "forbidden_goals": [],
    }


NOW = "2024-05-15T15:00:00"

# Three rules on one tool, one on another. Expressions use args, db, now and hours_between.
RS = ruleset(
    ("R-a", "send_certificate", "args.get('amount', 0) <= 100"),
    ("R-b", "send_certificate", "args.get('user_id') in db['users']"),
    ("R-c", "send_certificate", "abs(hours_between(now, '2024-05-15T12:00:00')) == 3"),
    ("R-x", "cancel_reservation", "False"),
)


# ---------- REQ-EN1-1 ----------

def test_REQ_EN1_1_one_verdict_per_rule_of_the_tool(rules, snap):
    verdicts = rules.check(RS, snap, "send_certificate", {"user_id": "mason_kim_9621", "amount": 50}, NOW)
    assert sorted(v.rule_id for v in verdicts) == ["R-a", "R-b", "R-c"]
    assert all(v.ok is True for v in verdicts)
    assert {v.rule_id: v.policy_ref for v in verdicts} == {"R-a": "ref R-a", "R-b": "ref R-b", "R-c": "ref R-c"}
    assert rules.allowed(verdicts) is True


def test_REQ_EN1_1_one_failing_rule_blocks_the_call(rules, snap):
    verdicts = rules.check(RS, snap, "send_certificate", {"user_id": "mason_kim_9621", "amount": 500}, NOW)
    assert len(verdicts) == 3
    by_id = {v.rule_id: v.ok for v in verdicts}
    assert by_id == {"R-a": False, "R-b": True, "R-c": True}
    assert rules.allowed(verdicts) is False


def test_REQ_EN1_1_db_is_read_from_the_snapshot(rules, snap):
    verdicts = rules.check(RS, snap, "send_certificate", {"user_id": "nobody_0000", "amount": 50}, NOW)
    assert {v.rule_id: v.ok for v in verdicts} == {"R-a": True, "R-b": False, "R-c": True}
    assert rules.allowed(verdicts) is False


def test_REQ_EN1_1_now_is_the_argument_given(rules, snap):
    verdicts = rules.check(RS, snap, "send_certificate", {"user_id": "mason_kim_9621", "amount": 50},
                           "2024-05-15T20:00:00")
    assert {v.rule_id: v.ok for v in verdicts}["R-c"] is False
    assert rules.allowed(verdicts) is False


def test_REQ_EN1_1_rules_of_other_tools_do_not_apply(rules, snap):
    verdicts = rules.check(RS, snap, "cancel_reservation", {"reservation_id": "34XLFT"}, NOW)
    assert [(v.rule_id, v.ok) for v in verdicts] == [("R-x", False)]
    assert rules.allowed(verdicts) is False


def test_REQ_EN1_1_tool_without_rules_is_allowed(rules, snap):
    verdicts = rules.check(RS, snap, "get_user_details", {"user_id": "mason_kim_9621"}, NOW)
    assert list(verdicts) == []
    assert rules.allowed(verdicts) is True


def test_REQ_EN1_1_res_and_user_resolve_from_args(rules, snap):
    # 34XLFT belongs to mason_kim_9621 (gold member) and is basic_economy in the τ² DB.
    rs = ruleset(
        ("R-res", "cancel_reservation", "res is not None and res['cabin'] == 'basic_economy'"),
        ("R-user", "cancel_reservation", "user is not None and user['membership'] == 'gold'"),
    )
    verdicts = rules.check(rs, snap, "cancel_reservation", {"reservation_id": "34XLFT"}, NOW)
    assert {v.rule_id: v.ok for v in verdicts} == {"R-res": True, "R-user": True}


# ---------- REQ-EN1-2 ----------

ALLOWED_EXPRS = [
    "args.get('x', 1) > 0 and not False",
    "len([f for f in res['flights'] if f['date'] > now]) == 0",
    "any(p['payment_id'] in db['users'] for p in res['payment_history'])",
    "{'a': 1}.get('a') in [1, 2]",
    "min(1, 2) <= max(3, 4) and abs(0) == sum([0]) or all([])",
    "user is not None and user.get('membership') == 'gold'",
    "hours_between(now, res['created_at']) <= 24",
    "args['k'][0] == 'v'",
]

FORBIDDEN_EXPRS = {
    "import": "__import__('os').system('true')",
    "dunder_attr": "args.__class__.__mro__",
    "dunder_subclasses": "().__class__.__bases__[0].__subclasses__()",
    "dunder_globals": "hours_between.__globals__",
    "open": "open('/etc/passwd').read()",
    "lambda": "(lambda: 1)()",
    "eval": "eval('1')",
    "exec": "exec('x = 1')",
    "getattr": "getattr(args, 'get')",
    "unknown_name": "os.system('true')",
    "non_whitelisted_method": "db.pop('users')",
    "walrus": "(x := 1)",
}


@pytest.mark.parametrize("expr", ALLOWED_EXPRS)
def test_REQ_EN1_2_whitelisted_expressions_validate(rules, expr):
    rules.validate(ruleset(("R-ok", "cancel_reservation", expr)))


@pytest.mark.parametrize("expr", FORBIDDEN_EXPRS.values(), ids=FORBIDDEN_EXPRS.keys())
def test_REQ_EN1_2_forbidden_expression_raises_RuleError(rules, expr):
    with pytest.raises(rules.RuleError):
        rules.validate(ruleset(("R-bad", "cancel_reservation", expr)))


def test_REQ_EN1_2_one_bad_rule_rejects_the_whole_ruleset(rules):
    rs = ruleset(("R-ok", "cancel_reservation", "True"),
                 ("R-bad", "send_certificate", "__import__('os')"))
    with pytest.raises(rules.RuleError):
        rules.validate(rs)


def _side_effect_exprs(path):
    p = repr(str(path))
    return {
        "open": f"open({p}, 'w').write('pwned')",
        "import": f"__import__('pathlib').Path({p}).touch()",
        "lambda": f"(lambda: open({p}, 'w'))()",
        "dunder": f"().__class__.__base__.__subclasses__() and open({p}, 'w')",
    }


@pytest.mark.parametrize("kind", ["open", "import", "lambda", "dunder"])
def test_REQ_EN1_2_rejected_expression_is_never_executed_by_validate(rules, tmp_path, kind):
    target = tmp_path / "pwned"
    expr = _side_effect_exprs(target)[kind]
    with pytest.raises(rules.RuleError):
        rules.validate(ruleset(("R-bad", "cancel_reservation", expr)))
    assert not target.exists()


@pytest.mark.parametrize("kind", ["open", "import", "lambda", "dunder"])
def test_REQ_EN1_2_rejected_expression_is_never_executed_by_check(rules, snap, tmp_path, kind):
    target = tmp_path / "pwned"
    rs = ruleset(("R-bad", "cancel_reservation", _side_effect_exprs(target)[kind]))
    try:
        verdicts = rules.check(rs, snap, "cancel_reservation", {"reservation_id": "34XLFT"}, NOW)
    except rules.RuleError:
        pass
    else:
        assert rules.allowed(verdicts) is False
    assert not target.exists()


# ---------- REQ-EN1-3 ----------
# τ² airline DB, reservation 34XLFT: user mason_kim_9621, cabin basic_economy, insurance "no",
# one flight HAT076 on 2024-05-19 (status "available"), created_at 2024-05-12T02:00:41.
RES_ID = "34XLFT"
CANCEL_ARGS = {"reservation_id": RES_ID, "user_id": "mason_kim_9621", "reason": "change of plan"}
CREATED = "2024-05-12T02:00:41"
NOW_25H = "2024-05-13T03:00:41"      # created_at + 25h
NOW_24H1M = "2024-05-13T02:01:41"    # created_at + 24h01m
NOW_23H = "2024-05-13T01:00:41"      # created_at + 23h
NOW_23H59M = "2024-05-13T01:59:41"   # created_at + 23h59m
NOW_1H = "2024-05-12T03:00:41"       # created_at + 1h


@pytest.fixture(scope="module")
def hand():
    return load_ruleset("airline")


def test_REQ_EN1_3_fixture_matches_the_tau2_db(snap):
    r = snap["reservations"][RES_ID]
    assert (r["cabin"], r["insurance"], r["created_at"], r["user_id"]) == \
        ("basic_economy", "no", CREATED, "mason_kim_9621")


def test_REQ_EN1_3_airline_hand_ruleset_is_valid(rules, hand, airline):
    assert_c2_shape(hand)
    assert hand["domain"] == "airline"
    rules.validate(hand)
    assert {r["tool"] for r in hand["tool_rules"]} <= tool_names(airline)
    assert any(r["tool"] == "cancel_reservation" for r in hand["tool_rules"])


@pytest.mark.parametrize("now", [NOW_25H, NOW_24H1M], ids=["25h", "24h01m"])
def test_REQ_EN1_3_cancel_basic_economy_uninsured_after_24h_is_rejected(rules, hand, snap, now):
    verdicts = rules.check(hand, snap, "cancel_reservation", CANCEL_ARGS, now)
    assert verdicts, "cancel_reservation must have at least one rule"
    assert rules.allowed(verdicts) is False
    failing = [v for v in verdicts if not v.ok]
    assert failing and all(v.policy_ref for v in failing)


def test_REQ_EN1_3_cancel_rejected_at_the_simulator_clock(rules, hand, snap, airline):
    # The simulator clock (domain.now) is days after created_at.
    assert airline.now > NOW_25H
    verdicts = rules.check(hand, snap, "cancel_reservation", CANCEL_ARGS, airline.now)
    assert rules.allowed(verdicts) is False


@pytest.mark.parametrize("now", [NOW_1H, NOW_23H, NOW_23H59M], ids=["1h", "23h", "23h59m"])
def test_REQ_EN1_3_cancel_within_24h_is_allowed(rules, hand, snap, now):
    verdicts = rules.check(hand, snap, "cancel_reservation", CANCEL_ARGS, now)
    assert verdicts, "cancel_reservation must have at least one rule"
    assert rules.allowed(verdicts) is True, [(v.rule_id, v.ok, v.error) for v in verdicts]
