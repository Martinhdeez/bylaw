"""PR1: `python -m bylaw bench` (C5 v1.2): bfs and muse rows on the same budget, printed and written as JSON."""
import json

from bylaw import llm
from bylaw.__main__ import main
from tests.test_proposer import G7_TWICE, ScriptedMuse


def test_bench_compares_muse_with_blind_bfs_on_one_budget(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(llm, "structured", ScriptedMuse({"G7": [G7_TWICE]}))
    out = tmp_path / "bench.json"
    main(["bench", "--domain", "airline", "--budget", "20", "--modes", "bfs,muse", "-o", str(out)])
    data = json.loads(out.read_text())
    assert (data["domain"], data["budget"]) == ("airline", 20)
    rows = {r["mode"]: r for r in data["rows"]}
    assert list(rows) == ["bfs", "muse"]
    for r in rows.values():
        assert r["holes"] == len(r["hole_keys"]) == len(set(r["hole_keys"]))
        assert 0 < r["tool_calls"] <= 20 and r["seconds"] >= 0
        # v1.6: when each hole was first proved, for holes-vs-budget curves
        assert [f["key"] for f in r["found"]] == r["hole_keys"]
        steps = [f["tool_calls"] for f in r["found"]]
        assert steps == sorted(steps) and all(1 <= s <= r["tool_calls"] for s in steps)
        assert all(0 <= f["seconds"] <= r["seconds"] for f in r["found"])
    assert rows["bfs"]["llm_calls"] == 0 and rows["muse"]["llm_calls"] == 7
    assert any(k.startswith("G7:") for k in rows["muse"]["ambiguity_keys"])
    printed = capsys.readouterr().out
    assert "bfs" in printed and "muse" in printed and "tool_calls" in printed


def test_bench_json_names_the_model_and_the_commit(tmp_path, monkeypatch):
    """FX1 / REQ-DM1-1: a bench result names the commit and the model that produced it."""
    monkeypatch.setattr(llm, "structured", ScriptedMuse({"G7": [G7_TWICE]}))
    monkeypatch.setenv("MODEL", "muse-test-model")
    out = tmp_path / "bench.json"
    main(["bench", "--domain", "airline", "--budget", "10", "--modes", "bfs,muse", "-o", str(out)])
    data = json.loads(out.read_text())
    assert data["model"] == "muse-test-model"
    assert data["commit"] and data["commit"] == data["rows"][0]["commit"]
    assert len(data["rows"]) == 2  # existing fields kept
    main(["bench", "--domain", "airline", "--budget", "10", "--modes", "bfs", "-o", str(out)])
    assert json.loads(out.read_text())["model"] is None


def test_bench_model_is_null_when_every_muse_call_failed(tmp_path, monkeypatch):
    """C5 v1.9: a muse row that never got an answer must not name a model."""
    def broken(messages, schema, name, **kw):
        raise RuntimeError("401 Unauthorized")

    monkeypatch.setattr(llm, "structured", broken)
    out = tmp_path / "bench.json"
    main(["bench", "--domain", "airline", "--budget", "10", "--modes", "muse", "-o", str(out)])
    assert json.loads(out.read_text())["model"] is None
