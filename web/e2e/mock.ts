// Stand-in for the Bylaw API (contract C9) while AP1 is not merged: `E2E_MOCK=1 npx playwright test`.
// fixtures/airline.report.json is a real `python -m bylaw audit --domain airline --no-llm` report (EX1 branch);
// airline.policy.json is the tau2 policy text; airline.ratified.json carries the hand RuleSet.
// The amendments, backtests and bench below are hand-written placeholders, not engine output.
import { readFileSync } from "node:fs";
import type { Page } from "@playwright/test";

const fx = (name: string) => JSON.parse(readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8"));

const allowance = "{'basic_economy': [0, 1, 2], 'economy': [1, 2, 3], 'business': [2, 3, 4]}[args['cabin']][{'regular': 0, 'silver': 1, 'gold': 2}[user['membership']]]";
const AMENDMENTS: Record<string, object> = {
  G5: {
    policy_text: "A cabin change recomputes the free bag allowance; bags above the new allowance are charged at 50 dollars each.",
    rule_patch: [{ id: "R-flights-bags-allowance", tool: "update_reservation_flights", allow_if: `res['total_baggages'] - res['nonfree_baggages'] <= ${allowance} * len(res['passengers'])`, policy_ref: "A cabin change recomputes the free bag allowance.", note: "" }],
    rationale: "Downgrading after bags were added keeps free bags the new cabin does not include.",
  },
  G1: {
    policy_text: "A cabin change does not unlock flight changes: a reservation booked in basic economy keeps that fare's rules.",
    rule_patch: [{ id: "R-flights-booked-basic", tool: "update_reservation_flights", allow_if: "res.get('booked_cabin', res['cabin']) != 'basic_economy' or args['flights'] == [{'flight_number': f['flight_number'], 'date': f['date']} for f in res['flights']]", policy_ref: "A cabin change does not unlock flight changes.", note: "" }],
    rationale: "Upgrading to economy, moving the flights and downgrading again modifies a basic economy itinerary.",
  },
  G2: {
    policy_text: "A business cancellation ground applies only to reservations booked in business; an upgrade refunds only the upgrade difference.",
    rule_patch: [{ id: "R-cancel-booked-business", tool: "cancel_reservation", allow_if: "res.get('booked_cabin', res['cabin']) == 'business' or hours_between(res['created_at'], now) <= 24 or res['insurance'] == 'yes'", policy_ref: "A business cancellation ground applies only to reservations booked in business.", note: "" }],
    rationale: "An upgrade to business followed by a cancellation refunds a non-refundable fare.",
  },
};

export function withAmendments(report: any) {
  let n = 0;
  for (const h of report.holes) {
    const a = AMENDMENTS[h.goal];
    if (!a) continue;
    h.amendment = { id: `A${++n}`, hole_id: h.id, ...a };
    h.closes = true;
    h.backtest = { tasks: 43, blocked: 0, baseline_blocked: 0, blocked_tasks: [] };
  }
  return report;
}

const found = (calls: number[]) => calls.map((c, i) => ({ key: `H${i + 1}`, tool_calls: c, seconds: c / 8.5 }));
const BENCH = {
  domain: "airline",
  budget: 2000,
  rows: [
    { mode: "bfs", holes: 15, hole_keys: [], tool_calls: 1486, llm_calls: 0, tokens: 0, seconds: 174.5, found: found([212, 240, 266, 310, 402, 455, 517, 590, 688, 760, 881, 973, 1104, 1290, 1460]) },
    { mode: "muse", holes: 18, hole_keys: [], tool_calls: 1320, llm_calls: 14, tokens: 412880, seconds: 236.0, found: found([22, 31, 38, 47, 61, 75, 96, 118, 140, 171, 205, 260, 330, 410, 520, 690, 905, 1210]) },
  ],
};

export const EVENTS = [
  { phase: "search", message: "hand RuleSet, 28 tool rules · 7 forbidden goals", muse: false },
  { phase: "search", message: "bfs depth ≤ 4 · write tools only · budget 2000", muse: false },
  { phase: "search", message: "706 chains tried · 1486 tool calls", muse: false },
  { phase: "verify", message: "15 class A holes replayed 5/5", muse: false },
  { phase: "done", message: "report stored as latest for airline", muse: false },
].map((e, i) => ({ ...e, tokens: 0, llm_calls: 0, tool_calls: Math.min(1486, 500 * i), holes: i >= 3 ? 15 : 0, t: [0.2, 1.1, 172.4, 174.1, 174.6][i] }));

const json = (body: unknown, status = 200) => ({ status, contentType: "application/json", body: JSON.stringify(body) });

// `partial` stops the event stream before `done`, to show a running audit. `stored: false` starts from the
// offline audit result (no amendments, C9 v1.2); place() then swaps in a stored report that carries them.
export async function mockApi(page: Page, { partial = false, stored = true } = {}) {
  let report = stored ? withAmendments(fx("airline.report.json")) : fx("airline.report.json");
  const ratified = fx("airline.ratified.json");
  const policy = fx("airline.policy.json");

  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const domain = url.searchParams.get("domain");
    const p = url.pathname;
    const hole = p.startsWith("/api/holes/") ? decodeURIComponent(p.split("/")[3]) : "";
    if (domain === "retail" && p !== "/api/audits") return route.fulfill(json({ detail: "no report for retail" }, 404));

    if (p === "/api/domains") return route.fulfill(json(["airline", "retail"]));
    if (p === "/api/policy") return route.fulfill(json(policy));
    if (p === "/api/reports/latest") return route.fulfill(json(report));
    if (p === "/api/ratified") return route.fulfill(json(ratified));
    if (p === "/api/bench") return route.fulfill(json(BENCH));
    if (p === "/api/audits" && method === "POST") return route.fulfill(json({ id: "a1" }, 202));
    if (p === "/api/audits/a1") return route.fulfill(json({ id: "a1", domain: "airline", status: "done", report, error: null }));
    if (p === "/api/audits/a1/events") {
      const evs = partial ? EVENTS.slice(0, 3) : EVENTS;
      // retry: a closed stream must not reconnect during the test.
      return route.fulfill({ status: 200, contentType: "text/event-stream", body: "retry: 600000\n\n" + evs.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("") });
    }
    if (hole && p.endsWith("/ratify") && method === "POST") {
      const h = report.holes.find((x: any) => x.key === hole);
      if (!h) return route.fulfill(json({ detail: "unknown hole" }, 404));
      if (!h.amendment) return route.fulfill(json({ detail: "no amendment" }, 409));
      if (!ratified.amendments.some((a: any) => a.hole_key === hole))
        ratified.amendments.push({ ...h.amendment, hole_key: hole, ratified_at: "2026-10-27T09:12:00Z" });
      return route.fulfill(json({ ratified: true, amendment_id: h.amendment.id, rule_ids: h.amendment.rule_patch.map((r: any) => r.id) }));
    }
    if (hole) {
      const h = [...report.holes, ...report.ambiguities].find((x: any) => x.key === hole);
      return route.fulfill(h ? json(h) : json({ detail: "not found" }, 404));
    }
    return route.fulfill(json({ detail: `mock has no ${method} ${p}` }, 404));
  });
  return { place: () => void (report = withAmendments(fx("airline.report.json"))) };
}
