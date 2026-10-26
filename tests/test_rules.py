"""Unit tests for the C2 rule checker (REQ-EN1-1..3)."""
import json
import time
from pathlib import Path

import pytest

from bylaw.rules import RuleError, allowed, check, validate

NOW = "2024-05-15T15:00:00"
SNAP = {
    "users": {"ann_1": {"membership": "gold", "payment_methods": {"cc_1": {"source": "credit_card"}}}},
    "reservations": {"RES1": {"user_id": "ann_1", "cabin": "economy", "created_at": "2024-05-15T03:00:00"}},
    "flights": {},
}


def rs(*rules):
    return {"domain": "t", "forbidden_goals": [],
            "tool_rules": [{"id": i, "tool": t, "allow_if": e, "policy_ref": f"ref {i}"} for i, t, e in rules]}


def test_one_verdict_per_rule_of_the_tool_and_all_must_pass():
    r = rs(("A", "cancel_reservation", "True"), ("B", "cancel_reservation", "args['n'] < 2"), ("X", "other", "False"))
    ok = check(r, SNAP, "cancel_reservation", {"n": 1}, NOW)
    bad = check(r, SNAP, "cancel_reservation", {"n": 5}, NOW)
    assert [(v.rule_id, v.ok, v.policy_ref) for v in ok] == [("A", True, "ref A"), ("B", True, "ref B")]
    assert allowed(ok) and not allowed(bad)
    assert [v.rule_id for v in bad if not v.ok] == ["B"]


def test_tool_without_rules_is_allowed():
    assert allowed(check(rs(("A", "x", "False")), SNAP, "y", {}, NOW))


def test_res_and_user_resolve_from_args():
    by_res = rs(("A", "t", "res['cabin'] == 'economy' and user['membership'] == 'gold'"))
    by_user = rs(("B", "t", "user is not None and res is None"))
    assert allowed(check(by_res, SNAP, "t", {"reservation_id": "RES1"}, NOW))
    assert allowed(check(by_user, SNAP, "t", {"user_id": "ann_1"}, NOW))


def test_hours_between_is_the_distance_in_hours():
    r = rs(("A", "t", "hours_between(res['created_at'], now) == 12 and hours_between(now, res['created_at']) == 12"))
    assert allowed(check(r, SNAP, "t", {"reservation_id": "RES1"}, NOW))


def test_runtime_error_is_a_failing_verdict_not_a_crash():
    [v] = check(rs(("A", "t", "res['cabin'] == 'x'")), SNAP, "t", {"reservation_id": "NOPE"}, NOW)
    assert not v.ok and v.error


ACCEPTED = [
    "len([f for f in res['flights'] if f['date'] > now]) == 0",
    "all(a['d'] == b['o'] for a, b in zip(args['l'], args['l'][1:]))",
    "{'a': 1}.get('a', 0) in [1, 2]",
    "max(1, 2) - min(3, 4) * 2 >= abs(-1) or sum([1]) // 1 % 2 == 1",
    "{k: v for k, v in [('a', 1)]} == {'a': 1}",
    "1 if True else 2",
]
REJECTED = [
    "__import__('os').system('true')",
    "args.__class__",
    "args.keys()",
    "open('/etc/passwd')",
    "(lambda: 1)()",
    "eval('1')",
    "getattr(args, 'get')",
    "os.system('true')",
    "(x := 1)",
    "2 ** 1000",
    "f'{args}'",
    "_x",
    "max(*args)",
    "1;2",
    "",
]


@pytest.mark.parametrize("expr", ACCEPTED)
def test_whitelist_is_accepted(expr):
    validate(rs(("A", "t", expr)))


@pytest.mark.parametrize("expr", REJECTED)
def test_forbidden_syntax_is_rejected(expr):
    with pytest.raises(RuleError):
        validate(rs(("A", "t", expr)))


def test_forbidden_rule_never_runs_in_check(tmp_path):
    p = tmp_path / "pwned"
    [v] = check(rs(("A", "t", f"open({str(p)!r}, 'w')")), SNAP, "t", {}, NOW)
    assert not v.ok and not p.exists()


