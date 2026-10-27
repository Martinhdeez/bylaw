"""HTTP API (contract C9): reports, background audits with SSE progress, ratify, bench, and the built web app.

Run: uv run uvicorn bylaw.api:app
"""
import json
import os
import threading
import time
import uuid
from functools import cache
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from bylaw import llm, ratified
from bylaw.domain import get_domain

ROOT = ratified.ROOT
WEB_DIST = ROOT / "web" / "dist"
HAND_RULESETS = Path(__file__).parent / "rulesets"
DOMAINS = ["airline", "retail"]
Domain = Literal["airline", "retail"]
TICK_S = 0.5  # minimum seconds between two search progress events

app = FastAPI(title="Bylaw")
JOBS: dict[str, "Job"] = {}  # ponytail: in memory, lost on restart; a store is needed only for multi-process serving


def reports_dir() -> Path:
    """Committed demo reports and bench (DM1). C9 v1.1: env read on every request, defaults from the repo root."""
    return ROOT / (os.environ.get("BYLAW_REPORTS_DIR") or "reports")


def cache_dir() -> Path:
    """Reports of audits run through the API."""
    return ROOT / (os.environ.get("BYLAW_CACHE_DIR") or ".cache/reports")


@cache
def domain_obj(name: str):
    return get_domain(name)


def _load(path: Path):
    return json.loads(path.read_text()) if path.is_file() else None


def latest_report(domain: str) -> dict | None:
    """The newest file by mtime among <reports>/<domain>.json and <cache>/<domain>-*.json."""
    files = [p for p in [reports_dir() / f"{domain}.json", *cache_dir().glob(f"{domain}-*.json")] if p.is_file()]
    return _load(max(files, key=lambda p: p.stat().st_mtime_ns)) if files else None


class AuditRequest(BaseModel):
    domain: Domain
    use_llm: bool = False
    budget: int = Field(2000, ge=1)
    amend: bool = False


class Job:
    def __init__(self, req: AuditRequest):
        self.id, self.req = uuid.uuid4().hex[:12], req
        self.status, self.report, self.error = "running", None, None
        self.events: list[dict] = []
        self.cond = threading.Condition()
        self.t0, self.tool_calls, self.holes, self.last_tick = time.monotonic(), 0, 0, 0.0
        # ponytail: llm.USAGE is process-global, so two audits running at once with Muse share their counters
        self.usage0 = dict(llm.USAGE)

    def emit(self, phase: str, message: str, muse: bool = False):
        u = llm.USAGE
        ev = {"phase": phase, "message": message, "muse": muse,
              "tokens": u["prompt_tokens"] + u["completion_tokens"] - self.usage0["prompt_tokens"] - self.usage0["completion_tokens"],
              "llm_calls": u["calls"] - self.usage0["calls"], "tool_calls": self.tool_calls, "holes": self.holes,
              "t": round(time.monotonic() - self.t0, 2)}
        with self.cond:
            self.events.append(ev)
            self.cond.notify_all()

    def view(self) -> dict:
        return {"id": self.id, "domain": self.req.domain, "status": self.status, "report": self.report, "error": self.error}


class _Counted:
    """The domain with every tool call counted (search and verifier replays), emitting throttled search progress."""

    def __init__(self, domain, job: Job, muse: bool):
        self._d, self._job, self._muse = domain, job, muse

    def __getattr__(self, name):
        return getattr(self._d, name)

    def call(self, env, tool, **args):
        j = self._job
        j.tool_calls += 1
        if time.monotonic() - j.last_tick >= TICK_S:
            j.last_tick = time.monotonic()
            j.emit("search", f"{j.tool_calls} tool calls executed", self._muse)
        return self._d.call(env, tool, **args)


def _amend(job: Job, domain, ruleset: dict, report: dict):
    """C7 per hole: draft (Muse), backtest against the unpatched baseline, closes = the hole's chain is now blocked."""
    try:
        from bylaw import amend
    except ImportError:
        return job.emit("amend", "amend skipped: bylaw.amend is not available")
    from bylaw.backtest import backtest
    from bylaw.executor import run

    base = backtest(domain, ruleset)
    for hole in report["holes"] + report.get("contradictions", []):  # C4 v1.7: Class B is amended too
        job.emit("amend", f"drafting the amendment for {hole['key']}", muse=True)
        am = amend.draft(domain, ruleset, hole)
        patched = amend.apply(ruleset, am)
        job.emit("backtest", f"backtesting {am['id']} on the gold tasks")
        bt = backtest(domain, patched)
        # ponytail: closes = this chain is blocked; C7's "re-audit finds 0 holes" lands with AM1's report helper
        r = run(domain, hole["chain"], patched)
        hole.update(amendment=am, closes=len(r["results"]) < len(hole["chain"]),
                    backtest={"tasks": bt["tasks"], "blocked": bt["blocked"], "baseline_blocked": base["blocked"],
                              "blocked_tasks": [x["id"] for x in bt["results"] if x["blocked"]]})


