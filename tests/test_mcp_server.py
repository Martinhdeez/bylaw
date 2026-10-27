"""PX1: `python -m bylaw proxy --domain airline` is an MCP stdio server over the proxy (REQ-PX1-1, REQ-PX1-2)."""
import sys
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from bylaw.domain import get_domain

ROOT = Path(__file__).resolve().parents[1]


async def _session(fn):
    params = StdioServerParameters(command=sys.executable, args=["-m", "bylaw", "proxy", "--domain", "airline"], cwd=ROOT)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as s:
        await s.initialize()
        return await fn(s)


def test_list_tools_and_a_rule_blocked_call_over_stdio():
    async def go(s):
        return (await s.list_tools()).tools, await s.call_tool(
            "cancel_reservation", {"reservation_id": "T1QOBS", "reason": "change of plan"})

    tools, blocked = anyio.run(_session, go)
    assert {t.name for t in tools} == {t["function"]["name"] for t in get_domain("airline").tools}
    assert "reservation_id" in next(t for t in tools if t.name == "cancel_reservation").input_schema["properties"]
    text = blocked.content[0].text
    assert text.startswith("BLOCKED R-cancel-ground: "), text
    assert len(text) > len("BLOCKED R-cancel-ground: ")  # names the policy line
