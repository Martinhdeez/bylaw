from types import SimpleNamespace

import pytest

from bylaw import llm


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.bodies = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **body):
        self.bodies.append(body)
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=20,
                                completion_tokens_details=SimpleNamespace(reasoning_tokens=15))
        msg = SimpleNamespace(content=self.replies.pop(0))
        return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")], usage=usage)


@pytest.fixture
def fake(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
    monkeypatch.delenv("BYLAW_NO_CACHE", raising=False)
    monkeypatch.setenv("MODEL", "muse-spark-1.3")

    def make(*replies):
        c = FakeClient(replies)
        monkeypatch.setattr(llm, "_client", c)
        return c
    return make


MSG = [{"role": "user", "content": "hi"}]


def test_capability_degradation(fake, monkeypatch):
    c = fake("a", '{"x": 1}')
    monkeypatch.setenv("MODEL", "some-other-model")
    monkeypatch.setitem(llm.CAPS, "some-other-model", dict(llm.DEFAULT_CAPS, json_schema=False))
    assert llm.complete(MSG, effort="high", max_tokens=100) == "a"
    assert "reasoning_effort" not in c.bodies[0]
    assert llm.structured(MSG, {"type": "object"}, "t") == {"x": 1}
    assert c.bodies[1]["response_format"] == {"type": "json_object"}


def test_spark_gets_effort_and_min_tokens(fake):
    c = fake("a")
    llm.complete(MSG, effort="high", max_tokens=100)
    assert c.bodies[0]["reasoning_effort"] == "high"
    assert c.bodies[0]["max_tokens"] == 2000


def test_cache_hit(fake):
    c = fake("first")
    hits = llm.USAGE["cache_hits"]
    assert llm.complete(MSG) == "first"
    assert llm.complete(MSG) == "first"
    assert len(c.bodies) == 1 and llm.USAGE["cache_hits"] == hits + 1


def test_no_cache_env(fake, monkeypatch):
    monkeypatch.setenv("BYLAW_NO_CACHE", "1")
    c = fake("a", "b")
    assert llm.complete(MSG) == "a"
    assert llm.complete(MSG) == "b"
    assert len(c.bodies) == 2


def test_retry_on_bad_json(fake):
    c = fake("not json", '{"ok": true}')
    calls = llm.USAGE["calls"]
    assert llm.structured(MSG, {"type": "object"}, "t") == {"ok": True}
    assert len(c.bodies) == 2 and llm.USAGE["calls"] == calls + 2
    assert c.bodies[0]["response_format"]["type"] == "json_schema"
    assert llm.structured(MSG, {"type": "object"}, "t") == {"ok": True}  # good reply was cached


@pytest.mark.live
def test_live_structured(monkeypatch):
    monkeypatch.setenv("BYLAW_NO_CACHE", "1")
    schema = {"type": "object", "properties": {"forbidden": {"type": "array", "items": {"type": "string"}}},
              "required": ["forbidden"], "additionalProperties": False}
    out = llm.structured([{"role": "user", "content": "List 2 forbidden outcomes from: 'Basic economy cannot be "
                           "modified. Insurance cannot be added after booking.'"}], schema, "goals")
    assert isinstance(out["forbidden"], list) and out["forbidden"]
