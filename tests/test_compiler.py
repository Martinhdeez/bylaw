import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from bylaw import __main__ as bylaw_main
from bylaw import compiler
from bylaw.compiler import compile_policy, match_report, match_rate
from bylaw.rules import RULESET_SCHEMA, RuleError, validate

POLICY_CANCEL = "Otherwise, flight can be cancelled if any of the following is true:"
HAND = {
    "domain": "airline",
    "tool_rules": [
        {"id": "R-cancel-1", "tool": "cancel_reservation",
         "allow_if": "hours_between(res['created_at'], now) <= 24 or res['cabin'] == 'business' "
                     "or res['insurance'] == 'yes'",
         "policy_ref": POLICY_CANCEL, "note": ""},
        {"id": "R-flights-1", "tool": "update_reservation_flights",
         "allow_if": "res['cabin'] != 'basic_economy'",
         "policy_ref": "Basic economy flights cannot be modified.", "note": ""},
        {"id": "R-cert-1", "tool": "send_certificate",
         "allow_if": "user['membership'] in ['silver', 'gold'] and args['amount'] <= 100",
         "policy_ref": "Only compensate if the user is a silver/gold member or has travel insurance or flies business.",
         "note": ""},
    ],
    "forbidden_goals": [
        {"id": "G1", "name": "basic_economy_flights_changed",
         "policy_ref": "Basic economy flights cannot be modified.",
         "description": "A basic-economy reservation ends with different flights."},
    ],
}

NOW = "2024-05-15T15:00:00"
DB = {
    "users": {
        "u_reg": {"user_id": "u_reg", "membership": "regular", "payment_methods": {}},
        "u_gold": {"user_id": "u_gold", "membership": "gold", "payment_methods": {}},
    },
    "reservations": {
        f"R{i}": {"reservation_id": f"R{i}", "user_id": user, "cabin": cabin, "insurance": ins, "created_at": created,
                  "status": None, "flights": [], "passengers": []}
        for i, (user, cabin, ins, created) in enumerate([
            ("u_reg", "basic_economy", "no", "2024-05-01T10:00:00"),
            ("u_reg", "basic_economy", "no", "2024-05-15T01:00:00"),   # 14h before now
            ("u_reg", "basic_economy", "no", "2024-05-14T00:00:00"),   # 39h before now
            ("u_gold", "economy", "yes", "2024-05-02T10:00:00"),
            ("u_gold", "business", "no", "2024-05-03T10:00:00"),
            ("u_reg", "economy", "no", "2024-05-04T10:00:00"),
        ])
    },
    "flights": {},
}


def _tool(name, *params):
    return {"type": "function", "function": {"name": name, "description": "",
                                             "parameters": {"type": "object", "properties": {p: {} for p in params}}}}


def make_domain(db=DB):
    return SimpleNamespace(
        name="airline", now=NOW, fresh_env=lambda: None, snapshot=lambda env: db,
        policy_text="Basic economy flights cannot be modified.\n" + POLICY_CANCEL,
        tools=[_tool("cancel_reservation", "reservation_id"),
               _tool("update_reservation_flights", "reservation_id", "cabin", "flights", "passengers", "payment_id"),
               _tool("send_certificate", "user_id", "amount")],
    )


DOMAIN = make_domain()


def rate(compiled, hand=HAND, domain=DOMAIN):
    return match_rate(compiled, hand, domain)


def with_rule(rule_id, allow_if, rs=HAND):
    rs = copy.deepcopy(rs)
    next(r for r in rs["tool_rules"] if r["id"] == rule_id)["allow_if"] = allow_if
    return rs


def plus_rule(rs, tool, allow_if, rule_id="R-extra"):
    return {**rs, "tool_rules": rs["tool_rules"] + [{"id": rule_id, "tool": tool, "allow_if": allow_if,
                                                      "policy_ref": "x", "note": ""}]}


# --- match_rate on probes built from the tool schemas and the domain DB ----------------------------

def test_match_rate_is_one_for_the_same_ruleset_on_both_sides():
    assert rate(HAND) == 1.0


