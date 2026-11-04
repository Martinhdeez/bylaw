"""RO1: BYLAW_READONLY=1 turns off every route that writes the ratified store or a report; reads and live keep working."""
import json

import pytest
from fastapi.testclient import TestClient

from bylaw import api
from tests.test_api import REPORT
from tests.test_lv1_live_session import Stub, stub  # noqa: F401 (fixture)

client = TestClient(api.app)
READONLY = {"detail": "read-only deployment"}


@pytest.fixture(autouse=True)
def stores(tmp_path, monkeypatch):
    for name in ("REPORTS", "CACHE"):
        (tmp_path / name).mkdir()
    monkeypatch.setenv("BYLAW_REPORTS_DIR", str(tmp_path / "REPORTS"))
    monkeypatch.setenv("BYLAW_CACHE_DIR", str(tmp_path / "CACHE"))
    monkeypatch.setenv("BYLAW_RATIFIED_DIR", str(tmp_path / "ratified"))
    monkeypatch.delenv("BYLAW_READONLY", raising=False)
    (tmp_path / "REPORTS" / "airline.json").write_text(json.dumps(REPORT))
    return tmp_path


def test_readonly_refuses_ratify_and_writes_no_store(stores, monkeypatch):
    monkeypatch.setenv("BYLAW_READONLY", "1")
    r = client.post("/api/holes/G1:T1QOBS/ratify", params={"domain": "airline"})
    assert (r.status_code, r.json()) == (403, READONLY)
    assert not (stores / "ratified").exists()
    assert client.get("/api/ratified", params={"domain": "airline"}).json()["amendments"] == []


def test_readonly_refuses_audits_and_writes_no_report(stores, monkeypatch):
    monkeypatch.setenv("BYLAW_READONLY", "1")
    jobs = dict(api.JOBS)
    r = client.post("/api/audits", json={"domain": "airline", "budget": 1})
    assert (r.status_code, r.json()) == (403, READONLY)
    assert api.JOBS == jobs and list((stores / "CACHE").iterdir()) == []


def test_readonly_keeps_reads_and_live_sessions(stores, monkeypatch, stub):  # noqa: F811
    monkeypatch.setenv("BYLAW_READONLY", "1")
    assert client.get("/api/config").json() == {"readonly": True}
    assert client.get("/api/reports/latest", params={"domain": "airline"}).json() == REPORT
    assert client.get("/api/holes/G1:T1QOBS", params={"domain": "airline"}).status_code == 200
    assert client.get("/api/ratified", params={"domain": "airline"}).status_code == 200
    assert client.get("/api/live").status_code == 200
    assert client.get("/api/live/status").status_code == 200
    stub.next = Stub([])
    r = client.post("/api/live/session", json={"guard": True})
    assert r.status_code == 201, r.text
    assert client.get(f"/api/live/session/{r.json()['session']}/export").status_code == 200
    assert not (stores / "ratified").exists() and list((stores / "CACHE").iterdir()) == []


def test_without_the_flag_ratify_still_writes_and_config_says_writable(stores):
    assert client.get("/api/config").json() == {"readonly": False}
    r = client.post("/api/holes/G1:T1QOBS/ratify", params={"domain": "airline"})
    assert r.status_code == 200 and r.json()["ratified"] is True
    assert (stores / "ratified" / "airline.json").is_file()
