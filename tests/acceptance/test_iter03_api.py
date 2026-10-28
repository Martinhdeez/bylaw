"""Acceptance tests for AP1: the HTTP API (C9 v1.1) and the ratified store (C10).

Written blind from docs/plan/03-product/requirements.md and contracts.md, with C1-C8 for the shapes.
Every test gets its own tmp store dirs through BYLAW_REPORTS_DIR, BYLAW_CACHE_DIR and
BYLAW_RATIFIED_DIR (read on every request, 03 v1.1): the reports dir holds the airline report and
bench fixtures, nothing for retail; the cache and ratified dirs start empty.
"""
import faulthandler
import importlib
import json
import os
import threading
import time
from datetime import datetime
from types import SimpleNamespace

import pytest

from conftest import (AMEND_RULE, AMENDMENT, HOP_KEY, NO_AMEND_KEY, ROOT, load_ruleset,
                      report_fixture)

# 03 contracts v1.3: a ratified rule_patch rule id is stored as <hole_key>/<rule_id>.
RATIFIED_RULE = {**AMEND_RULE, "id": f"{HOP_KEY}/{AMEND_RULE['id']}"}

BENCH = {"domain": "airline", "budget": 50, "rows": [
    {"mode": "bfs", "holes": 1, "hole_keys": [HOP_KEY], "tool_calls": 50, "llm_calls": 0, "tokens": 0,
     "seconds": 1.5},
    {"mode": "muse", "holes": 2, "hole_keys": [HOP_KEY, NO_AMEND_KEY], "tool_calls": 50, "llm_calls": 3,
     "tokens": 1200, "seconds": 9.0},
]}
PHASES = {"compile", "search", "verify", "amend", "backtest", "done", "error"}
COUNTERS = ("tokens", "llm_calls", "tool_calls", "holes")


@pytest.fixture(scope="module")
def app():
    return importlib.import_module("bylaw.api").app


@pytest.fixture
def stores(tmp_path, monkeypatch):
    dirs = SimpleNamespace(reports=tmp_path / "reports", cache=tmp_path / "cache", ratified=tmp_path / "ratified")
    for d in vars(dirs).values():
        d.mkdir()
    (dirs.reports / "airline.json").write_text(json.dumps(report_fixture()))
    (dirs.reports / "airline.bench.json").write_text(json.dumps(BENCH))
    monkeypatch.setenv("BYLAW_REPORTS_DIR", str(dirs.reports))
    monkeypatch.setenv("BYLAW_CACHE_DIR", str(dirs.cache))
    monkeypatch.setenv("BYLAW_RATIFIED_DIR", str(dirs.ratified))
    return dirs


@pytest.fixture
def client(app, stores):
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c
    faulthandler.cancel_dump_traceback_later()  # teardown finished: disarm read_events' watchdog


@pytest.fixture
def no_store(stores):
    return stores.ratified / "airline.json"


@pytest.fixture
def offline_llm(monkeypatch):
    """With use_llm=false nothing may reach the model client."""
    llm = importlib.import_module("bylaw.llm")

    def refuse(*a, **k):
        raise AssertionError("offline audit called the model")

    monkeypatch.setattr(llm, "structured", refuse)


def domain_obj(name):
    return importlib.import_module("bylaw.domain").get_domain(name)


EVENTS_DEADLINE = 120  # seconds for one SSE read to reach done/error


def read_events(client, audit_id, deadline=EVENTS_DEADLINE):
    """Read the stream in a daemon thread so a stream that never ends fails instead of hanging.

    On timeout the test fails; a watchdog stays armed so that, if teardown then blocks on the stuck
    stream, the process exits with a traceback instead of hanging the gate.
    """
    events, failure = [], []

    def read():
        try:
            with client.stream("GET", f"/api/audits/{audit_id}/events") as r:
                assert r.status_code == 200
                assert r.headers["content-type"].startswith("text/event-stream")
                for line in r.iter_lines():
                    if line.startswith("data:"):
                        ev = json.loads(line[len("data:"):].strip())
                        events.append(ev)
                        if ev["phase"] in ("done", "error"):
                            break
        except BaseException as e:  # re-raised in the test thread
            failure.append(e)

    reader = threading.Thread(target=read, daemon=True)
    faulthandler.dump_traceback_later(deadline * 2, exit=True)
    reader.start()
    reader.join(deadline)
    if reader.is_alive():
        pytest.fail(f"event stream of {audit_id} gave no done/error within {deadline} s; got {events[-3:]}")
    faulthandler.cancel_dump_traceback_later()
    if failure:
        raise failure[0]
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


