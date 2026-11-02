// Bylaw: the demo's agent list as upstream's server.py _build_agents_list() returns it for targets/cs_demo/airline.
// ponytail: static for the prototype; phase 2 serves it from the backend (see the VZ3 contract).
import type { Agent } from "./types";

const GUARDS = ["relevance_guardrail", "jailbreak_guardrail"];

export const AGENTS: Agent[] = [
  {
    name: "Triage Agent",
    description: "Delegates requests to the right specialist agent (flight info, booking, seats, FAQ, baggage, compensation).",
    handoffs: ["Flight Information Agent", "Booking and Cancellation Agent", "Seat and Special Services Agent", "FAQ Agent", "Refunds and Compensation Agent"],
    tools: ["get_trip_details"],
    input_guardrails: GUARDS,
  },
  {
    name: "FAQ Agent",
    description: "Answers common questions about policies, baggage, seats, and compensation.",
    handoffs: ["Triage Agent"],
    tools: ["faq_lookup_tool"],
    input_guardrails: GUARDS,
  },
  {
    name: "Seat and Special Services Agent",
    description: "Updates seats and handles medical or special service seating.",
    handoffs: ["Refunds and Compensation Agent", "Triage Agent"],
    tools: ["update_seat", "assign_special_service_seat", "display_seat_map"],
    input_guardrails: GUARDS,
  },
  {
    name: "Flight Information Agent",
    description: "Provides flight status, connection impact, and alternate options.",
    handoffs: ["Booking and Cancellation Agent", "Triage Agent"],
    tools: ["flight_status_tool", "get_matching_flights"],
    input_guardrails: GUARDS,
  },
  {
    name: "Booking and Cancellation Agent",
    description: "Handles new bookings, rebookings after delays, and cancellations.",
    handoffs: ["Seat and Special Services Agent", "Refunds and Compensation Agent", "Triage Agent"],
    tools: ["cancel_flight", "get_matching_flights", "book_new_flight"],
    input_guardrails: GUARDS,
  },
  {
    name: "Refunds and Compensation Agent",
    description: "Opens compensation cases and issues hotel/meal support after delays.",
    handoffs: ["FAQ Agent", "Triage Agent"],
    tools: ["issue_compensation", "faq_lookup_tool"],
    input_guardrails: GUARDS,
  },
];
