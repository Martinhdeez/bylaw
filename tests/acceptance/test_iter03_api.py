"""Acceptance tests for AP1: the HTTP API (C9) and the ratified store (C10).

Written blind from docs/plan/03-product/requirements.md and contracts.md, with C1-C8 for the shapes.

Store seams (the contract names paths, not a test override for the report store):
- The committed report store is `reports/<domain>.json` and `reports/<domain>.bench.json` at the repo
  root. The module fixture writes the airline fixtures there and hides the retail ones before the app
  is imported, and restores every file afterwards. API-run audits land in `.cache/reports/`, which is
  set aside for the module and restored too, so a previous run cannot make retail "latest".
- `BYLAW_RATIFIED_DIR` points at a tmp dir for the whole module (set before import, in case it is read
  then); each ratify test starts from a missing `<dir>/airline.json`, which C10 says loads as empty.
Tests run in file order: the retail 404 checks come before the retail audit that makes retail latest.
"""
import importlib
import json
import shutil
import time
from datetime import datetime

import pytest

from conftest import (AMEND_RULE, AMENDMENT, HOP_KEY, NO_AMEND_KEY, ROOT, load_ruleset,
                      report_fixture)

REPORTS = ROOT / "reports"
CACHE_REPORTS = ROOT / ".cache" / "reports"
BENCH = {"domain": "airline", "budget": 50, "rows": [
    {"mode": "bfs", "holes": 1, "hole_keys": [HOP_KEY], "tool_calls": 50, "llm_calls": 0, "tokens": 0,
     "seconds": 1.5},
    {"mode": "muse", "holes": 2, "hole_keys": [HOP_KEY, NO_AMEND_KEY], "tool_calls": 50, "llm_calls": 3,
     "tokens": 1200, "seconds": 9.0},
]}
PHASES = {"compile", "search", "verify", "amend", "backtest", "done", "error"}
COUNTERS = ("tokens", "llm_calls", "tool_calls", "holes")


@pytest.fixture(scope="module")
def ratified_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("ratified")


@pytest.fixture(scope="module")
def client(ratified_dir, tmp_path_factory):
    from fastapi.testclient import TestClient

    backup = tmp_path_factory.mktemp("store-backup")
    store = {REPORTS / "airline.json": report_fixture(), REPORTS / "airline.bench.json": BENCH,
             REPORTS / "retail.json": None, REPORTS / "retail.bench.json": None}
    made_reports = not REPORTS.exists()
    REPORTS.mkdir(exist_ok=True)
    saved = {}
    for path, content in store.items():
        if path.exists():
            saved[path] = backup / path.name
            shutil.copy2(path, saved[path])
            path.unlink()
        if content is not None:
            path.write_text(json.dumps(content))
    cache_saved = backup / "cache-reports"
    if CACHE_REPORTS.exists():
        shutil.move(CACHE_REPORTS, cache_saved)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("BYLAW_RATIFIED_DIR", str(ratified_dir))
        mp.delenv("MODEL_API_KEY", raising=False)
        try:
            api = importlib.import_module("bylaw.api")
            with TestClient(api.app) as c:
                yield c
        finally:
            for path in store:
                path.unlink(missing_ok=True)
            for path, src in saved.items():
                shutil.copy2(src, path)
            if made_reports and not any(REPORTS.iterdir()):
                REPORTS.rmdir()
            shutil.rmtree(CACHE_REPORTS, ignore_errors=True)
            if cache_saved.exists():
                shutil.move(cache_saved, CACHE_REPORTS)


@pytest.fixture
def no_store(ratified_dir):
    (ratified_dir / "airline.json").unlink(missing_ok=True)
    return ratified_dir / "airline.json"


@pytest.fixture
def offline_llm(monkeypatch):
    """With use_llm=false nothing may reach the model client."""
    llm = importlib.import_module("bylaw.llm")

    def refuse(*a, **k):
        raise AssertionError("offline audit called the model")

    monkeypatch.setattr(llm, "structured", refuse)


def domain_obj(name):
    return importlib.import_module("bylaw.domain").get_domain(name)


def read_events(client, audit_id):
    events = []
    with client.stream("GET", f"/api/audits/{audit_id}/events") as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        for line in r.iter_lines():
            if line.startswith("data:"):
                ev = json.loads(line[len("data:"):].strip())
                events.append(ev)
                if ev["phase"] in ("done", "error"):
                    break
    return events


def wait_finished(client, audit_id):
    for _ in range(600):
        body = client.get(f"/api/audits/{audit_id}").json()
        if body["status"] != "running":
            return body
        time.sleep(0.1)
    raise AssertionError("audit still running after 60 s")


def parse_iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ---------- REQ-AP1-1 ----------

def test_REQ_AP1_1_domains_lists_airline_and_retail(client):
    r = client.get("/api/domains")
    assert r.status_code == 200
    assert r.json() == ["airline", "retail"]


