"""LC1: --long-context prompt (REQ-LC1-1) and per-audit token counts (REQ-LC1-2)."""
import json
import threading
from types import SimpleNamespace

from bylaw import __main__ as cli
from bylaw import llm as muse
from bylaw.backtest import load_gold
from bylaw.domain import get_domain
from bylaw.env.tau2_airline import RULESET
from bylaw.report import audit

DOMAIN = get_domain("airline")
RULES = json.loads(RULESET.read_text())
NO_TEMPLATES = '{"templates": []}'


class Recorder:
    """Stands in for bylaw.llm.structured: records every request, proposes nothing."""

    def __init__(self):
        self.calls, self.lock = [], threading.Lock()

    def __call__(self, messages, schema, name, effort=None, **opts):
        with self.lock:
            self.calls.append(messages)
        return {"templates": []}


def _payloads(messages):
    out = []
    for m in messages:
        try:
            out.append(json.loads(m["content"]))
        except (json.JSONDecodeError, TypeError):
            out.append(m["content"])
    return out


def test_long_context_sends_the_whole_policy_every_tool_schema_and_the_gold_tasks_in_each_call():
    rec = Recorder()
    audit(DOMAIN, RULES, budget=2, use_llm=True, long_context=True, llm=rec)
    gold = load_gold(DOMAIN)
    assert gold and len(rec.calls) == len(DOMAIN.goals)  # one prompt per proposer call
    for messages in rec.calls:
        dicts = [p for p in _payloads(messages) if isinstance(p, dict)]
        assert any(p.get("policy") == DOMAIN.policy_text for p in dicts)  # untruncated
        assert any(p.get("tools") == DOMAIN.tools for p in dicts)  # read tools too, not only the write tools
        assert any(p.get("gold_tasks") == gold for p in dicts)
        assert json.loads(messages[-1]["content"])["goal"]["id"] in DOMAIN.goals  # the goal stays the last message


def test_without_long_context_the_gold_tasks_are_not_sent():
    rec = Recorder()
    audit(DOMAIN, RULES, budget=2, use_llm=True, llm=rec)
    assert rec.calls and not any("gold_tasks" in p for m in rec.calls for p in _payloads(m) if isinstance(p, dict))


def test_cli_audit_long_context_flag_reaches_the_audit(monkeypatch, tmp_path):
    seen = {}

    def fake_audit(domain, ruleset, budget, use_llm, **kw):
        seen.update(use_llm=use_llm, **kw)
        return {"holes": [], "ambiguities": [], "run": {"context_tokens": 0},
                "stats": {"chains_tried": 0, "tool_calls": 0, "llm_calls": 0, "tokens": 0, "seconds": 0}}

    monkeypatch.setattr("bylaw.report.audit", fake_audit)
    cli.main(["audit", "--domain", "airline", "--long-context", "-o", str(tmp_path / "r.json")])
    assert seen == {"use_llm": True, "long_context": True}


class SlowClient:
    """OpenAI-shaped fake. Every request waits until `parties` requests are in flight, so two audits overlap
    for certain. Prompt tokens depend on the audit's tag in the messages."""

    def __init__(self, parties, prompt_tokens):
        self.barrier, self.prompt_tokens = threading.Barrier(parties, timeout=60), prompt_tokens
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **body):
        tag = body["messages"][0]["content"]
        self.barrier.wait()
        usage = SimpleNamespace(prompt_tokens=self.prompt_tokens[tag], completion_tokens=20,
                                completion_tokens_details=SimpleNamespace(reasoning_tokens=0))
        msg = SimpleNamespace(content=NO_TEMPLATES)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")], usage=usage)


def test_two_concurrent_audits_each_report_their_own_tokens(monkeypatch, tmp_path):
    monkeypatch.setattr(muse, "CACHE_DIR", tmp_path)
    monkeypatch.setenv("BYLAW_NO_CACHE", "1")
    monkeypatch.setenv("MODEL", "muse-spark-1.3")
    n = len(DOMAIN.goals)
    monkeypatch.setattr(muse, "_client", SlowClient(2 * n, {"audit-a": 1000, "audit-b": 7}))

    def tagged(tag):  # the real client path (bylaw.llm.structured), with the audit named in the first message
        return lambda messages, schema, name, **kw: muse.structured(
            [{"role": "system", "content": tag}, *messages], schema, name, **kw)

    reports = {}

    def run(tag):
        reports[tag] = audit(DOMAIN, RULES, budget=2, use_llm=True, llm=tagged(tag))

    threads = [threading.Thread(target=run, args=(t,)) for t in ("audit-a", "audit-b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(120)
    a, b = reports["audit-a"], reports["audit-b"]
    assert a["stats"]["tokens"] == n * (1000 + 20)
    assert b["stats"]["tokens"] == n * (7 + 20)
    assert a["run"]["context_tokens"] == 1000 and b["run"]["context_tokens"] == 7
