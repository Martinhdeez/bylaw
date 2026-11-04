"""TR1: GET /api/usage (cost rule, totals, live split) and the committed usage ledger (scripts/usage_ledger.py)."""
import asyncio
import json
import runpy
import types

import pytest
from fastapi.testclient import TestClient

from bylaw import api, live

LEDGER = live.ROOT / "reports/usage.json"


@pytest.fixture
def client():
    with TestClient(api.app) as c:
        yield c


def test_cost_rule_and_totals_from_a_ledger(client, tmp_path, monkeypatch):
    entries = [  # split: 1e6 in + 1e6 out = 1.25 + 4.25; lump: 1e6 tokens = 1.25 .. 4.25
        {"id": "a", "stage": "amend", "label": "a", "source": "x", "calls": 2, "input_tokens": 1_000_000,
         "output_tokens": 1_000_000, "tokens": 2_000_000, "seconds": None},
        {"id": "b", "stage": "audit", "label": "b", "source": "x", "calls": None, "input_tokens": None,
         "output_tokens": None, "tokens": 1_000_000, "seconds": 1.5},
    ]
    (tmp_path / "usage.json").write_text(json.dumps({"entries": entries}))
    monkeypatch.setenv("BYLAW_REPORTS_DIR", str(tmp_path))
    rec = client.get("/api/usage").json()["recorded"]
    assert [e["cost_usd"] for e in rec["entries"]] == [{"low": 5.5, "high": 5.5}, {"low": 1.25, "high": 4.25}]
    assert rec["total"] == {"calls": 2, "tokens": 3_000_000, "cost_usd": {"low": 6.75, "high": 9.75}}


def test_no_ledger_means_empty_record(client, tmp_path, monkeypatch):
    monkeypatch.setenv("BYLAW_REPORTS_DIR", str(tmp_path))
    monkeypatch.setenv("BYLAW_LIVE", "0")
    r = client.get("/api/usage")
    assert r.status_code == 200
    body = r.json()
    assert body["recorded"] == {"entries": [], "total": {"calls": 0, "tokens": 0, "cost_usd": {"low": 0.0, "high": 0.0}}}
    assert body["live"]["enabled"] is False
    assert body["price"]["input_per_1m"] == 1.25 and body["price"]["output_per_1m"] == 4.25


def test_live_counter_splits_input_and_output(client, monkeypatch):
    for k in ("tokens", "input_tokens", "output_tokens"):
        monkeypatch.setitem(live.USAGE, k, 0)
    usage = types.SimpleNamespace(input_tokens=400_000, output_tokens=200_000)

    class Inner:
        async def get_response(self, *a, **kw):
            return types.SimpleNamespace(usage=usage)

    asyncio.run(live.Counted(Inner()).get_response())
    u = client.get("/api/usage").json()["live"]
    assert (u["input_tokens"], u["output_tokens"], u["tokens_used"]) == (400_000, 200_000, 600_000)
    assert u["cost_usd"] == 1.35  # 0.4 * 1.25 + 0.2 * 4.25
    assert client.get("/api/live/status").json()["tokens_used"] == 600_000


def test_committed_ledger_matches_its_sources():
    """Fails when a source file changes and reports/usage.json was not regenerated."""
    built = runpy.run_path(str(live.ROOT / "scripts/usage_ledger.py"))["build"]()
    assert json.loads(LEDGER.read_text()) == built


def test_ledger_figures():
    e = {x["id"]: x for x in json.loads(LEDGER.read_text())["entries"]}
    # figures as read by hand from reports/live/dm3-summary.md and reports/csdemo.json
    assert (e["dm3-runs"]["calls"], e["dm3-runs"]["input_tokens"], e["dm3-runs"]["output_tokens"]) == (175, 198042, 54093)
    assert (e["dm5-amend"]["calls"], e["dm5-amend"]["input_tokens"], e["dm5-amend"]["output_tokens"]) == (4, 23044, 43135)
    assert (e["csdemo-audit"]["calls"], e["csdemo-audit"]["tokens"], e["csdemo-audit"]["seconds"]) == (4, 31630, 14.33)
    assert sum(x["tokens"] for x in e.values()) == 704032  # VD4 total 629630 + airline audit - LV1 - VD4 live
    stages = {"compile", "audit", "amend", "bench", "live"}
    assert all(x["stage"] in stages and (live.ROOT / x["source"]).is_file() for x in e.values())