def test_match_rate_counts_equivalent_conditions_written_differently():
    rs = with_rule("R-flights-1", "not (res.get('cabin') == 'basic_economy')")
    rs["tool_rules"][0]["id"] = "C-anything"   # ids do not matter, only tool + truth table
    assert rate(rs) == 1.0


def test_match_rate_drops_a_rule_whose_truth_table_differs_on_db_probes():
    # 48h instead of 24h: only the reservation booked 39h ago tells them apart.
    rs = with_rule("R-cancel-1", "hours_between(res['created_at'], now) <= 48 or res['cabin'] == 'business' "
                                 "or res['insurance'] == 'yes'")
    assert rate(rs) == pytest.approx(2 / 3)


def test_match_rate_probes_recent_bookings_even_in_a_large_db():
    # A big DB is sampled; the only record that separates 24h from 48h must still be probed.
    old = DB["reservations"]["R0"]
    big = {**DB, "reservations": {f"X{i:04}": {**old, "reservation_id": f"X{i:04}"} for i in range(1000)}}
    big["reservations"]["X0001"] = {**old, "reservation_id": "X0001", "created_at": "2024-05-14T00:00:00"}
    big["reservations"]["X0016"] = {**old, "reservation_id": "X0016", "cabin": "business"}  # in the stride sample
    rs = with_rule("R-cancel-1", "hours_between(res['created_at'], now) <= 48 or res['cabin'] == 'business' "
                                 "or res['insurance'] == 'yes'")
    assert rate(rs, domain=make_domain(big)) == pytest.approx(2 / 3)


def test_match_rate_probes_argument_values_on_the_tool_schema():
    # Differs from the hand rule only for amount == 100, which no DB record holds.
    rs = with_rule("R-cert-1", "user['membership'] in ['silver', 'gold'] and args['amount'] < 100")
    assert rate(rs) == pytest.approx(2 / 3)


def test_match_rate_probes_structured_args_built_from_db_records():
    # Only a call whose passenger list differs from the reservation's tells these apart.
    hand = plus_rule(HAND, "update_reservation_flights", "len(args['passengers']) == len(res['passengers'])")
    compiled = plus_rule(HAND, "update_reservation_flights", "len(args['passengers']) >= 0")
    m = match_report(compiled, hand, DOMAIN)
    assert m["discriminable"] == 4 and m["rate"] == pytest.approx(3 / 4)


def test_match_rate_probes_calls_that_change_several_arguments_at_once():
    # False only when cabin and passenger count change in the same call.
    hand = plus_rule(HAND, "update_reservation_flights",
                     "not (args['cabin'] != res['cabin'] and len(args['passengers']) != len(res['passengers']))")
    m = match_report(plus_rule(HAND, "update_reservation_flights", "res is not None"), hand, DOMAIN)
    assert m["discriminable"] == 4 and m["rate"] == pytest.approx(3 / 4)


def test_match_rate_probes_conversation_facts_the_rules_read():
    hand = plus_rule(HAND, "cancel_reservation", "args.get('reason') in ['health', 'weather']")
    assert rate(plus_rule(HAND, "cancel_reservation", "args.get('reason') == 'health'"), hand) == pytest.approx(3 / 4)
    assert rate(hand, hand) == 1.0


def test_a_hand_rule_split_into_several_compiled_rules_matches_by_parts():
    # One hand rule with two conditions, compiled as two rules that the checker ANDs.
    hand = with_rule("R-flights-1", "res['cabin'] != 'basic_economy' and args['cabin'] == res['cabin']")
    split = {**hand, "tool_rules": [r for r in hand["tool_rules"] if r["id"] != "R-flights-1"]}
    split = plus_rule(split, "update_reservation_flights", "res['cabin'] != 'basic_economy'", "C-a")
    split = plus_rule(split, "update_reservation_flights", "args['cabin'] == res['cabin']", "C-b")
    split = plus_rule(split, "update_reservation_flights", "len(args['passengers']) <= 5", "C-unrelated")
    m = match_report(split, hand, DOMAIN)
    assert m["rate"] == 1.0 and m["by_parts"] == 1 and m["strict_rate"] == pytest.approx(2 / 3)
    # Parts that are too weak together do not match.
    weak = {**split, "tool_rules": [r for r in split["tool_rules"] if r["id"] != "C-b"]}
    assert rate(weak, hand) == pytest.approx(2 / 3)


