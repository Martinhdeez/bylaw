"""PA1: a PydanticAI agent whose tools come only from `python -m bylaw proxy --domain csdemo` (MCP stdio).
A scripted stub model makes the calls; the committed ratified store decides them. Offline."""
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from bylaw.pydanticai_agent import run

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


def test_vouchers_on_the_disrupted_booking_pass():
    model = scripted(("get_trip_details", {"message": DISRUPTED}),
                     ("issue_compensation", {"reason": "Delay causing missed connection - PA441 delayed 5 hours"}))
    out = run({"name": "t", "turns": [DISRUPTED]}, model)
    assert checks(out) == [("get_trip_details", True, None), ("issue_compensation", True, None)]
    paid = next(e for e in out["events"] if e["type"] == "tool_output" and e["tool"] == "issue_compensation")
    assert "compensation case" in paid["output"]
