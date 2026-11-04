"""Acceptance tests for TR1: GET /api/usage, written blind from docs/plan/06-showcase/tr1-contract.md v1.0.

Offline. Each test starts its own `uvicorn bylaw.api:app` subprocess through the LV1 `start` fixture, so the
process-wide live counters and the env (BYLAW_LIVE, BYLAW_REPORTS_DIR) never leak between tests (an in-process
TestClient would share them). The model is a local fake chat completions server on 127.0.0.1 reached through
MODEL_BASE_URL, reporting a fixed, distinct input and output usage per answer (VZ3-C6 counts "the model layer's
reported usage"); no key, no network.
"""
import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from conftest import ROOT
from test_06_lv1_live_session import MODEL, done_of, new_session, start, turn  # noqa: F401 (start is a fixture)

STAGES = {"compile", "audit", "amend", "bench", "live"}
X, Y = 1000, 300  # prompt and completion tokens every fake answer reports
PRICE = {"model": "muse-spark-1.3", "input_per_1m": 1.25, "output_per_1m": 4.25,
         "source": "https://dev.meta.ai/docs/pricing-rate-limits", "read": "2026-11-01"}

# A ledger exercising both cost rules. Costs worked out by hand:
#   e-total: only tokens, 31630 -> low 0.0395375 -> 0.0395, high 0.1344275 -> 0.1344
#   e-split: 100000 in, 20000 out -> 0.125 + 0.085 = 0.21 (low == high)
#   e-small: 3000 in, 1000 out -> 0.00375 + 0.00425 = 0.008 (low == high), calls null
LEDGER = {"entries": [
    {"id": "e-total", "stage": "audit", "label": "audit, total only", "source": "reports/csdemo.json",
     "calls": 4, "input_tokens": None, "output_tokens": None, "tokens": 31630, "seconds": 14.33},
    {"id": "e-split", "stage": "compile", "label": "compile, split known", "source": "reports/airline.json",
     "calls": 2, "input_tokens": 100000, "output_tokens": 20000, "tokens": 120000, "seconds": None},
    {"id": "e-small", "stage": "bench", "label": "bench, no calls", "source": "reports/retail.json",
     "calls": None, "input_tokens": 3000, "output_tokens": 1000, "tokens": 4000, "seconds": 1.5},
]}
COSTS = {"e-total": {"low": 0.0395, "high": 0.1344}, "e-split": {"low": 0.21, "high": 0.21},
         "e-small": {"low": 0.008, "high": 0.008}}
# 4 + 2 + 0 calls; 31630 + 120000 + 4000 tokens; low 0.2575(375), high 0.3524(275), the same whether the
# rounded or the raw entry costs are summed
TOTAL = {"calls": 6, "tokens": 155630, "cost_usd": {"low": 0.2575, "high": 0.3524}}
ZERO = {"calls": 0, "tokens": 0, "cost_usd": {"low": 0.0, "high": 0.0}}