def test_validate_rejects_a_malformed_ruleset():
    with pytest.raises(RuleError):
        validate({"domain": "t", "tool_rules": [{"id": "A", "tool": "t"}], "forbidden_goals": []})


# ---- airline hand RuleSet on the real tau2 DB (REQ-EN1-3) ----

@pytest.fixture(scope="module")
def airline():
    from bylaw.domain import get_domain
    d = get_domain("airline")
    return d, d.snapshot(d.fresh_env())


@pytest.fixture(scope="module")
def hand():
    return json.loads((Path(__file__).resolve().parents[1] / "bylaw/rulesets/airline.json").read_text())


def failing(hand, snap, tool, args, now):
    return [v.rule_id for v in check(hand, snap, tool, args, now) if not v.ok]


# 34XLFT: basic economy, no insurance, created 2024-05-12T02:00:41, flight not flown.
@pytest.mark.parametrize("now, rejected", [
    ("2024-05-12T03:00:41", False), ("2024-05-13T02:00:41", False),
    ("2024-05-13T02:01:41", True), ("2024-05-15T15:00:00", True),
])
def test_basic_economy_uninsured_cancel_needs_the_24h_window(airline, hand, now, rejected):
    _, snap = airline
    args = {"reservation_id": "34XLFT", "reason": "change of plan"}
    assert failing(hand, snap, "cancel_reservation", args, now) == (["R-cancel-ground"] if rejected else [])


def test_cancel_needs_a_reason_and_an_active_reservation(airline, hand):
    _, snap = airline
    assert "R-cancel-reason" in failing(hand, snap, "cancel_reservation", {"reservation_id": "34XLFT"}, "2024-05-12T03:00:00")
    assert "R-cancel-active" in failing(hand, snap, "cancel_reservation", {"reservation_id": "NOPE", "reason": "other"}, NOW)


def test_hand_ruleset_names_only_domain_tools_and_goals(airline, hand):
    d, _ = airline
    validate(hand)
    assert {r["tool"] for r in hand["tool_rules"]} <= {t["function"]["name"] for t in d.tools}
    assert {g["id"] for g in hand["forbidden_goals"]} == set(d.goals) == {f"G{i}" for i in range(1, 8)}


def test_basic_economy_may_change_cabin_but_never_flights(airline, hand):
    """Policy: "Basic economy flights cannot be modified." / "all reservations, including basic economy,
    can change cabin without changing the flights." """
    d, snap = airline
    r = snap["reservations"]["T1QOBS"]  # basic economy, one way JFK-MIA, HAT060 on 2024-05-26
    pid = next(k for k, v in snap["users"][r["user_id"]]["payment_methods"].items() if v["source"] == "credit_card")
    same = [{"flight_number": "HAT060", "date": "2024-05-26"}]
    other = [{"flight_number": "HAT060", "date": "2024-05-27"}]

    def upd(cabin, flights):
        args = {"reservation_id": "T1QOBS", "cabin": cabin, "flights": flights, "payment_id": pid}
        return failing(hand, snap, "update_reservation_flights", args, d.now)

    assert upd("economy", same) == []
    assert upd("economy", other) == ["R-flights-not-basic"]
    assert upd("basic_economy", other) == ["R-flights-not-basic"]


def test_other_cabins_may_change_cabin_and_flights_in_one_call(airline, hand):
    """Gold tasks 15 and 16 (v1.4 baseline): business M05KNL goes to economy on new flights in one call."""
    d, snap = airline
    assert snap["reservations"]["M05KNL"]["cabin"] == "business"
    args = {"reservation_id": "M05KNL", "cabin": "economy", "payment_id": "gift_card_8887175",
            "flights": [{"flight_number": "HAT110", "date": "2024-05-24"}, {"flight_number": "HAT172", "date": "2024-05-24"}]}
    assert failing(hand, snap, "update_reservation_flights", args, d.now) == []


