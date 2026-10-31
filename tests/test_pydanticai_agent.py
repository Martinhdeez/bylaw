"""PA1: a PydanticAI agent whose tools come only from `python -m bylaw proxy --domain csdemo` (MCP stdio).
A scripted stub model makes the calls; the committed ratified store decides them. Offline."""
import subprocess
from pathlib import Path

from mcp.client.stdio import get_default_environment
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from bylaw.pydanticai_agent import proxy_transport as transport, run

ROOT = Path(__file__).resolve().parents[1]

DISRUPTED = ("I flew Paris to New York and my delayed flight PA441 made me miss my connection to Austin. "
             "Can I get hotel and meal vouchers?")


def scripted(*calls):
    """A model that makes `calls` in order, one per request, then answers with text."""
    def fn(messages, info):
        made = sum(isinstance(p, ToolReturnPart) or p.part_kind == "retry-prompt"
                   for m in messages for p in m.parts)
        if made < len(calls):
            return ModelResponse(parts=[ToolCallPart(*calls[made])])
        return ModelResponse(parts=[TextPart("done")])
    return FunctionModel(fn)


def checks(out):
    return [(e["tool"], e["allowed"], e["rule_id"]) for e in out["events"] if e["type"] == "bylaw_check"]


def test_vouchers_on_the_on_time_booking_are_denied_by_the_ratified_d1_rule():
    model = scripted(("flight_status_tool", {"flight_number": "FLT-123"}),
                     ("issue_compensation", {"reason": "missed connection in New York"}))
    out = run({"name": "t", "turns": ["check FLT-123, then vouchers please"]}, model)
    assert checks(out) == [("flight_status_tool", True, None),
                           ("issue_compensation", False, "D1:LL0EZ6/R-comp-booking-disrupted")]
    denied = next(e for e in out["events"] if e["type"] == "tool_output" and e["tool"] == "issue_compensation")
    assert denied["output"].startswith("BLOCKED D1:LL0EZ6/R-comp-booking-disrupted: ")


def test_proxy_child_never_holds_the_model_key(tmp_path):
    """The proxy needs no key. bylaw.llm calls load_dotenv() at import, which reads the .env next to the package,
    so the agent's child env must pin MODEL_API_KEY empty. A placeholder .env, written here, plays the real one."""
    for d in ("bylaw", "targets"):
        (tmp_path / d).symlink_to(ROOT / d)
    (tmp_path / ".env").write_text("MODEL_API_KEY=placeholder-not-a-key\n")
    t = transport("csdemo", cwd=tmp_path)
    # What `python -m bylaw proxy --domain csdemo` imports and builds before serving, then the key it sees.
    probe = ("import os; import bylaw.__main__; from bylaw.domain import get_domain; from bylaw.proxy.core import Proxy; "
             f"Proxy(get_domain({t.args[-1]!r})); print(repr(os.environ.get('MODEL_API_KEY', '')))")
    env = get_default_environment() | {"PYTHONUTF8": "1", **(t.env or {})}  # as fastmcp and mcp spawn the child
    out = subprocess.run([t.command, "-c", probe], cwd=t.cwd, env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.strip().splitlines()[-1] == "''"


def test_vouchers_on_the_disrupted_booking_pass():
    model = scripted(("get_trip_details", {"message": DISRUPTED}),
                     ("issue_compensation", {"reason": "Delay causing missed connection - PA441 delayed 5 hours"}))
    out = run({"name": "t", "turns": [DISRUPTED]}, model)
    assert checks(out) == [("get_trip_details", True, None), ("issue_compensation", True, None)]
    paid = next(e for e in out["events"] if e["type"] == "tool_output" and e["tool"] == "issue_compensation")
    assert "compensation case" in paid["output"]