def _run(job: Job):
    from bylaw.report import audit

    req = job.req
    try:
        domain = domain_obj(req.domain)
        ruleset = json.loads((HAND_RULESETS / f"{req.domain}.json").read_text())
        job.emit("compile", f"hand RuleSet bylaw/rulesets/{req.domain}.json, {len(ruleset['tool_rules'])} rules")
        job.emit("search", f"searching with budget {req.budget}" + (" (Muse-guided)" if req.use_llm else " (blind BFS)"),
                 req.use_llm)
        report = audit(_Counted(domain, job, req.use_llm), ruleset, req.budget, use_llm=req.use_llm,
                       model=llm.model() if req.use_llm else "")
        job.holes = len(report["holes"])
        job.emit("verify", f"{job.holes} Class A holes, {len(report.get('contradictions', []))} contradictions and "
                           f"{len(report['ambiguities'])} ambiguities proven 5/5")
        if req.amend and not req.use_llm:
            job.emit("amend", "amend skipped: drafting needs Muse (use_llm=false)")
        elif req.amend:
            _amend(job, domain, ruleset, report)
        path = cache_dir() / f"{req.domain}-{job.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
        job.report, job.status = report, "done"
        job.emit("done", f"report stored as {path.name}")
    except Exception as e:  # any failure ends the stream with an error event instead of a silent thread death
        job.error, job.status = f"{type(e).__name__}: {e}", "error"
        job.emit("error", job.error)


@app.get("/api/domains")
def domains():
    return DOMAINS


@app.get("/api/policy")
def policy(domain: Domain):
    return {"domain": domain, "lines": domain_obj(domain).policy_text.splitlines()}


@app.get("/api/reports/latest")
def report_latest(domain: Domain):
    report = latest_report(domain)
    if report is None:
        raise HTTPException(404, f"no report for {domain}")
    return report


@app.post("/api/audits", status_code=202)
def start_audit(req: AuditRequest):
    job = Job(req)
    JOBS[job.id] = job
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return {"id": job.id}


def _job(audit_id: str) -> Job:
    if audit_id not in JOBS:
        raise HTTPException(404, f"no audit {audit_id}")
    return JOBS[audit_id]


@app.get("/api/audits/{audit_id}")
def audit_status(audit_id: str):
    return _job(audit_id).view()


@app.get("/api/audits/{audit_id}/events")
def audit_events(audit_id: str):
    job = _job(audit_id)

    def stream():
        i = 0
        while True:
            with job.cond:
                job.cond.wait_for(lambda: len(job.events) > i, timeout=15)
                new = job.events[i:]
            if not new:
                yield ": keepalive\n\n"
                continue
            for ev in new:
                yield f"data: {json.dumps(ev)}\n\n"
            i += len(new)
            if new[-1]["phase"] in ("done", "error"):
                return

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def _hole(domain: str, key: str) -> dict:
    report = latest_report(domain) or {}
    for h in report.get("holes", []) + report.get("contradictions", []) + report.get("ambiguities", []):  # A, B, C
        if h["key"] == key:
            return h
    raise HTTPException(404, f"no hole {key} in the latest {domain} report")


@app.get("/api/holes/{key}")
def hole(key: str, domain: Domain):
    return _hole(domain, key)


@app.post("/api/holes/{key}/ratify")
def ratify(key: str, domain: Domain):
    h = _hole(domain, key)
    if not h.get("amendment"):
        raise HTTPException(409, f"hole {key} has no amendment")
    try:
        entry = ratified.ratify(domain, h)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ratified": True, "amendment_id": entry["id"], "rule_ids": [r["id"] for r in entry["rule_patch"]]}


@app.get("/api/ratified")
def ratified_view(domain: Domain):
    store = ratified.load(domain)
    return {"domain": domain, "amendments": store["amendments"], "ruleset": ratified.effective_ruleset(domain, store)}


@app.get("/api/bench")
def bench(domain: Domain):
    data = _load(reports_dir() / f"{domain}.bench.json")
    if data is None:
        raise HTTPException(404, f"no bench for {domain}")
    return data


@app.get("/{path:path}", include_in_schema=False)
def web(path: str):
    """The built web app (web/dist): a file when it exists inside dist, else index.html."""
    dist = WEB_DIST.resolve()
    f = (dist / path).resolve()
    if path.startswith("api/"):
        raise HTTPException(404)
    if path and f.is_file() and f.is_relative_to(dist):
        return FileResponse(f)
    if (dist / "index.html").is_file():
        return FileResponse(dist / "index.html")
    raise HTTPException(404, "web/dist is not built (cd web && npm run build)")