def test_bags_cannot_be_removed_or_exceed_the_free_allowance(airline, hand):
    d, snap = airline
    rid, r = next((k, v) for k, v in sorted(snap["reservations"].items())
                  if v["cabin"] == "business" and v["status"] != "cancelled" and v["total_baggages"] > 0)
    u = snap["users"][r["user_id"]]
    cap = {"regular": 2, "silver": 3, "gold": 4}[u["membership"]] * len(r["passengers"])  # policy: business allowance
    pid = next(iter(u["payment_methods"]))

    def bags(total, nonfree):
        args = {"reservation_id": rid, "total_baggages": total, "nonfree_baggages": nonfree, "payment_id": pid}
        return failing(hand, snap, "update_reservation_baggages", args, d.now)

    assert bags(r["nonfree_baggages"] + cap, r["nonfree_baggages"]) == []
    assert bags(r["nonfree_baggages"] + cap + 1, r["nonfree_baggages"]) == ["R-bags-free-allowance"]
    assert "R-bags-no-remove" in bags(r["total_baggages"] - 1, r["nonfree_baggages"])


def test_snapshot_is_json_with_collections_keyed_by_id(airline):
    d, snap = airline
    assert json.loads(json.dumps(snap))["reservations"]["34XLFT"]["user_id"] == "mason_kim_9621"
    assert d.now == "2024-05-15T15:00:00" and "Airline Agent Policy" in d.policy_text
    assert "cancel_reservation" in d.write_tools and "get_user_details" not in d.write_tools


def test_targets_are_real_reservations_matching_the_goal(airline):
    d, snap = airline
    g2 = d.targets("G2")
    assert {"user_id": "mason_kim_9621", "reservation_id": "34XLFT"} in g2
    for t in g2:  # G2: basic economy, uninsured, booked more than 24h before now
        r = snap["reservations"][t["reservation_id"]]
        assert r["user_id"] == t["user_id"] and r["cabin"] == "basic_economy" and r["insurance"] == "no"
        assert r["created_at"] < "2024-05-14T15:00:00"


def test_unknown_or_missing_domain_fails_clearly():
    from bylaw.domain import get_domain
    with pytest.raises(ValueError):
        get_domain("telecom")
    try:
        import bylaw.env.tau2_retail  # noqa: F401
    except ModuleNotFoundError:
        with pytest.raises(RuntimeError, match="retail"):
            get_domain("retail")


def test_domain_call_strips_conversation_facts_and_keeps_them_in_the_result(airline):
    d, _ = airline
    env = d.fresh_env()
    step = d.call(env, "cancel_reservation", reservation_id="34XLFT", reason="change of plan")
    assert step.ok and step.error is None and step.args["reason"] == "change of plan"
    assert d.snapshot(env)["reservations"]["34XLFT"]["status"] == "cancelled"
    assert d.snapshot(d.fresh_env())["reservations"]["34XLFT"]["status"] != "cancelled"


# ---- C2 v1.5 evaluation budget: 10^6 iterations plus elements built, per rule evaluation ----

# 200 reservations: a triple-nested comprehension is 8 * 10^6 iterations, over the budget, yet an unguarded
# evaluation still finishes in seconds, so removing the guard makes these tests fail instead of hang.
BIG = {"users": {}, "flights": {}, "reservations": {f"R{i}": {} for i in range(200)}}
ROWS = "db['reservations']"
SHARED2 = f"[[y for b in {ROWS}] for y in [[0 for c in {ROWS}]]][0]"  # 200 refs to one 200-row
SHARED3 = f"[[y for a in {ROWS}] for y in [{SHARED2}]][0]"  # 200 refs to that
NESTED = "len([1 for a in db['reservations'] for b in db['reservations'] for c in db['reservations']]) >= 0"
OVER_BOUND = {
    "str_repeat": "len('a' * 1000000000) > 0",
    "str_repeat_huge": "len('a' * 100000000000) > 0",
    "str_format": "len('%0999999999d' % 1) > 0",
    "list_repeat": "len([0] * 2000000) > 0",
    "concat": "len([0] * 600000 + [0] * 600000) > 0",
    "sum_concat": "len(sum([[0] * 1000] * 2000, [])) > 0",
    "per_value_sum": "len([[0] * 10000 for a in db['reservations']]) > 0",  # 200 values of 10^4 each
    "nested_comprehension": NESTED,
    "nested_generator": "sum(1 for a in db['reservations'] for b in db['reservations'] for c in db['reservations']) >= 0",
    # review round 2 (agent-abb217651162f51b6/.scratch/review-en2/amplify.py)
    "deep_eq_repeat": "([[[[[0]*100]*100]*100]*100]*100) == ([[[[[0]*100]*100]*100]*100]*100)",
    "int_squaring": "len([1 for x0 in [99999999999] " + " ".join(f"for x{i} in [x{i-1}*x{i-1}]" for i in range(1, 27)) + "]) == 1",
    # repetition hidden from validate, refused at runtime
    "runtime_repeat": "len([s * 1000000000 for s in ['ab']]) > 0",
    # sharing built by comprehensions, then a deep compare: 200^3 leaf compares, ~600 iterations charged
    "shared_deep_eq": f"({SHARED3}) == ({SHARED3})",
    "shared_deep_max": f"max([{SHARED3}, {SHARED3}]) == 0",
    "sum_over_cap": "sum([999999999999999, 999999999999999]) > 0",
}