class FakeMuse:
    """Chat completions on 127.0.0.1: guardrail requests (response_format) get a schema-filled pass, others a
    text answer that ends the turn. Every answer reports usage X prompt + Y completion tokens."""

    def __init__(self):
        self.requests, self.lock = [], threading.Lock()
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def send(self, obj, ctype="application/json"):
                out = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
                with fake.lock:
                    fake.requests.append(body)
                fmt = body.get("response_format")
                if fmt:
                    props = (fmt.get("json_schema") or {}).get("schema", {}).get("properties", {})
                    content = json.dumps({k: True if v.get("type") == "boolean" else "ok" for k, v in props.items()})
                else:
                    content = "Turn done."
                msg = {"role": "assistant", "content": content}
                base = {"id": "chatcmpl-fake", "created": 0, "model": body.get("model", MODEL)}
                usage = {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": X + Y}
                if not body.get("stream"):
                    return self.send(dict(base, object="chat.completion", usage=usage,
                                          choices=[{"index": 0, "message": msg, "finish_reason": "stop"}]))
                chunks = [{"choices": [{"index": 0, "delta": msg, "finish_reason": None}]},
                          {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
                          {"choices": [], "usage": usage}]
                data = "".join(f"data: {json.dumps(dict(base, object='chat.completion.chunk', **c))}\n\n"
                               for c in chunks) + "data: [DONE]\n\n"
                self.send(data.encode(), "text/event-stream")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


@pytest.fixture
def muse():
    m = FakeMuse()
    yield m
    m.server.shutdown()


def usage(c):
    r = c.get("/api/usage")
    assert r.status_code == 200, r.text
    return r.json()


def cost(i, o):
    return round(i * 1.25 / 1e6 + o * 4.25 / 1e6, 4)


def with_ledger(start, **env):
    (start.reports / "usage.json").write_text(json.dumps(LEDGER))
    return start(**env)


def approx_cost(c):
    return {"low": pytest.approx(c["low"], abs=1e-9), "high": pytest.approx(c["high"], abs=1e-9)}


COMMITTED = {"BYLAW_REPORTS_DIR": str(ROOT / "reports")}


# ---------- REQ-TR1-1 shape ----------

@pytest.mark.parametrize("env", [{}, {"BYLAW_READONLY": "1"}, {"BYLAW_LIVE": "0"}])
def test_REQ_TR1_1_usage_is_200_with_price_recorded_live(start, env):
    """REQ-TR1-1: 200 with price, recorded (entries, total) and live, shaped as the contract; also read-only."""
    u = usage(with_ledger(start, **env))
    assert set(u) == {"price", "recorded", "live"}
    assert set(u["price"]) == {"model", "input_per_1m", "output_per_1m", "source", "read"}
    assert set(u["recorded"]) == {"entries", "total"}
    assert len(u["recorded"]["entries"]) == 3
    for e in u["recorded"]["entries"]:
        assert set(e) == {"id", "stage", "label", "source", "calls", "input_tokens", "output_tokens", "tokens",
                          "seconds", "cost_usd"}
        assert set(e["cost_usd"]) == {"low", "high"}
    assert set(u["recorded"]["total"]) == {"calls", "tokens", "cost_usd"}
    assert set(u["recorded"]["total"]["cost_usd"]) == {"low", "high"}
    assert set(u["live"]) == {"enabled", "model", "sessions", "input_tokens", "output_tokens", "tokens_used",
                              "token_cap", "cost_usd"}


def test_REQ_TR1_1_entries_pass_through_the_ledger_fields(start):
    """REQ-TR1-1: every ledger field comes back unchanged, in order, plus the computed cost_usd."""
    got = usage(with_ledger(start))["recorded"]["entries"]
    assert [{k: v for k, v in e.items() if k != "cost_usd"} for e in got] == LEDGER["entries"]


# ---------- REQ-TR1-2 price ----------

def test_REQ_TR1_2_price_is_muse_spark_list_price(start):
    """REQ-TR1-2: input 1.25 and output 4.25 USD per 1M tokens, model muse-spark-1.3."""
    p = usage(start())["price"]
    assert p["input_per_1m"] == 1.25 and p["output_per_1m"] == 4.25 and p["model"] == "muse-spark-1.3"
    assert p == PRICE


# ---------- REQ-TR1-3 entry cost ----------

def test_REQ_TR1_3_entry_cost_follows_split_or_range_rule(start):
    """REQ-TR1-3: split known -> low == high; only total known -> tokens priced at the input and output rates."""
    got = {e["id"]: e["cost_usd"] for e in usage(with_ledger(start))["recorded"]["entries"]}
    assert got == {k: approx_cost(v) for k, v in COSTS.items()}


def test_REQ_TR1_3_committed_ledger_costs_follow_the_rule(start):
    """REQ-TR1-3: on the committed reports/usage.json, each entry's cost_usd is recomputed from its own fields."""
    entries = usage(start(**COMMITTED))["recorded"]["entries"]
    assert entries, "the committed ledger has no entries"
    for e in entries:
        i, o, t = e["input_tokens"], e["output_tokens"], e["tokens"]
        want = ({"low": cost(i, o), "high": cost(i, o)} if i is not None and o is not None
                else {"low": round(t * 1.25 / 1e6, 4), "high": round(t * 4.25 / 1e6, 4)})
        assert e["cost_usd"] == approx_cost(want), e


# ---------- REQ-TR1-4 total ----------

def test_REQ_TR1_4_total_sums_entries_null_calls_as_zero(start):
    """REQ-TR1-4: recorded.total is the sum of calls (null as 0), tokens, cost low and high."""
    total = usage(with_ledger(start))["recorded"]["total"]
    assert total["calls"] == TOTAL["calls"] and total["tokens"] == TOTAL["tokens"]
    assert total["cost_usd"] == approx_cost(TOTAL["cost_usd"])


def test_REQ_TR1_4_committed_total_sums_its_entries(start):
    """REQ-TR1-4: on the committed ledger too (one rounding step of slack per sum)."""
    rec = usage(start(**COMMITTED))["recorded"]
    es, total = rec["entries"], rec["total"]
    assert es
    assert total["calls"] == sum(e["calls"] or 0 for e in es)
    assert total["tokens"] == sum(e["tokens"] for e in es)
    for k in ("low", "high"):
        assert total["cost_usd"][k] == pytest.approx(sum(e["cost_usd"][k] for e in es), abs=len(es) * 5e-5 + 1e-9)


# ---------- REQ-TR1-5 live counters ----------

def test_REQ_TR1_5_live_counters_start_at_zero_and_match_status(start):
    """REQ-TR1-5: a fresh process has zero counters, equal to /api/live/status."""
    c = start()
    live, st = usage(c)["live"], c.get("/api/live/status").json()
    assert live == {"enabled": True, "model": MODEL, "sessions": 0, "input_tokens": 0, "output_tokens": 0,
                    "tokens_used": 0, "token_cap": 300000, "cost_usd": 0.0}
    assert {k: live[k] for k in st} == st


def test_REQ_TR1_5_one_live_turn_grows_input_and_output_by_reported_usage(start, muse):
    """REQ-TR1-5: after one turn, input grows by X per model call, output by Y, cost by the rule."""
    c = start()
    before = usage(c)["live"]
    sid = new_session(c, True)["session"]
    _, named = turn(c, sid, "Hi, I have a question about my flight.")
    done_of(named)
    n = len(muse.requests)
    assert n >= 1
    live, st = usage(c)["live"], c.get("/api/live/status").json()
    assert live["input_tokens"] - before["input_tokens"] == X * n
    assert live["output_tokens"] - before["output_tokens"] == Y * n
    assert live["tokens_used"] == live["input_tokens"] + live["output_tokens"] == st["tokens_used"]
    assert live["cost_usd"] == pytest.approx(cost(live["input_tokens"], live["output_tokens"]), abs=1e-9)
    assert live["sessions"] == st["sessions"] == 1
    for k in ("enabled", "model", "token_cap"):
        assert live[k] == st[k], k


def test_REQ_TR1_5_token_cap_matches_status(start):
    """REQ-TR1-5: token_cap is the same as /api/live/status under BYLAW_LIVE_TOKEN_CAP."""
    c = start(BYLAW_LIVE_TOKEN_CAP="1234")
    assert usage(c)["live"]["token_cap"] == c.get("/api/live/status").json()["token_cap"] == 1234


# ---------- REQ-TR1-6 live disabled ----------

def test_REQ_TR1_6_live_disabled_is_200_with_enabled_false(start):
    """REQ-TR1-6: BYLAW_LIVE=0 -> 200, live.enabled false, the recorded side still served."""
    u = usage(with_ledger(start, BYLAW_LIVE="0"))
    assert u["live"]["enabled"] is False
    assert u["price"] == PRICE and u["recorded"]["total"]["tokens"] == TOTAL["tokens"]


# ---------- REQ-TR1-7 missing ledger ----------

def test_REQ_TR1_7_missing_ledger_is_empty_with_zero_totals(start):
    """REQ-TR1-7: BYLAW_REPORTS_DIR without usage.json -> entries [] and every total 0."""
    assert not (start.reports / "usage.json").exists()
    assert usage(start())["recorded"] == {"entries": [], "total": ZERO}


# ---------- REQ-TR1-8 committed ledger ----------

def test_REQ_TR1_8_committed_ledger_sources_ids_stages():
    """REQ-TR1-8: committed reports/usage.json: sources exist in the repo, ids unique, stages allowed."""
    doc = json.loads((ROOT / "reports" / "usage.json").read_text())
    es = doc["entries"]
    assert es
    ids = [e["id"] for e in es]
    assert len(ids) == len(set(ids)), ids
    for e in es:
        assert e["stage"] in STAGES, e
        src = Path(e["source"])
        assert not src.is_absolute() and ".." not in src.parts, e
        assert (ROOT / src).is_file(), e
        assert subprocess.run(["git", "ls-files", "--error-unmatch", str(src)], cwd=ROOT,
                              capture_output=True).returncode == 0, ("source is not committed", e)
        assert isinstance(e["tokens"], int), e