@pytest.mark.parametrize("name", ["airline", "retail"])
def test_REQ_AP1_1_policy_is_the_domain_policy_text_as_numbered_lines(client, name):
    r = client.get("/api/policy", params={"domain": name})
    assert r.status_code == 200
    body = r.json()
    assert body["domain"] == name
    lines = body["lines"]
    assert isinstance(lines, list) and len(lines) > 10
    assert all(isinstance(line, str) and "\n" not in line for line in lines)
    text = domain_obj(name).policy_text
    assert "\n".join(lines).strip() == text.strip()
    # 1-based line n is lines[n-1]: the first line of the text is line 1.
    assert lines[0] == text.lstrip("\n").splitlines()[0]


# ---------- REQ-AP1-2 ----------

def test_REQ_AP1_2_latest_report_is_the_stored_report_with_amendment_fields(client):
    r = client.get("/api/reports/latest", params={"domain": "airline"})
    assert r.status_code == 200
    body = r.json()
    assert body == report_fixture()
    h1 = body["holes"][0]
    assert h1["amendment"] == AMENDMENT and h1["closes"] is True and h1["backtest"]["tasks"] == 43


def test_REQ_AP1_2_latest_report_is_404_when_the_domain_has_none(client):
    assert client.get("/api/reports/latest", params={"domain": "retail"}).status_code == 404


def test_REQ_AP1_2_hole_by_key_is_the_hole_of_the_latest_report(client):
    r = client.get(f"/api/holes/{HOP_KEY}", params={"domain": "airline"})
    assert r.status_code == 200
    assert r.json() == report_fixture()["holes"][0]
    r = client.get(f"/api/holes/{NO_AMEND_KEY}", params={"domain": "airline"})
    assert r.status_code == 200 and r.json()["id"] == "H2"


def test_REQ_AP1_2_absent_hole_key_is_404(client):
    assert client.get("/api/holes/G2:NOSUCH", params={"domain": "airline"}).status_code == 404


# ---------- REQ-AP1-5 (bench 404 before the retail audit) ----------

def test_REQ_AP1_5_bench_returns_the_stored_bench_json(client):
    r = client.get("/api/bench", params={"domain": "airline"})
    assert r.status_code == 200
    assert r.json() == BENCH


def test_REQ_AP1_5_bench_is_404_when_none_is_stored(client):
    assert client.get("/api/bench", params={"domain": "retail"}).status_code == 404


def test_REQ_AP1_5_built_web_app_is_served_at_root(client):
    index = ROOT / "web" / "dist" / "index.html"
    if not index.exists():
        pytest.skip("web/dist is not built (run npm run build in web/ first)")
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.text == index.read_text()


# ---------- REQ-AP1-4 ----------

def test_REQ_AP1_4_empty_store_gives_the_hand_ruleset_and_no_amendments(client, no_store):
    r = client.get("/api/ratified", params={"domain": "airline"})
    assert r.status_code == 200
    body = r.json()
    assert body["domain"] == "airline"
    assert body["amendments"] == []
    assert body["ruleset"] == load_ruleset("airline")


def test_REQ_AP1_4_ratify_appends_the_amendment_patch_to_the_store(client, no_store):
    r = client.post(f"/api/holes/{HOP_KEY}/ratify", params={"domain": "airline"})
    assert r.status_code == 200
    assert r.json() == {"ratified": True, "amendment_id": "A1", "rule_ids": [AMEND_RULE["id"]]}
    stored = json.loads(no_store.read_text())
    assert stored["domain"] == "airline"
    assert len(stored["amendments"]) == 1
    a = stored["amendments"][0]
    assert a["id"] == "A1" and a["hole_key"] == HOP_KEY
    assert a["rule_patch"] == [AMEND_RULE]
    assert a["policy_text"] == AMENDMENT["policy_text"] and a["rationale"] == AMENDMENT["rationale"]
    parse_iso(a["ratified_at"])


def test_REQ_AP1_4_ratifying_twice_is_idempotent(client, no_store):
    first = client.post(f"/api/holes/{HOP_KEY}/ratify", params={"domain": "airline"})
    second = client.post(f"/api/holes/{HOP_KEY}/ratify", params={"domain": "airline"})
    assert first.status_code == second.status_code == 200
    assert second.json()["ratified"] is True and second.json()["amendment_id"] == "A1"
    assert len(json.loads(no_store.read_text())["amendments"]) == 1
    body = client.get("/api/ratified", params={"domain": "airline"}).json()
    assert len(body["amendments"]) == 1
    ids = [r["id"] for r in body["ruleset"]["tool_rules"]]
    assert ids.count(AMEND_RULE["id"]) == 1


