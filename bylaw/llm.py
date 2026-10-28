"""Provider-agnostic OpenAI-compatible LLM client (Muse Spark by default).

Config (env / .env): MODEL_BASE_URL (or BASE_URL), MODEL, MODEL_API_KEY.
BYLAW_NO_CACHE=1 bypasses the on-disk cache in .cache/llm/.
BYLAW_EFFORT (e.g. low) overrides the reasoning effort every caller asks for.
"""
import contextvars
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MODEL = "muse-spark-1.3"
CACHE_DIR = Path(".cache/llm")

_SPARK = dict(reasoning_effort=True, json_schema=True, video_input=False, context_tokens=1_000_000, min_max_tokens=2000)
CAPS = {
    "muse-spark-1.3": _SPARK,
    "muse-spark-1.2": _SPARK,
    "muse-spark-1.1": _SPARK,
}
# Unknown models (other providers, future Muse versions): plain chat, strict schema assumed.
DEFAULT_CAPS = dict(reasoning_effort=False, json_schema=True, video_input=False, context_tokens=128_000, min_max_tokens=0)

USAGE = {"calls": 0, "cache_hits": 0, "prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0, "latency_s": 0.0}
CALLS = []  # per-call records: model, tokens, latency
# The calls of one audit: a list set by the caller around its requests; contextvars keep threads apart.
TALLY: contextvars.ContextVar[list | None] = contextvars.ContextVar("bylaw_llm_tally", default=None)

_client = None


def model():
    return os.environ.get("MODEL") or DEFAULT_MODEL


def effective_effort(requested=None):
    return os.environ.get("BYLAW_EFFORT") or requested


def caps(name=None):
    return CAPS.get(name or model(), DEFAULT_CAPS)


def client():
    global _client
    if _client is None:
        key = os.environ.get("MODEL_API_KEY")
        if not key:
            raise RuntimeError("MODEL_API_KEY is not set (put it in .env)")
        base = os.environ.get("MODEL_BASE_URL") or os.environ.get("BASE_URL") or DEFAULT_BASE_URL
        _client = OpenAI(base_url=base, api_key=key, timeout=300)
    return _client


def _cache_path(payload):
    h = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return CACHE_DIR / f"{h}.json"


def _call(messages, response_format=None, effort=None, read_cache=True, **opts):
    name = opts.pop("model", None) or model()
    cap = caps(name)
    effort = effective_effort(effort)  # part of the body, hence of the cache key
    body ={"model": name, "messages": messages, **opts}
    body["max_tokens"] = max(opts.get("max_tokens", 4000), cap["min_max_tokens"])
    if effort and cap["reasoning_effort"]:
        body["reasoning_effort"] = effort
    if response_format:
        body["response_format"] = response_format

    use_cache = os.environ.get("BYLAW_NO_CACHE") != "1"
    path = _cache_path(body)
    if use_cache and read_cache and path.exists():
        USAGE["cache_hits"] += 1
        return json.loads(path.read_text())["content"]

    t = time.time()
    resp = client().chat.completions.create(**body)
    dt = time.time() - t
    choice = resp.choices[0]
    content = choice.message.content or ""
    u = resp.usage
    details = getattr(u, "completion_tokens_details", None) if u else None
    rec = {
        "model": name,
        "prompt_tokens": getattr(u, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(u, "completion_tokens", 0) or 0,
        "reasoning_tokens": getattr(details, "reasoning_tokens", 0) or 0,
        "latency_s": round(dt, 2),
    }
    CALLS.append(rec)
    if (tally := TALLY.get()) is not None:
        tally.append(rec)
    USAGE["calls"] += 1
    for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "latency_s"):
        USAGE[k] += rec[k]
    if not content:
        raise RuntimeError(f"empty reply from {name} (finish_reason={choice.finish_reason}); raise max_tokens")
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"content": content}))
    return content


def complete(messages, effort=None, **opts) -> str:
    return _call(messages, effort=effort, **opts)


def structured(messages, schema: dict, name: str, effort=None, **opts) -> dict:
    if caps(opts.get("model"))["json_schema"]:
        fmt = {"type": "json_schema", "json_schema": {"name": name, "schema": schema, "strict": True}}
    else:
        fmt = {"type": "json_object"}
        messages = [{"role": "system", "content": "Reply with JSON only, matching this schema:\n" + json.dumps(schema)}, *messages]
    text = _call(messages, response_format=fmt, effort=effort, **opts)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Retry once, skipping (and overwriting) the cached bad reply.
        return json.loads(_call(messages, response_format=fmt, effort=effort, read_cache=False, **opts))


def _ping():
    try:
        reply = _call([{"role": "user", "content": "Say hello in 3 words."}], read_cache=False)
    except Exception as e:
        print(f"ping failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    rec = CALLS[-1]
    print(f"model={rec['model']} latency={rec['latency_s']}s tokens in={rec['prompt_tokens']} "
          f"out={rec['completion_tokens']} reasoning={rec['reasoning_tokens']}")
    print(f"reply: {reply}")
    return 0


if __name__ == "__main__":
    if "--ping" not in sys.argv:
        sys.exit("usage: python -m bylaw.llm --ping")
    sys.exit(_ping())
