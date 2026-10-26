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
    assert rows["bfs"]["llm_calls"] == 0 and rows["muse"]["llm_calls"] == 7
    assert any(k.startswith("G7:") for k in rows["muse"]["ambiguity_keys"])
    printed = capsys.readouterr().out
    assert "bfs" in printed and "muse" in printed and "tool_calls" in printed