def test_REQ_AP1_4_ratified_returns_base_plus_patches_and_the_amendments(client, no_store):
    client.post(f"/api/holes/{HOP_KEY}/ratify", params={"domain": "airline"})
    body = client.get("/api/ratified", params={"domain": "airline"}).json()
    hand = load_ruleset("airline")
    assert body["domain"] == "airline"
    assert body["ruleset"]["tool_rules"] == hand["tool_rules"] + [AMEND_RULE]
    assert body["ruleset"]["forbidden_goals"] == hand["forbidden_goals"]
    [a] = body["amendments"]
    assert a["id"] == "A1" and a["hole_key"] == HOP_KEY and a["rule_patch"] == [AMEND_RULE]
    parse_iso(a["ratified_at"])


def test_REQ_AP1_4_hole_without_amendment_is_409_and_stores_nothing(client, no_store):
    r = client.post(f"/api/holes/{NO_AMEND_KEY}/ratify", params={"domain": "airline"})
    assert r.status_code == 409
    assert client.get("/api/ratified", params={"domain": "airline"}).json()["amendments"] == []


def test_REQ_AP1_4_ratified_store_module_matches_the_api(client, no_store):
    ratified = importlib.import_module("bylaw.ratified")
    assert ratified.load("airline")["amendments"] == []
    client.post(f"/api/holes/{HOP_KEY}/ratify", params={"domain": "airline"})
    assert [a["id"] for a in ratified.load("airline")["amendments"]] == ["A1"]
    eff = ratified.effective_ruleset("airline")
    assert eff == client.get("/api/ratified", params={"domain": "airline"}).json()["ruleset"]
    assert eff["tool_rules"][-1] == AMEND_RULE


# ---------- REQ-AP1-3 (runs last: it makes retail latest) ----------

def test_REQ_AP1_3_offline_audit_streams_progress_and_becomes_latest(client, offline_llm):
    r = client.post("/api/audits", json={"domain": "retail", "use_llm": False, "budget": 30, "amend": False})
    assert r.status_code == 202
    audit_id = r.json()["id"]
    assert isinstance(audit_id, str) and audit_id

    events = read_events(client, audit_id)
    assert events, "no events"
    assert events[-1]["phase"] == "done", events[-1]
    assert all(e["phase"] != "error" for e in events)
    for e in events:
        assert e["phase"] in PHASES
        assert isinstance(e["message"], str)
        assert e["muse"] is False  # use_llm=false: no phase uses Muse
        assert all(isinstance(e[k], int) and e[k] >= 0 for k in COUNTERS)
        assert isinstance(e["t"], (int, float))
    for a, b in zip(events, events[1:]):  # cumulative counters never go down
        assert all(b[k] >= a[k] for k in COUNTERS), (a, b)
    assert events[-1]["llm_calls"] == 0 and events[-1]["tokens"] == 0

    body = wait_finished(client, audit_id)
    assert body["id"] == audit_id and body["domain"] == "retail"
    assert body["status"] == "done" and body["error"] is None
    report = body["report"]
    assert report["run"]["domain"] == "retail"
    assert isinstance(report["holes"], list) and isinstance(report["ambiguities"], list)
    assert report["stats"]["llm_calls"] == 0
    assert events[-1]["holes"] == len(report["holes"])

    latest = client.get("/api/reports/latest", params={"domain": "retail"})
    assert latest.status_code == 200 and latest.json() == report
    saved = CACHE_REPORTS / f"retail-{audit_id}.json"
    assert saved.exists()
    assert json.loads(saved.read_text()) == report


def test_REQ_AP1_3_late_subscriber_gets_every_past_event(client, offline_llm):
    audit_id = client.post("/api/audits",
                           json={"domain": "retail", "use_llm": False, "budget": 10, "amend": False}).json()["id"]
    first = read_events(client, audit_id)
    wait_finished(client, audit_id)
    late = read_events(client, audit_id)
    assert late == first
    assert late[-1]["phase"] == "done"


def test_REQ_AP1_3_newest_audit_wins_latest(client, offline_llm):
    ids = []
    for _ in range(2):
        audit_id = client.post("/api/audits",
                               json={"domain": "retail", "use_llm": False, "budget": 10, "amend": False}).json()["id"]
        read_events(client, audit_id)
        ids.append(audit_id)
        report = wait_finished(client, audit_id)["report"]
    assert ids[0] != ids[1]
    assert client.get("/api/reports/latest", params={"domain": "retail"}).json() == report


def test_REQ_AP1_3_airline_latest_is_untouched_by_a_retail_audit(client):
    assert client.get("/api/reports/latest", params={"domain": "airline"}).json() == report_fixture()


@pytest.mark.live
def test_REQ_AP1_3_live_audit_marks_muse_phases(client):
    r = client.post("/api/audits", json={"domain": "airline", "use_llm": True, "budget": 40, "amend": False})
    events = read_events(client, r.json()["id"])
    assert events[-1]["phase"] == "done"
    assert any(e["muse"] for e in events)
    assert events[-1]["llm_calls"] > 0 and events[-1]["tokens"] > 0
