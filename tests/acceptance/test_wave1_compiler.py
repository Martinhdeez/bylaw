"""Acceptance tests for CP1: policy compiler and match rate (C3).

Written blind from docs/plan/01-engine/requirements.md and contracts.md.
compile_policy and the compile CLI call Muse, so those tests are @pytest.mark.live.
"""
import copy
import importlib
import json
import re
import subprocess
import sys

import pytest

from conftest import ROOT, assert_c2_shape, load_ruleset, tool_names


@pytest.fixture(scope="module")
def compiler():
    return importlib.import_module("bylaw.compiler")


@pytest.fixture(scope="module")
def rules():
    return importlib.import_module("bylaw.rules")


@pytest.fixture(scope="module")
def hand():
    return load_ruleset("airline")


# ---------- REQ-CP1-1 ----------

@pytest.mark.live
def test_REQ_CP1_1_compile_policy_returns_a_valid_ruleset(compiler, rules):
    domain = importlib.import_module("bylaw.domain").get_domain("airline")
    compiled = compiler.compile_policy(domain)
    assert_c2_shape(compiled)
    rules.validate(compiled)
    assert compiled["domain"] == "airline"
    assert {r["tool"] for r in compiled["tool_rules"]} <= tool_names(domain)
    json.dumps(compiled)


# ---------- REQ-CP1-2 ----------

def test_REQ_CP1_2_hand_against_itself_is_one(compiler, hand):
    rate = compiler.match_rate(copy.deepcopy(hand), copy.deepcopy(hand))
    assert isinstance(rate, float)
    assert rate == 1.0


def test_REQ_CP1_2_retail_hand_against_itself_is_one(compiler):
    retail = load_ruleset("retail")
    assert compiler.match_rate(copy.deepcopy(retail), copy.deepcopy(retail)) == 1.0


def test_REQ_CP1_2_equivalent_rewrites_still_match(compiler, hand):
    # Same tool, same truth table, different text and ids, reversed order -> still 1.0.
    compiled = copy.deepcopy(hand)
    for i, r in enumerate(compiled["tool_rules"]):
        r["id"] = f"C-{i}"
        r["allow_if"] = f"not not ({r['allow_if']})"
    compiled["tool_rules"].reverse()
    assert compiler.match_rate(compiled, hand) == 1.0


def test_REQ_CP1_2_no_compiled_rules_is_zero(compiler, hand):
    compiled = copy.deepcopy(hand)
    compiled["tool_rules"] = []
    rate = compiler.match_rate(compiled, hand)
    assert isinstance(rate, float)
    assert rate == 0.0


def test_REQ_CP1_2_same_condition_on_another_tool_does_not_match(compiler, hand):
    compiled = copy.deepcopy(hand)
    for r in compiled["tool_rules"]:
        r["tool"] = "no_such_tool"
    assert compiler.match_rate(compiled, hand) == 0.0


def _rs(*rules_):
    return {"domain": "airline",
            "tool_rules": [{"id": rid, "tool": tool, "allow_if": expr, "policy_ref": "p", "note": ""}
                           for rid, tool, expr in rules_],
            "forbidden_goals": []}


def test_REQ_CP1_2_share_of_hand_rules_matched(compiler):
    # Constant conditions have the same truth table on any probe set.
    hand = _rs(("H1", "cancel_reservation", "True"),
               ("H2", "book_reservation", "len(args) >= 0"))
    compiled = _rs(("C1", "cancel_reservation", "1 == 1"),       # equivalent to H1
                   ("C2", "book_reservation", "len(args) < 0"),  # opposite of H2
                   ("C3", "send_certificate", "True"))           # extra rule, no hand counterpart
    rate = compiler.match_rate(compiled, hand)
    assert isinstance(rate, float)
    assert rate == 0.5
    assert 0.0 <= rate <= 1.0


def test_REQ_CP1_2_negated_condition_does_not_match(compiler):
    hand = _rs(("H1", "cancel_reservation", "True"))
    assert compiler.match_rate(_rs(("C1", "cancel_reservation", "False")), hand) == 0.0


# ---------- REQ-CP1-3 ----------

@pytest.mark.live
def test_REQ_CP1_3_compile_cli_writes_ruleset_and_prints_match_rate(rules, tmp_path):
    out = tmp_path / "X.json"
    proc = subprocess.run(
        [sys.executable, "-m", "bylaw", "compile", "--domain", "airline", "-o", str(out)],
        cwd=ROOT, capture_output=True, text=True, timeout=900,
    )
    assert proc.returncode == 0, proc.stderr
    compiled = json.loads(out.read_text())
    assert_c2_shape(compiled)
    rules.validate(compiled)
    assert compiled["domain"] == "airline"
    m = re.search(r"match[^\n]*?(\d+(?:\.\d+)?)\s*(%?)", proc.stdout, re.IGNORECASE)
    assert m, f"no match rate in stdout: {proc.stdout!r}"
    value = float(m.group(1)) / (100 if m.group(2) else 1)
    assert 0.0 <= value <= 1.0
