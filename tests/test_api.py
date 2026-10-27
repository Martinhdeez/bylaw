"""AP1 / C9: the HTTP API over the report store, background audits with SSE progress, ratify and bench. Offline."""
import json
import os
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bylaw import api

client = TestClient(api.app)
PATCH = {"id": "R-test-amend-1", "tool": "cancel_reservation", "allow_if": "False", "policy_ref": "test", "note": ""}
AMENDED = {"id": "H1", "key": "G1:T1QOBS", "class": "A", "goal": "G1", "title": "t", "money_delta": 0.0, "chain": [],
           "diff": {}, "goal_true": True, "replays": "5/5",
           "amendment": {"id": "A1", "hole_id": "H1", "policy_text": "No.", "rule_patch": [PATCH], "rationale": "r"}}
BARE = {**{k: v for k, v in AMENDED.items() if k != "amendment"}, "id": "H2", "key": "G2:XYZ"}
REPORT = {"run": {"domain": "airline"}, "holes": [AMENDED, BARE], "ambiguities": [], "stats": {}}
EVENT_KEYS = {"phase", "message", "muse", "tokens", "llm_calls", "tool_calls", "holes", "t"}


@pytest.fixture(autouse=True)
def stores(tmp_path, monkeypatch):
    """Empty report, cache, ratified and web dirs for every test (C9 v1.1 env overrides, read per request)."""
    for name in ("REPORTS", "CACHE", "WEB_DIST"):
        (tmp_path / name).mkdir()
    monkeypatch.setenv("BYLAW_REPORTS_DIR", str(tmp_path / "REPORTS"))
    monkeypatch.setenv("BYLAW_CACHE_DIR", str(tmp_path / "CACHE"))
    monkeypatch.setenv("BYLAW_RATIFIED_DIR", str(tmp_path / "ratified"))
    monkeypatch.setattr(api, "WEB_DIST", tmp_path / "WEB_DIST")
    return tmp_path


def events(audit_id: str) -> list[dict]:
    with client.stream("GET", f"/api/audits/{audit_id}/events") as r:
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
        return [json.loads(line[5:]) for line in r.iter_lines() if line.startswith("data:")]


def test_domains_and_numbered_policy_lines():
    assert client.get("/api/domains").json() == ["airline", "retail"]
    body = client.get("/api/policy", params={"domain": "airline"}).json()
    assert body["domain"] == "airline" and len(body["lines"]) > 10
    assert body["lines"][0].startswith("# Airline Agent Policy")
    assert client.get("/api/policy", params={"domain": "bank"}).status_code == 422


def test_latest_report_is_404_without_one_and_the_committed_report_otherwise(stores):
    assert client.get("/api/reports/latest", params={"domain": "airline"}).status_code == 404
    (stores / "REPORTS" / "airline.json").write_text(json.dumps(REPORT))
    assert client.get("/api/reports/latest", params={"domain": "airline"}).json() == REPORT
    assert client.get("/api/reports/latest", params={"domain": "retail"}).status_code == 404


def test_latest_is_the_newest_file_by_mtime_across_reports_and_cache(stores):
    older, newer = dict(REPORT, run={"domain": "airline", "n": 1}), dict(REPORT, run={"domain": "airline", "n": 2})
    for path, rep, mtime in [(stores / "CACHE" / "airline-a.json", newer, 300), (stores / "CACHE" / "airline-b.json", older, 200),
                             (stores / "REPORTS" / "airline.json", older, 100), (stores / "CACHE" / "retail-c.json", older, 999)]:
        path.write_text(json.dumps(rep))
        os.utime(path, (mtime, mtime))
    assert client.get("/api/reports/latest", params={"domain": "airline"}).json()["run"]["n"] == 2
    os.utime(stores / "REPORTS" / "airline.json", (400, 400))
    assert client.get("/api/reports/latest", params={"domain": "airline"}).json()["run"]["n"] == 1
    assert client.get("/api/reports/latest", params={"domain": "retail"}).json()["run"]["n"] == 1


def test_default_store_dirs_resolve_from_the_repo_root(monkeypatch, tmp_path):
    for var in ("BYLAW_REPORTS_DIR", "BYLAW_CACHE_DIR", "BYLAW_RATIFIED_DIR"):
        monkeypatch.delenv(var)
    monkeypatch.chdir(tmp_path)
    root = Path(api.__file__).resolve().parents[1]
    assert (api.reports_dir(), api.cache_dir()) == (root / "reports", root / ".cache" / "reports")
    assert api.ratified._path("airline") == root / "ratified" / "airline.json"


