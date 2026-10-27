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
v1.7 names no requirement id; tests are titled by the contract clause.
"""
import json
import subprocess
import sys

import pytest

from conftest import ROOT

GOLD_SANCTIONED = {"G1": {"32"}, "G2": {"7"}, "G4": {"25"}, "G5": {"18"}}


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    out = tmp_path_factory.mktemp("v17") / "report.json"
    proc = subprocess.run([sys.executable, "-m", "bylaw", "audit", "--domain", "airline", "--no-llm",
                           "-o", str(out)], cwd=ROOT, capture_output=True, text=True, timeout=1800)
    assert proc.returncode == 0, proc.stderr[-4000:]
    return json.loads(out.read_text())


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


def test_C4_v17_report_has_a_contradictions_list(report):
    assert isinstance(report["contradictions"], list)
    assert isinstance(report["holes"], list) and isinstance(report["ambiguities"], list)


def test_C4_v17_every_entry_carries_class_and_gold(report):
    assert entries(report)
    for name, e in entries(report):
        assert e["class"] == {"holes": "A", "contradictions": "B", "ambiguities": "C"}[name], (name, e["key"])
        assert_gold_field(e)


def test_C4_v17_holes_hold_no_gold_sanctioned_goal(report):
    for e in report["holes"]:
        assert e["goal"] not in GOLD_SANCTIONED, e["key"]
        assert e["gold"]["sanctioned"] is False and e["gold"]["tasks"] == [], e["key"]


def test_C4_v17_contradictions_are_gold_sanctioned_class_B(report):
    for e in report["contradictions"]:
        assert e["class"] == "B"
        assert e["goal"] in GOLD_SANCTIONED, e["key"]
        assert e["gold"]["sanctioned"] is True
        assert e["key"].startswith(e["goal"] + ":")
        assert isinstance(e["chain"], list) and e["chain"]
        assert e["goal_true"] is True


def test_C4_v17_offline_audit_reports_G1_G2_G5_as_contradictions_with_their_gold_tasks(report):
    by_goal = {}
    for e in report["contradictions"]:
        by_goal.setdefault(e["goal"], set()).update(e["gold"]["tasks"])
    assert {"G1", "G2", "G5"} <= set(by_goal), sorted(by_goal)
    assert "32" in by_goal["G1"] and "7" in by_goal["G2"] and "18" in by_goal["G5"]


def test_C4_v17_keys_are_unique_across_the_three_lists(report):
    keys = [(e["class"], e["key"]) for _, e in entries(report)]
    assert len(keys) == len(set(keys))
    a_or_b = [e["key"] for name, e in entries(report) if name != "ambiguities"]
    assert len(a_or_b) == len(set(a_or_b)), "a finding is either a hole or a contradiction"