def test_REQ_AP1_2_latest_is_the_newest_file_by_mtime(client, stores):
    committed = dict(report_fixture(), run=dict(report_fixture()["run"], domain="retail", commit="committed"))
    audited = dict(committed, run=dict(committed["run"], commit="audited"))
    (stores.reports / "retail.json").write_text(json.dumps(committed))
    (stores.cache / "retail-x1.json").write_text(json.dumps(audited))
    os.utime(stores.reports / "retail.json", (1_000_000, 1_000_000))
    os.utime(stores.cache / "retail-x1.json", (2_000_000, 2_000_000))
    assert client.get("/api/reports/latest", params={"domain": "retail"}).json() == audited
    os.utime(stores.reports / "retail.json", (3_000_000, 3_000_000))
    assert client.get("/api/reports/latest", params={"domain": "retail"}).json() == committed
    # An airline cache file never shadows retail, and the reverse.
    assert client.get("/api/reports/latest", params={"domain": "airline"}).json() == report_fixture()


def test_REQ_AP1_2_absent_hole_key_is_404(client):
    assert client.get("/api/holes/G2:NOSUCH", params={"domain": "airline"}).status_code == 404


# ---------- REQ-AP1-5 ----------

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
    assert r.json() == {"ratified": True, "amendment_id": "A1", "rule_ids": [RATIFIED_RULE["id"]]}
    stored = json.loads(no_store.read_text())
    assert stored["domain"] == "airline"
    assert len(stored["amendments"]) == 1
    a = stored["amendments"][0]
    assert a["id"] == "A1" and a["hole_key"] == HOP_KEY
    assert a["rule_patch"] == [RATIFIED_RULE]
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
    assert ids.count(RATIFIED_RULE["id"]) == 1


def test_REQ_AP1_4_ratified_returns_base_plus_patches_and_the_amendments(client, no_store):
    client.post(f"/api/holes/{HOP_KEY}/ratify", params={"domain": "airline"})
    body = client.get("/api/ratified", params={"domain": "airline"}).json()
    hand = load_ruleset("airline")
    assert body["domain"] == "airline"
    assert body["ruleset"]["tool_rules"] == hand["tool_rules"] + [RATIFIED_RULE]
    assert body["ruleset"]["forbidden_goals"] == hand["forbidden_goals"]
    [a] = body["amendments"]
    assert a["id"] == "A1" and a["hole_key"] == HOP_KEY and a["rule_patch"] == [RATIFIED_RULE]
    parse_iso(a["ratified_at"])


def test_REQ_AP1_4_hole_without_amendment_is_409_and_stores_nothing(client, no_store):
    r = client.post(f"/api/holes/{NO_AMEND_KEY}/ratify", params={"domain": "airline"})
    assert r.status_code == 409
    assert client.get("/api/ratified", params={"domain": "airline"}).json()["amendments"] == []


def test_REQ_AP1_4_ratify_unknown_hole_key_is_404(client, no_store):
    r = client.post("/api/holes/G2:NOSUCH/ratify", params={"domain": "airline"})
    assert r.status_code == 404
    assert not no_store.exists() or json.loads(no_store.read_text())["amendments"] == []


def test_REQ_AP1_4_ratified_store_module_matches_the_api(client, no_store):
    ratified = importlib.import_module("bylaw.ratified")
    assert ratified.load("airline")["amendments"] == []
    client.post(f"/api/holes/{HOP_KEY}/ratify", params={"domain": "airline"})
    assert [a["id"] for a in ratified.load("airline")["amendments"]] == ["A1"]
    eff = ratified.effective_ruleset("airline")
    assert eff == client.get("/api/ratified", params={"domain": "airline"}).json()["ruleset"]
    assert eff["tool_rules"][-1] == RATIFIED_RULE


# ---------- REQ-AP1-3 ----------

def test_REQ_AP1_3_offline_audit_streams_progress_and_becomes_latest(client, stores, offline_llm):
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
    saved = stores.cache / f"retail-{audit_id}.json"
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


def test_REQ_AP1_3_airline_latest_is_untouched_by_a_retail_audit(client, offline_llm):
    audit_id = client.post("/api/audits",
                           json={"domain": "retail", "use_llm": False, "budget": 10, "amend": False}).json()["id"]
    read_events(client, audit_id)
    wait_finished(client, audit_id)
    assert client.get("/api/reports/latest", params={"domain": "airline"}).json() == report_fixture()


@pytest.mark.live
def test_REQ_AP1_3_live_audit_marks_muse_phases(client):
    r = client.post("/api/audits", json={"domain": "airline", "use_llm": True, "budget": 40, "amend": False})
    events = read_events(client, r.json()["id"])
    assert events[-1]["phase"] == "done"
    assert any(e["muse"] for e in events)
    assert events[-1]["llm_calls"] > 0 and events[-1]["tokens"] > 0