def test_by_parts_ignores_compiled_rules_the_hand_rule_does_not_imply():
    # C-b is stricter than the hand rule (denies where it allows); it must not make up the difference.
    hand = with_rule("R-flights-1", "res['cabin'] != 'basic_economy'")
    rs = with_rule("R-flights-1", "True", hand)
    rs = plus_rule(rs, "update_reservation_flights", "res['cabin'] == 'business'", "C-b")
    assert rate(rs, hand) == pytest.approx(2 / 3)


def test_match_rate_probes_other_itineraries_for_the_flights_argument():
    # Only a business reservation given another booking's two-segment itinerary tells these apart.
    db = copy.deepcopy(DB)
    for i, (rid, r) in enumerate(sorted(db["reservations"].items())):
        r["flights"] = [{"flight_number": f"HAT{i}{k}", "date": "2024-05-20"} for k in range(2 if i == 0 else 1)]
    hand = plus_rule(HAND, "update_reservation_flights", "res['cabin'] != 'business' or len(args['flights']) == 1")
    m = match_report(plus_rule(HAND, "update_reservation_flights", "res is not None"), hand, make_domain(db))
    assert m["rate"] == pytest.approx(3 / 4)


def test_probes_name_the_record_collection_the_snapshot_has():
    # A retail-shaped snapshot: rules read `res` through args["order_id"], not reservation_id.
    db = {"users": DB["users"], "products": {"P1": {"product_id": "P1", "variants": {}}},
          "orders": {f"#W{i}": {"order_id": f"#W{i}", "user_id": "u_reg", "status": s, "items": [], "payment_history": []}
                     for i, s in enumerate(["pending", "delivered", "pending", "cancelled"])}}
    hand = {"domain": "retail", "forbidden_goals": [],
            "tool_rules": [{"id": "R-cancel-1", "tool": "cancel_pending_order", "allow_if": "res['status'] == 'pending'",
                            "policy_ref": "x", "note": ""}]}
    domain = SimpleNamespace(name="retail", now=NOW, fresh_env=lambda: None, snapshot=lambda env: db,
                             tools=[_tool("cancel_pending_order", "order_id", "reason")])
    m = match_report(hand, hand, domain)
    assert m["rate"] == 1.0 and m["discriminable"] == 1
    assert match_rate(with_rule("R-cancel-1", "res['status'] != 'cancelled'", hand), hand, domain) == 0.0


def test_retail_probes_vary_items_new_items_and_payment_methods():
    variants = {"V1": {"item_id": "V1", "available": True}, "V2": {"item_id": "V2", "available": True},
                "V3": {"item_id": "V3", "available": False}}
    db = {"users": {"u1": {"user_id": "u1", "payment_methods": {"gift_card_1": {"source": "gift_card"}}}},
          "products": {"P1": {"product_id": "P1", "variants": variants},
                       "P2": {"product_id": "P2", "variants": {"W1": {"item_id": "W1", "available": True}}}},
          "orders": {f"#W{i}": {"order_id": f"#W{i}", "user_id": "u1", "status": "pending",
                                "items": [{"item_id": "V1", "product_id": "P1"}],
                                "payment_history": [{"payment_method_id": "gift_card_1"}]} for i in range(3)}}
    rule = lambda rid, expr: {"id": rid, "tool": "modify_pending_order_items", "allow_if": expr,  # noqa: E731
                              "policy_ref": "x", "note": ""}
    hand = {"domain": "retail", "forbidden_goals": [], "tool_rules": [
        rule("A", "len(args['item_ids']) > 0"),
        rule("B", "all(b != a for a, b in zip(args['item_ids'], args['new_item_ids']))"),
        rule("C", "args['payment_method_id'] in user['payment_methods']"),
    ]}
    domain = SimpleNamespace(name="retail", now=NOW, fresh_env=lambda: None, snapshot=lambda env: db,
                             tools=[_tool("modify_pending_order_items", "order_id", "item_ids", "new_item_ids",
                                          "payment_method_id")])
    m = match_report(hand, hand, domain)
    assert m["rate"] == 1.0 and m["discriminable"] == 3
    # Differs from C only for a payment method outside the user's profile.
    assert match_rate({**hand, "tool_rules": hand["tool_rules"][:2] + [rule("C2", "user is not None")]},
                      hand, domain) == pytest.approx(2 / 3)


