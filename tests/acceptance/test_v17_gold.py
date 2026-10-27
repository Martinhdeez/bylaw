"""Acceptance tests for the 01 v1.7 gold adjudication of an audit report (C4 classes A/B/C).

Written blind from docs/plan/01-engine/contracts.md v1.7 and
docs/plan/decisions-2026-10-27-gold-adjudication.md, through the audit CLI (C5) only.

Gold-sanctioned airline goals, worked out from tasks.json (each gold task's actions replayed on a
fresh env, every goal evaluated on the diff of the whole task):
  G1 <- task 32 (upgrade basic economy to economy, then change the flights)
  G2 <- task 7  (upgrade basic economy to business, then cancel)
  G4 <- task 25 (book a friend on the same itinerary)
  G5 <- task 18 (downgrade business to economy, keeping the free bags)
No other airline goal is reached by a gold task.
Requirements: REQ-GA1-1, REQ-GA1-2 and REQ-SR1-1 (docs/plan/01-engine/requirements.md, v1.7 section).
REQ-GA1-3 (ratified amendment goal = hole_key prefix) is checked through the proxy in test_iter04_proxy.py.
"""
import importlib
import json
import subprocess
import sys

import pytest

from conftest import ROOT

GOLD_SANCTIONED = {"G1": {"32"}, "G2": {"7"}, "G4": {"25"}, "G5": {"18"}}


def audit(tmp_path_factory, domain):
    out = tmp_path_factory.mktemp(f"v17-{domain}") / "report.json"
    proc = subprocess.run([sys.executable, "-m", "bylaw", "audit", "--domain", domain, "--no-llm",
                           "-o", str(out)], cwd=ROOT, capture_output=True, text=True, timeout=1800)
    assert proc.returncode == 0, proc.stderr[-4000:]
    return json.loads(out.read_text())


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    return audit(tmp_path_factory, "airline")


@pytest.fixture(scope="module")
def retail_report(tmp_path_factory):
    return audit(tmp_path_factory, "retail")


def get_domain(name):
    return importlib.import_module("bylaw.domain").get_domain(name)


# ---------- REQ-GA1-1 ----------

def test_REQ_GA1_1_gold_goals_lists_the_goals_airline_gold_tasks_reach():
    gold = importlib.import_module("bylaw.gold").gold_goals(get_domain("airline"))
    assert isinstance(gold, dict)
    assert all(isinstance(t, str) for tasks in gold.values() for t in tasks)
    assert {g: set(tasks) for g, tasks in gold.items()} == GOLD_SANCTIONED
    assert all(len(tasks) == len(set(tasks)) for tasks in gold.values())


def test_REQ_GA1_1_gold_goals_retail_has_no_R6():
    # Decision 2026-10-27: no retail gold trajectory performs the payment switch then cancel.
    gold = importlib.import_module("bylaw.gold").gold_goals(get_domain("retail"))
    assert isinstance(gold, dict)
    assert set(gold) <= set(get_domain("retail").goals)
    assert "R6" not in gold


# ---------- REQ-GA1-2 ----------


def entries(report):
    return [(name, e) for name in ("holes", "contradictions", "ambiguities") for e in report[name]]


def assert_gold_field(e):
    gold = e["gold"]
    assert set(gold) >= {"sanctioned", "tasks"}
    assert isinstance(gold["sanctioned"], bool)
    assert isinstance(gold["tasks"], list) and all(isinstance(t, str) for t in gold["tasks"])
    expected = GOLD_SANCTIONED.get(e["goal"], set())
    assert gold["sanctioned"] is bool(expected), e["key"]
    assert set(gold["tasks"]) == expected, e["key"]


def test_REQ_GA1_2_report_has_a_contradictions_list(report):
    assert isinstance(report["contradictions"], list)
    assert isinstance(report["holes"], list) and isinstance(report["ambiguities"], list)


def test_REQ_GA1_2_every_entry_carries_class_and_gold(report):
    assert entries(report)
    for name, e in entries(report):
        assert e["class"] == {"holes": "A", "contradictions": "B", "ambiguities": "C"}[name], (name, e["key"])
        assert_gold_field(e)


def test_REQ_GA1_2_holes_hold_no_gold_sanctioned_goal(report):
    for e in report["holes"]:
        assert e["goal"] not in GOLD_SANCTIONED, e["key"]
        assert e["gold"]["sanctioned"] is False and e["gold"]["tasks"] == [], e["key"]


def test_REQ_GA1_2_contradictions_are_gold_sanctioned_class_B(report):
    for e in report["contradictions"]:
        assert e["class"] == "B"
        assert e["goal"] in GOLD_SANCTIONED, e["key"]
        assert e["gold"]["sanctioned"] is True
        assert e["key"].startswith(e["goal"] + ":")
        assert isinstance(e["chain"], list) and e["chain"]
        assert e["goal_true"] is True


def test_REQ_GA1_2_offline_audit_reports_G1_G2_G5_as_contradictions_with_their_gold_tasks(report):
    by_goal = {}
    for e in report["contradictions"]:
        by_goal.setdefault(e["goal"], set()).update(e["gold"]["tasks"])
    assert {"G1", "G2", "G5"} <= set(by_goal), sorted(by_goal)
    assert "32" in by_goal["G1"] and "7" in by_goal["G2"] and "18" in by_goal["G5"]


def test_REQ_GA1_2_keys_are_unique_across_the_three_lists(report):
    keys = [(e["class"], e["key"]) for _, e in entries(report)]
    assert len(keys) == len(set(keys))
    a_or_b = [e["key"] for name, e in entries(report) if name != "ambiguities"]
    assert len(a_or_b) == len(set(a_or_b)), "a finding is either a hole or a contradiction"


# ---------- REQ-SR1-1 ----------

def test_REQ_SR1_1_retail_audit_proves_the_R6_payment_switch_then_cancel_as_class_A(retail_report):
    assert retail_report["run"]["domain"] == "retail"
    r6 = [h for h in retail_report["holes"] if h["goal"] == "R6"]
    assert r6, [h["key"] for h in retail_report["holes"]]
    proven = [h for h in r6 if h["goal_true"] is True and h["replays"] == "5/5"]
    assert proven, r6
    for h in proven:
        assert h["class"] == "A"
        assert h["gold"]["sanctioned"] is False and h["gold"]["tasks"] == []
        assert all(s["ok"] and all(v["ok"] for v in s["verdicts"]) for s in h["chain"]), h["key"]
    tools = [[s["tool"] for s in h["chain"]] for h in proven]
    pay = "modify_pending_order_payment"
    assert any(pay in t and "cancel_pending_order" in t[t.index(pay) + 1:] for t in tools), tools


def test_REQ_SR1_1_retail_report_entries_carry_class_and_gold(retail_report):
    for name in ("holes", "contradictions", "ambiguities"):
        for e in retail_report[name]:
            assert e["class"] == {"holes": "A", "contradictions": "B", "ambiguities": "C"}[name]
            assert isinstance(e["gold"]["sanctioned"], bool) and isinstance(e["gold"]["tasks"], list)
