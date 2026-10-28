import importlib
import socket
import sys

from agents import Agent

EXPECTED = {
    "Triage Agent": {"get_trip_details"},
    "Flight Information Agent": {"flight_status_tool", "get_matching_flights"},
    "Booking and Cancellation Agent": {"cancel_flight", "get_matching_flights", "book_new_flight"},
    "Seat and Special Services Agent": {"update_seat", "assign_special_service_seat", "display_seat_map"},
    "Refunds and Compensation Agent": {"issue_compensation", "faq_lookup_tool"},
    "FAQ Agent": {"faq_lookup_tool"},
}


def test_import_is_offline_and_lists_six_agents(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("network call during import")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    for name in [m for m in sys.modules if m.startswith("targets.cs_demo")]:
        monkeypatch.delitem(sys.modules, name)

    agents = importlib.import_module("targets.cs_demo.airline.agents")

    found = {
        a.name: {t.name for t in a.tools}
        for a in vars(agents).values()
        if isinstance(a, Agent)
    }
    assert found == EXPECTED