def test_match_rate_needs_the_same_tool():
    rs = copy.deepcopy(HAND)
    rs["tool_rules"][1]["tool"] = "update_reservation_baggages"
    assert rate(rs) == pytest.approx(2 / 3)


def test_match_rate_of_an_empty_or_always_true_compiled_ruleset_is_zero():
    assert rate({**HAND, "tool_rules": []}) == 0.0
    all_true = {**HAND, "tool_rules": [{**r, "allow_if": "True"} for r in HAND["tool_rules"]]}
    assert rate(all_true) == 0.0


def test_a_constant_hand_rule_matches_only_the_same_constant_and_is_reported_as_not_discriminable():
    hand = plus_rule(HAND, "cancel_reservation", "True")
    m = match_report(HAND, hand, DOMAIN)
    assert m["rate"] == pytest.approx(3 / 4) and m["discriminable"] == 3 and m["matched_discriminable"] == 3
    m = match_report(plus_rule(HAND, "cancel_reservation", "1 == 1"), hand, DOMAIN)
    assert m["rate"] == 1.0 and m["matched"] == 4 and m["matched_discriminable"] == 3


def test_a_hand_rule_that_does_not_parse_counts_as_unmatched_without_crashing():
    hand = plus_rule(HAND, "cancel_reservation", "res[")
    m = match_report(HAND, hand, DOMAIN)
    assert m["invalid"] == 1 and m["rate"] == pytest.approx(3 / 4)


def test_a_compiled_rule_that_raises_denies_like_the_checker():
    # Raises exactly where the hand rule is False; deny-on-error makes the truth tables equal.
    hand = with_rule("R-cancel-1", "res['insurance'] == 'yes'")
    assert rate(with_rule("R-cancel-1", "res['insurance'] == 'yes' or res['no_such_field']", hand), hand) == 1.0


def test_user_is_resolved_through_the_reservation_when_args_name_no_user():
    hand = with_rule("R-cancel-1", "user['membership'] == 'gold'")   # cancel_reservation takes no user_id
    m = match_report(hand, hand, DOMAIN)
    assert m["rate"] == 1.0 and m["discriminable"] == 3


# --- compile_policy with Muse scripted (contract C3 v1.1 `llm=`) -----------------------------------

class Muse:
    """Scripted stand-in for bylaw.llm.structured."""

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def __call__(self, messages, schema, name, effort=None, **opts):
        self.calls.append({"messages": copy.deepcopy(messages), "schema": schema, "effort": effort, **opts})
        return copy.deepcopy(self.replies.pop(0))


def test_compile_policy_returns_the_valid_ruleset_muse_produced():
    muse = Muse(HAND)
    out = compile_policy(DOMAIN, llm=muse)
    validate(out)
    assert out == HAND
    (call,) = muse.calls
    assert call["effort"] == "high" and call["schema"] == RULESET_SCHEMA
    prompt = json.dumps(call["messages"])
    assert "Basic economy flights cannot be modified." in prompt
    assert all(t in prompt for t in ("cancel_reservation", "update_reservation_flights", "send_certificate"))
    assert "hours_between" in prompt and "policy_ref" in prompt
    assert 'args[\\"reason\\"]' in prompt and 'args[\\"complaint\\"]' in prompt   # v1.1 conversation facts


def test_compile_policy_stamps_the_domain_name():
    assert compile_policy(DOMAIN, llm=Muse({**HAND, "domain": "retail"}))["domain"] == "airline"


def test_compile_policy_sends_a_rejected_ruleset_back_once_with_the_reason():
    muse = Muse(with_rule("R-flights-1", "__import__('os')"), HAND)
    assert compile_policy(DOMAIN, llm=muse) == HAND
    assert len(muse.calls) == 2 and "__import__" in muse.calls[1]["messages"][-1]["content"]


