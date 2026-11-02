"""PA1: a PydanticAI agent whose only tools are Bylaw's MCP stdio proxy (`python -m bylaw proxy`), Muse as its model.

The proxy enforces the effective RuleSet (hand rules plus the ratified store) unchanged; this module only wires it.
`python -m bylaw.pydanticai_agent --script FILE -o OUT` writes an event file in the CS-C3 shape.
"""
import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from fastmcp.client.transports import StdioTransport
from pydantic_ai import Agent
from pydantic_ai.exceptions import ToolFailed
from pydantic_ai.mcp import MCPToolset

from bylaw import llm

ROOT = Path(__file__).resolve().parents[1]
INSTRUCTIONS = ("You are an airline customer service agent. Help the customer with the tools you have. "
                "If a tool refuses an action, tell the customer and do not retry it.")


def muse_model():
    """Muse through PydanticAI's OpenAI-compatible Chat Completions model, with the Bylaw client settings."""
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    sync = llm.client()  # MODEL_BASE_URL and MODEL_API_KEY, loaded from .env by bylaw.llm
    return OpenAIChatModel(llm.model(), provider=OpenAIProvider(base_url=str(sync.base_url), api_key=sync.api_key))


def proxy_transport(domain: str, cwd: Path = ROOT) -> StdioTransport:
    """`python -m bylaw proxy --domain <domain>` as an MCP stdio server."""
    # The child gets a sanitized env plus the BYLAW_* settings (e.g. BYLAW_RATIFIED_DIR). The proxy imports bylaw.llm,
    # whose load_dotenv() would read the key from .env; an empty MODEL_API_KEY wins, as load_dotenv does not override.
    env = {k: v for k, v in os.environ.items() if k.startswith("BYLAW_")} | {"MODEL_API_KEY": ""}
    return StdioTransport(command=sys.executable, args=["-m", "bylaw", "proxy", "--domain", domain], env=env, cwd=str(cwd))


async def _run(script: dict, model, domain: str) -> dict:
    t0, events = time.monotonic(), []

    def emit(kind, **kw):
        events.append({"t": round(time.monotonic() - t0, 3), "type": kind, **kw})

    async def record(ctx, call_tool, name, args):
        emit("tool_call", agent="pydantic-ai", tool=name, args=args)
        try:
            result = await call_tool(name, args)
        except ToolFailed as e:  # isError from the proxy: a Bylaw denial ("BLOCKED <id>: ...") or a tool error
            text = e.message
            denied = text.startswith("BLOCKED ")
            emit("bylaw_check", tool=name, allowed=not denied, enforced=True,
                 rule_id=text[8:].split(": ", 1)[0] if denied else None,
                 policy_ref=text.split(": ", 1)[1] if denied else None)
            emit("tool_output", tool=name, output=text)
            raise
        emit("bylaw_check", tool=name, allowed=True, rule_id=None, policy_ref=None, enforced=True)
        emit("tool_output", tool=name, output=str(result))
        return result

    proxy = MCPToolset(proxy_transport(domain), tool_error_behavior="failed", process_tool_call=record)
    agent = Agent(model, instructions=INSTRUCTIONS, toolsets=[proxy],
                  model_settings={"openai_reasoning_effort": "low"})
    out = {"name": script["name"], "guard": True, "framework": "pydantic-ai", "model": model.model_name,
           "started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "events": events}
    history, usage = [], {"requests": 0, "input_tokens": 0, "output_tokens": 0}
    async with proxy:  # one proxy process, hence one session, for the whole conversation
        for text in script["turns"]:
            emit("user", text=text)
            r = await agent.run(text, message_history=history)
            emit("agent_message", agent="pydantic-ai", text=r.output)
            history = r.all_messages()
            u = r.usage
            for k in usage:
                usage[k] += getattr(u, k) or 0
    out["usage"] = usage
    out["final_state"] = None  # the session lives in the proxy process
    return out


def run(script: dict, model, domain: str = "csdemo") -> dict:
    return asyncio.run(_run(script, model, domain))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="play a script through a PydanticAI agent guarded by the bylaw MCP proxy")
    p.add_argument("--script", required=True)
    p.add_argument("--domain", default="csdemo")
    p.add_argument("-o", "--output", required=True)
    a = p.parse_args()
    script = json.loads(Path(a.script).read_text())
    script["name"] = "pa1-" + script["name"].removeprefix("dm3-")
    Path(a.output).write_text(json.dumps(run(script, muse_model(), a.domain), indent=2, default=str) + "\n")