@pytest.mark.parametrize("expr", OVER_BOUND.values(), ids=OVER_BOUND.keys())
def test_rule_over_the_evaluation_budget_gives_a_failing_verdict(expr):
    t = time.perf_counter()
    [v] = check(rs(("A", "t", expr)), BIG, "t", {}, NOW)
    assert not v.ok and v.error
    assert time.perf_counter() - t < 5.0


def test_rules_within_the_budget_still_evaluate():
    within = ("len([0, 0] + [1]) + sum([1, 2]) + len([1 for a in db['reservations']]) + 7 % 4 + 12 * 2 - 10 // 3"
              " + max([[1, 2], [1, 3]])[1] + (999999999999999 - 1) * 1 // 999999999999999 == 233"
              " and [{'a': [1]}] == [{'a': [1]}] and 3 in [1, 2, 3] and 'R5' in db['reservations']")
    [v] = check(rs(("A", "t", within)), BIG, "t", {}, NOW)
    assert v.ok and v.error is None


def test_the_budget_is_per_evaluation_not_per_process():
    r = rs(("A", "t", "len([1 for a in db['reservations'] for b in db['reservations']]) == 40000"))
    assert all(allowed(check(r, BIG, "t", {}, NOW)) for _ in range(30))  # 30 * 4 * 10^4 > 10^6 in total


def test_concurrent_checks_over_the_budget_all_fail_cleanly():
    from concurrent.futures import ThreadPoolExecutor
    r = rs(("A", "t", NESTED), ("B", "t", "True"))
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda _: check(r, BIG, "t", {}, NOW), range(8)))
    assert all([(v.rule_id, v.ok) for v in vs] == [("A", False), ("B", True)] for vs in results)


@pytest.mark.parametrize("expr", ["b'a' * 1000000000", "len(b'%0999999999d' % 1) > 0", "b'x' in [b'x']"])
def test_bytes_constants_are_rejected(expr):
    with pytest.raises(RuleError):
        validate(rs(("A", "t", expr)))


@pytest.mark.parametrize("expr", ["[0] * 3 == [0, 0, 0]", "'ab' * 2 == 'abab'", "2 * (1, 2) == (1, 2, 1, 2)",
                                  "[x for x in [1]] * 2 == [1, 1]", "1000000000000001 > 0", "1e16 > 0"])
def test_repetition_and_oversized_literals_are_rejected_by_validate(expr):
    with pytest.raises(RuleError):
        validate(rs(("A", "t", expr)))


@pytest.mark.parametrize("expr", ["x * 2 > 0", "x + x > 0", "x - -x > 0", "x * x // 1 > 0", "-x * 10 < 0", "x * 10.0 > 0"])
def test_numbers_over_ten_to_the_fifteen_fail(expr):
    [v] = check(rs(("A", "t", expr.replace("x", "999999999999999"))), BIG, "t", {}, NOW)
    assert not v.ok and v.error