@pytest.mark.parametrize("bad", [
    with_rule("R-flights-1", "res.__class__"),
    with_rule("R-flights-1", "len(**args) > 0"),
    with_rule("R-flights-1", "open('/etc/passwd')"),
    {**HAND, "tool_rules": [{**HAND["tool_rules"][0], "tool": "delete_everything"}]},
    {**HAND, "tool_rules": [{**HAND["tool_rules"][0], "policy_ref": ""}]},
])
def test_compile_policy_raises_when_muse_cannot_produce_a_valid_ruleset(bad):
    with pytest.raises(RuleError):
        compile_policy(DOMAIN, llm=Muse(bad, bad))


# --- CLI: python -m bylaw compile --domain D -o PATH ---------------------------------------------

@pytest.fixture
def cli(monkeypatch, tmp_path):
    monkeypatch.setattr(bylaw_main, "get_domain", lambda name: DOMAIN)
    monkeypatch.setattr(bylaw_main, "HAND_RULESETS", tmp_path / "rulesets")
    monkeypatch.setattr(compiler, "structured", Muse(with_rule("R-cancel-1", "res['cabin'] == 'business'")))
    return tmp_path


def test_cli_compile_writes_a_valid_ruleset_and_prints_the_match_rate(cli, capsys):
    (cli / "rulesets").mkdir()
    (cli / "rulesets" / "airline.json").write_text(json.dumps(HAND))
    out = cli / "compiled.json"
    assert bylaw_main.main(["compile", "--domain", "airline", "-o", str(out)]) == 0
    validate(json.loads(out.read_text()))
    printed = capsys.readouterr().out
    assert "match rate: 0.67 (2/3 hand rules: 2 by one compiled rule, 0 by several; strict 0.67; " \
           "3/3 discriminable on the probes, 2 of them matched; 0 invalid)" in printed
    assert "unmatched R-cancel-1" in printed


def test_cli_compile_without_a_hand_ruleset_prints_the_rule_count(cli, capsys):
    out = cli / "compiled.json"
    assert bylaw_main.main(["compile", "--domain", "airline", "-o", str(out)]) == 0
    validate(json.loads(out.read_text()))
    printed = capsys.readouterr().out
    assert "3 tool rules, 1 forbidden goals" in printed and "no hand RuleSet" in printed


# --- the real airline domain (local tau2-bench checkout; live test needs MODEL_API_KEY) -----------

ROOT = Path(__file__).parents[1]
needs_tau2 = pytest.mark.skipif(not (ROOT / ".context/tau2-bench/data").exists(), reason="no .context/tau2-bench checkout")


@needs_tau2
def test_every_airline_hand_rule_is_discriminable_and_matches_itself():
    hand = json.loads((ROOT / "bylaw/rulesets/airline.json").read_text())
    m = match_report(hand, hand)
    assert m["rate"] == 1.0 and m["discriminable"] == m["hand_rules"] == len(hand["tool_rules"])


@needs_tau2
def test_every_retail_hand_rule_is_discriminable_and_matches_itself():
    hand = json.loads((ROOT / "bylaw/rulesets/retail.json").read_text())
    m = match_report(hand, hand)
    assert m["rate"] == 1.0 and m["discriminable"] == m["hand_rules"] == len(hand["tool_rules"])


@needs_tau2
def test_an_always_true_ruleset_matches_no_airline_hand_rule():
    hand = json.loads((ROOT / "bylaw/rulesets/airline.json").read_text())
    tools = sorted({r["tool"] for r in hand["tool_rules"]})
    all_true = {**hand, "tool_rules": [{"id": f"T-{t}", "tool": t, "allow_if": "True", "policy_ref": "x", "note": ""}
                                       for t in tools]}
    assert match_rate(all_true, hand) == 0.0


@needs_tau2
@pytest.mark.live
def test_live_compile_airline_policy():
    from bylaw.domain import get_domain
    d = get_domain("airline")
    rs = compile_policy(d)
    validate(rs)
    assert rs["domain"] == "airline" and rs["tool_rules"] and rs["forbidden_goals"]
    assert {r["tool"] for r in rs["tool_rules"]} <= {t["function"]["name"] for t in d.tools}
    assert 0.0 <= match_rate(rs, json.loads((ROOT / "bylaw/rulesets/airline.json").read_text()), d) <= 1.0