def test_hole_lookup_by_key(stores):
    (stores / "REPORTS" / "airline.json").write_text(json.dumps(REPORT))
    assert client.get("/api/holes/G1:T1QOBS", params={"domain": "airline"}).json() == AMENDED
    assert client.get("/api/holes/G9:NOPE", params={"domain": "airline"}).status_code == 404


def test_ratify_appends_once_and_the_ratified_view_shows_base_plus_patch(stores):
    (stores / "REPORTS" / "airline.json").write_text(json.dumps(REPORT))
    for _ in range(2):
        r = client.post("/api/holes/G1:T1QOBS/ratify", params={"domain": "airline"})
        assert r.status_code == 200
        assert r.json() == {"ratified": True, "amendment_id": "A1", "rule_ids": ["R-test-amend-1"]}
    view = client.get("/api/ratified", params={"domain": "airline"}).json()
    assert view["domain"] == "airline"
    assert [(a["hole_key"], a["id"]) for a in view["amendments"]] == [("G1:T1QOBS", "A1")]
    assert "ratified_at" in view["amendments"][0]
    assert view["ruleset"]["tool_rules"][-1] == PATCH
    assert json.loads((stores / "ratified" / "airline.json").read_text())["amendments"][0]["hole_key"] == "G1:T1QOBS"


def test_ratify_a_hole_without_amendment_is_409_and_unknown_hole_404(stores):
    (stores / "REPORTS" / "airline.json").write_text(json.dumps(REPORT))
    assert client.post("/api/holes/G2:XYZ/ratify", params={"domain": "airline"}).status_code == 409
    assert client.post("/api/holes/G9:NOPE/ratify", params={"domain": "airline"}).status_code == 404
    assert client.get("/api/ratified", params={"domain": "airline"}).json()["amendments"] == []


def test_bench_is_served_from_the_store_or_404(stores):
    bench = {"domain": "airline", "budget": 10, "rows": []}
    (stores / "REPORTS" / "airline.bench.json").write_text(json.dumps(bench))
    assert client.get("/api/bench", params={"domain": "airline"}).json() == bench
    assert client.get("/api/bench", params={"domain": "retail"}).status_code == 404


def test_built_web_app_is_served_at_root_and_api_paths_are_not_swallowed(stores):
    assert client.get("/").status_code == 404  # no build
    (stores / "WEB_DIST" / "index.html").write_text("<html>bylaw</html>")
    (stores / "WEB_DIST" / "app.js").write_text("console.log(1)")
    assert client.get("/").text == "<html>bylaw</html>"
    assert client.get("/app.js").text == "console.log(1)"
    assert client.get("/api/nothing").status_code == 404
    (stores / "secret.txt").write_text("outside dist")
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/..%2fsecret.txt"):
        assert "outside dist" not in client.get(path).text, path


@pytest.fixture(scope="module")
def offline_audit(tmp_path_factory):
    """One small offline airline audit with amend requested (drafting needs Muse, so it is skipped)."""
    cache = tmp_path_factory.mktemp("cache")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("BYLAW_CACHE_DIR", str(cache))
        r = client.post("/api/audits", json={"domain": "airline", "use_llm": False, "budget": 30, "amend": True})
        assert r.status_code == 202
        aid = r.json()["id"]
        evs = events(aid)
    return aid, evs, cache


def test_audit_streams_cumulative_progress_ending_in_done(offline_audit):
    aid, evs, _ = offline_audit
    assert evs and all(set(e) == EVENT_KEYS for e in evs)
    assert evs[-1]["phase"] == "done" and [e["phase"] for e in evs].count("done") == 1
    assert {"search", "verify"} <= {e["phase"] for e in evs}
    for key in ("tokens", "llm_calls", "tool_calls", "holes", "t"):
        assert [e[key] for e in evs] == sorted(e[key] for e in evs), f"{key} is not cumulative"
    assert evs[-1]["tool_calls"] > 0 and evs[-1]["llm_calls"] == 0 and not any(e["muse"] for e in evs)
    assert any(e["phase"] == "amend" and "skip" in e["message"] for e in evs)


# A hole the offline BFS proves at budget 30: downgrading 00GMVN to basic economy keeps bags over the allowance (G5).
DOWNGRADE = ("update_reservation_flights", {"reservation_id": "00GMVN", "cabin": "basic_economy",
                                            "flights": [{"flight_number": "HAT204", "date": "2024-05-21"}],
                                            "payment_id": "credit_card_3029145"})
BLOCK = {"id": "R-test-no-upgrade", "tool": "update_reservation_flights", "allow_if": "False", "policy_ref": "t", "note": ""}


