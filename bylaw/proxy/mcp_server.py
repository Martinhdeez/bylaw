"""C11: MCP stdio server wrapping one Proxy session; the agent sees the tau2 tools, Bylaw sees every call."""
import json

import anyio
import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from bylaw.proxy.core import Proxy


def text(out: dict) -> str:
    if out["ok"]:
        return json.dumps(out["result"], default=str)
    return out["reason"] if out["blocked"] else f"Error: {out['reason']}"


def build(proxy: Proxy) -> Server:
    async def list_tools(ctx, params):
        return types.ListToolsResult(tools=[types.Tool(name=t["name"], description=t["description"],
                                                       inputSchema=t["input_schema"]) for t in proxy.tools()])

    async def call_tool(ctx, params):
        out = proxy.call(params.name, params.arguments or {})
        return types.CallToolResult(content=[types.TextContent(type="text", text=text(out))], isError=not out["ok"])

    return Server(f"bylaw-{proxy.domain.name}", on_list_tools=list_tools, on_call_tool=call_tool)


def serve(proxy: Proxy) -> None:
    server = build(proxy)

    async def main():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    anyio.run(main)
