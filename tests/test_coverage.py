"""CV1: per-goal coverage in the report (stats.per_goal) and `python -m bylaw coverage` (REQ-CV1-1)."""
import json

import bylaw.report
from bylaw.__main__ import main
from bylaw.domain import get_domain
from bylaw.env.tau2_airline import RULESET
from tests.test_report import ONLY_1KUOX2

DOMAIN = get_domain("airline")
RULES = json.loads(RULESET.read_text())


def test_per_goal_counts_the_chains_aimed_at_each_goal_their_executed_steps_and_findings(monkeypatch):
    g2_target = DOMAIN.targets("G2")[0]["reservation_id"]  # basic economy, no insurance, booked >24h ago
    blocked = [("cancel_reservation", {"reservation_id": g2_target, "reason": "change of plan"})]  # rules block step 1
    hole = [(s["tool"], json.loads(s["args_json"])) for s in ONLY_1KUOX2["steps"]]  # 1KUOX2: G1 target, not G2

    def fake_search(domain, ruleset, budget, use_llm, llm=None):
        yield blocked
        yield hole

    monkeypatch.setattr(bylaw.report, "search", fake_search)
    r = bylaw.report.audit(DOMAIN, RULES, budget=10)
    pg = r["stats"]["per_goal"]
    assert set(pg) == set(DOMAIN.goals)
    assert {k: pg["G1"][k] for k in ("chains", "executed")} == {"chains": 2, "executed": 2}
    assert pg["G2"] == {"chains": 1, "executed": 0, "A": 0, "B": 0, "C": 0}
    assert (pg["G1"]["A"], pg["G1"]["B"]) == (0, 1)  # G1 is gold-sanctioned (tau2 task 32, contracts v1.7): Class B
    for gid, counts in pg.items():
        assert counts["A"] == sum(h["goal"] == gid for h in r["holes"])
        assert counts["B"] == sum(e["goal"] == gid for e in r["contradictions"])
        assert counts["C"] == sum(e["goal"] == gid for e in r["ambiguities"])


NEW = {"run": {"domain": "airline", "mode": "bfs", "budget": 2000},
       "holes": [{"goal": "G1", "class": "A"}], "ambiguities": [{"goal": "G7", "class": "C"}],
       "stats": {"per_goal": {"G1": {"chains": 120, "executed": 300, "A": 1, "B": 0, "C": 0},
                              "G7": {"chains": 80, "executed": 95, "A": 0, "B": 2, "C": 1}}}}


def test_coverage_prints_a_markdown_row_per_goal_and_writes_the_json(tmp_path, capsys):
    rep, out = tmp_path / "report.json", tmp_path / "coverage.json"
    rep.write_text(json.dumps(NEW))
    main(["coverage", str(rep), "--json", str(out)])
    lines = capsys.readouterr().out.strip().splitlines()
    table = [ln for ln in lines if ln.startswith("|")]
    assert table[0].replace(" ", "") == "|goal|chains|executed|A|B|C|"
    assert set(table[1].replace(" ", "")) <= set("|-:")
    assert table[2].replace(" ", "") == "|G1|120|300|1|0|0|"
    assert table[3].replace(" ", "") == "|G7|80|95|0|2|1|"
    rows = json.loads(out.read_text())["goals"]
    assert rows == [{"goal": "G1", "chains": 120, "executed": 300, "A": 1, "B": 0, "C": 0},
                    {"goal": "G7", "chains": 80, "executed": 95, "A": 0, "B": 2, "C": 1}]


def test_an_old_report_without_per_goal_gives_class_counts_and_na(tmp_path, capsys):
    old = {"run": {"domain": "airline", "mode": "bfs", "budget": 2000},
           "holes": [{"goal": "G1", "class": "A"}, {"goal": "G1", "class": "A"}],
           "contradictions": [{"goal": "G2", "class": "B"}],
           "ambiguities": [{"goal": "G7", "class": "C"}],
           "stats": {"chains_tried": 9, "tool_calls": 9}}
    rep, out = tmp_path / "old.json", tmp_path / "coverage.json"
    rep.write_text(json.dumps(old))
    main(["coverage", str(rep), "--json", str(out)])
    table = {ln.replace(" ", "").split("|")[1]: ln.replace(" ", "") for ln in capsys.readouterr().out.splitlines()
             if ln.startswith("| G")}
    assert set(table) == set(DOMAIN.goals)  # every forbidden goal of the domain, with or without findings
    assert table["G1"] == "|G1|n/a|n/a|2|0|0|"
    assert table["G2"] == "|G2|n/a|n/a|0|1|0|"
    assert table["G7"] == "|G7|n/a|n/a|0|0|1|"
    assert table["G3"] == "|G3|n/a|n/a|0|0|0|"
    rows = {r["goal"]: r for r in json.loads(out.read_text())["goals"]}
    assert rows["G1"] == {"goal": "G1", "chains": None, "executed": None, "A": 2, "B": 0, "C": 0}