def test_muse_audit_with_amend_drafts_backtests_and_counts_llm_calls(monkeypatch):
    """PR1 and AM1 are not merged: the Muse search and drafter are stand-ins that count one LLM call each."""
    import bylaw.backtest
    import bylaw.report

    def fake_search(domain, ruleset, budget, use_llm):
        assert use_llm
        api.llm.USAGE["calls"] += 1
        api.llm.USAGE["prompt_tokens"] += 100
        yield [DOWNGRADE]

    def draft(domain, ruleset, hole):
        api.llm.USAGE["calls"] += 1
        return {"id": "A1", "hole_id": hole["id"], "policy_text": "No upgrades.", "rule_patch": [BLOCK], "rationale": "r"}

    fake_amend = types.ModuleType("bylaw.amend")
    fake_amend.draft, fake_amend.apply = draft, lambda rs, am: {**rs, "tool_rules": rs["tool_rules"] + am["rule_patch"]}
    monkeypatch.setitem(sys.modules, "bylaw.amend", fake_amend)
    monkeypatch.setattr(bylaw.report, "search", fake_search)
    monkeypatch.setattr(bylaw.backtest, "backtest", lambda d, rs: {"tasks": 43, "blocked": len(rs["tool_rules"]) % 2,
                                                                   "unknown": 0, "results": [{"id": "7", "blocked": True}]})
    monkeypatch.setenv("MODEL", "muse-spark-1.3")
    r = client.post("/api/audits", json={"domain": "airline", "use_llm": True, "budget": 5, "amend": True})
    evs = events(r.json()["id"])
    assert evs[-1]["phase"] == "done", evs[-1]
    assert next(e for e in evs if e["phase"] == "search")["muse"] is True
    assert next(e for e in evs if e["phase"] == "amend")["muse"] is True
    assert "backtest" in {e["phase"] for e in evs}
    assert evs[-1]["llm_calls"] == 2 and evs[-1]["tokens"] == 100
    report = client.get("/api/reports/latest", params={"domain": "airline"}).json()
    (hole,) = [h for h in report["holes"] if h["key"] == "G5:00GMVN"]
    assert report["run"]["mode"] == "muse" and report["run"]["model"] == "muse-spark-1.3"
    assert hole["amendment"]["rule_patch"] == [BLOCK] and hole["closes"] is True
    assert hole["backtest"]["tasks"] == 43 and "baseline_blocked" in hole["backtest"]
    assert client.post("/api/holes/G5:00GMVN/ratify", params={"domain": "airline"}).json()["rule_ids"] == [BLOCK["id"]]


def test_done_audit_report_is_stored_in_the_cache(offline_audit):
    aid, evs, cache = offline_audit
    st = client.get(f"/api/audits/{aid}").json()
    assert (st["id"], st["domain"], st["status"], st["error"]) == (aid, "airline", "done", None)
    assert st["report"]["run"]["mode"] == "bfs" and evs[-1]["holes"] == len(st["report"]["holes"]) > 0
    assert json.loads((cache / f"airline-{aid}.json").read_text()) == st["report"]


def test_late_subscriber_gets_every_past_event(offline_audit):
    aid, evs, _ = offline_audit
    assert events(aid) == evs


def test_audit_becomes_latest_for_its_domain(stores):
    committed = stores / "REPORTS" / "airline.json"
    committed.write_text(json.dumps(REPORT))
    os.utime(committed, (1, 1))  # older than anything the audit writes
    r = client.post("/api/audits", json={"domain": "airline", "use_llm": False, "budget": 1})
    evs = events(r.json()["id"])
    assert evs[-1]["phase"] == "done"
    latest = client.get("/api/reports/latest", params={"domain": "airline"}).json()
    assert latest == client.get(f"/api/audits/{r.json()['id']}").json()["report"]
    assert list((stores / "CACHE").glob("airline-*.json"))


def test_failing_audit_ends_in_error_event_and_error_status():
    r = client.post("/api/audits", json={"domain": "retail", "use_llm": False, "budget": 5})  # no retail BFS move set
    evs = events(r.json()["id"])
    assert evs[-1]["phase"] == "error" and evs[-1]["message"]
    st = client.get(f"/api/audits/{r.json()['id']}").json()
    assert st["status"] == "error" and st["error"] and st["report"] is None
    assert client.get("/api/reports/latest", params={"domain": "retail"}).status_code == 404


def test_unknown_audit_is_404_and_bad_body_422():
    assert client.get("/api/audits/nope").status_code == 404
    assert client.get("/api/audits/nope/events").status_code == 404
    assert client.post("/api/audits", json={"domain": "bank"}).status_code == 422
    assert client.post("/api/audits", json={"domain": "airline", "budget": 0}).status_code == 422
