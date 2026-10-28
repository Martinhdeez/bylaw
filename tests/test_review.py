"""BR1: blind reviewer (REQ-BR1-1) and its agreement with the engine class (REQ-BR1-2), model scripted offline."""
import copy
import json
import re

from bylaw import review
from bylaw.__main__ import main
from bylaw.domain import get_domain

DOMAIN = get_domain("airline")


def _entry(id_, cls, goal, res, cabin):
    step = {"tool": "update_reservation_flights", "ok": True,
            "args": {"reservation_id": res, "cabin": cabin, "flights": [], "payment_id": "credit_card_1"},
            "verdicts": [{"rule_id": "R-flights-active", "ok": True, "policy_ref": "x"}]}
    return {"id": id_, "key": f"{goal}:{res}", "class": cls, "goal": goal,
            "title": f"{DOMAIN.goals[goal].name} on {res}", "money_delta": 0.0, "chain": [step],
            "diff": {"reservations": {res: {"before": {"cabin": "basic_economy"}, "after": {"cabin": cabin}}}},
            "goal_true": True, "replays": "5/5", "gold": {"sanctioned": cls == "B", "tasks": []}}


# Engine classes: two A, one B, one C.
REPORT = {"run": {"commit": "abc123", "domain": "airline", "model": "", "mode": "bfs", "started": "", "budget": 10,
                  "goals_commit": ""},
          "holes": [_entry("H1", "A", "G1", "AAA111", "economy"), _entry("H2", "A", "G5", "BBB222", "business")],
          "contradictions": [_entry("B1", "B", "G2", "CCC333", "economy")],
          "ambiguities": [_entry("C1", "C", "G7", "DDD444", "business")],
          "stats": {}}


class Scripted:
    """Stands in for bylaw.llm.structured: answers by the reservation named in the prompt, records every call."""

    def __init__(self, verdicts):
        self.verdicts, self.calls = verdicts, []

    def __call__(self, messages, schema, name, effort=None, **opts):
        self.calls.append({"messages": copy.deepcopy(messages), "schema": schema})
        text = json.dumps(messages)
        res = next(r for r in self.verdicts if r in text)
        return {"verdict": self.verdicts[res], "reason": f"judged {res}"}


ALL_AGREE = {"AAA111": "violation", "BBB222": "violation", "CCC333": "sanctioned", "DDD444": "unclear"}
# A: one violation, one unclear. B: called a violation. C: unclear.
MIXED = {"AAA111": "violation", "BBB222": "unclear", "CCC333": "violation", "DDD444": "unclear"}


def test_prompt_carries_no_class_goal_or_finding_label():
    llm = Scripted(ALL_AGREE)
    review.review(REPORT, domain=DOMAIN, llm=llm)
    assert len(llm.calls) == 4
    entries = REPORT["holes"] + REPORT["contradictions"] + REPORT["ambiguities"]
    for call in llm.calls:
        text = "\n".join(m["content"] for m in call["messages"])
        for g in DOMAIN.goals.values():
            assert not re.search(rf"\b{g.id}\b", text), g.id
            assert g.name not in text and g.name.replace("_", " ") not in text, g.name
        for e in entries:
            assert e["key"] not in text and e["title"] not in text
            assert not re.search(rf"\b{e['id']}\b", text), e["id"]
        for word in ('"class"', '"goal"', '"gold"', '"key"', "Class A", "Class B", "Class C"):
            assert word not in text, word


def test_each_finding_is_judged_in_a_fresh_context_with_its_chain_diff_and_policy():
    llm = Scripted(ALL_AGREE)
    review.review(REPORT, domain=DOMAIN, llm=llm)
    for call, res in zip(llm.calls, ["AAA111", "BBB222", "CCC333", "DDD444"]):
        assert [m["role"] for m in call["messages"]] == ["system", "user"]
        text = "\n".join(m["content"] for m in call["messages"])
        assert res in text and "update_reservation_flights" in text and "basic_economy" in text
        assert DOMAIN.policy_text in text
        assert not any(other in text for other in ALL_AGREE if other != res)


def test_verdict_comes_from_a_strict_schema_and_is_recorded_with_its_reason():
    llm = Scripted(MIXED)
    out = review.review(REPORT, domain=DOMAIN, llm=llm)
    schema = llm.calls[0]["schema"]
    assert schema["properties"]["verdict"]["enum"] == ["violation", "sanctioned", "unclear"]
    assert schema["additionalProperties"] is False and set(schema["required"]) == {"verdict", "reason"}
    assert [(r["key"], r["verdict"], r["reason"]) for r in out["reviews"]] == [
        ("G1:AAA111", "violation", "judged AAA111"), ("G5:BBB222", "unclear", "judged BBB222"),
        ("G2:CCC333", "violation", "judged CCC333"), ("G7:DDD444", "unclear", "judged DDD444")]


def test_agreement_overall_per_class_and_confusion_matrix():
    ag = review.review(REPORT, domain=DOMAIN, llm=Scripted(MIXED))["agreement"]
    assert ag["overall"] == {"n": 4, "agree": 2, "rate": 0.5}
    assert ag["by_class"] == {"A": {"n": 2, "agree": 1, "rate": 0.5}, "B": {"n": 1, "agree": 0, "rate": 0.0},
                              "C": {"n": 1, "agree": 1, "rate": 1.0}}
    assert ag["confusion"] == {"A": {"violation": 1, "sanctioned": 0, "unclear": 1},
                               "B": {"violation": 1, "sanctioned": 0, "unclear": 0},
                               "C": {"violation": 0, "sanctioned": 0, "unclear": 1}}


def test_a_class_with_no_findings_has_no_rate():
    report = dict(REPORT, contradictions=[])
    ag = review.review(report, domain=DOMAIN, llm=Scripted(ALL_AGREE))["agreement"]
    assert ag["by_class"]["B"] == {"n": 0, "agree": 0, "rate": None}
    assert ag["overall"] == {"n": 3, "agree": 3, "rate": 1.0}


def test_cli_writes_the_review_and_prints_the_rates_with_the_run_named(tmp_path, monkeypatch, capsys):
    src, out = tmp_path / "report.json", tmp_path / "review.json"
    src.write_text(json.dumps(REPORT))
    monkeypatch.setattr(review.llm_mod, "structured", Scripted(MIXED))
    monkeypatch.setenv("MODEL", "muse-test-model")
    main(["review", str(src), "-o", str(out)])
    data = json.loads(out.read_text())
    assert data["run"]["model"] == "muse-test-model" and data["run"]["report"] == str(src)
    assert re.fullmatch(r"[0-9a-f]{40}", data["run"]["commit"])
    assert data["agreement"]["overall"]["rate"] == 0.5 and len(data["reviews"]) == 4
    printed = capsys.readouterr().out
    assert str(src) in printed and "muse-test-model" in printed and data["run"]["commit"][:7] in printed
    assert "2/4" in printed and "0.50" in printed
    assert re.search(r"A\s.*1/2", printed) and re.search(r"B\s.*0/1", printed) and re.search(r"C\s.*1/1", printed)
    assert re.search(r"A\s+1\s+0\s+1", printed)  # the confusion matrix row for class A
