// Stand-in for the Bylaw API (contract C9) while AP1 is not merged: `E2E_MOCK=1 npx playwright test`.
// fixtures/airline.report.json is a real `python -m bylaw audit --domain airline --no-llm` report (EX1 branch);
// airline.policy.json is the tau2 policy text; airline.ratified.json carries the hand RuleSet.
// The report predates 01 v1.7, so adjudicate() applies the gold classification here, with the gold tasks named in
// docs/plan/decisions-2026-10-27-gold-adjudication.md. The amendments, backtests and bench below are hand-written
// placeholders, not engine output; money figures only ever come from the report itself.
import { readFileSync } from "node:fs";
import type { Page } from "@playwright/test";

const fx = (name: string) => JSON.parse(readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8"));

const allowance = "{'basic_economy': [0, 1, 2], 'economy': [1, 2, 3], 'business': [2, 3, 4]}[args['cabin']][{'regular': 0, 'silver': 1, 'gold': 2}[user['membership']]]";
const AMENDMENTS: Record<string, object> = {
  G5: {
    policy_text: "Placeholder: A cabin change recomputes the free bag allowance; bags above the new allowance are charged at 50 dollars each.",
    rule_patch: [{ id: "R-flights-bags-allowance", tool: "update_reservation_flights", allow_if: `res['total_baggages'] - res['nonfree_baggages'] <= ${allowance} * len(res['passengers'])`, policy_ref: "A cabin change recomputes the free bag allowance.", note: "" }],
    rationale: "Placeholder: Downgrading after bags were added keeps free bags the new cabin does not include.",
  },
  G1: {
    policy_text: "Placeholder: A cabin change does not unlock flight changes: a reservation booked in basic economy keeps that fare's rules.",
    rule_patch: [{ id: "R-flights-booked-basic", tool: "update_reservation_flights", allow_if: "res.get('booked_cabin', res['cabin']) != 'basic_economy' or args['flights'] == [{'flight_number': f['flight_number'], 'date': f['date']} for f in res['flights']]", policy_ref: "A cabin change does not unlock flight changes.", note: "" }],
    rationale: "Placeholder: Upgrading to economy, moving the flights and downgrading again modifies a basic economy itinerary.",
  },
  G2: {
    policy_text: "Placeholder: A business cancellation ground applies only to reservations booked in business; an upgrade refunds only the upgrade difference.",
    rule_patch: [{ id: "R-cancel-booked-business", tool: "cancel_reservation", allow_if: "res.get('booked_cabin', res['cabin']) == 'business' or hours_between(res['created_at'], now) <= 24 or res['insurance'] == 'yes'", policy_ref: "A business cancellation ground applies only to reservations booked in business.", note: "" }],
    rationale: "Placeholder: An upgrade to business followed by a cancellation refunds a non-refundable fare.",
  },
};

const GOLD: Record<string, string[]> = { G1: ["32"], G2: ["7"], G4: ["25"], G5: ["18"] };

export function adjudicate(report: any) {
  const gold = (h: any) => ({ ...h, gold: { sanctioned: h.goal in GOLD, tasks: GOLD[h.goal] ?? [] } });
  const found = report.holes.map(gold);
  report.holes = found.filter((h: any) => !h.gold.sanctioned).map((h: any, i: number) => ({ ...h, id: `H${i + 1}` }));
  report.contradictions = found.filter((h: any) => h.gold.sanctioned).map((h: any, i: number) => ({ ...h, class: "B", id: `B${i + 1}` }));
  report.ambiguities = report.ambiguities.map(gold);
  return report;
}

export function withAmendments(report: any) {
  let n = 0;
  for (const h of [...report.holes, ...report.contradictions]) {
    const a = AMENDMENTS[h.goal];
    if (!a) continue;
    h.amendment = { id: `A${++n}`, hole_id: h.id, ...a };
    // No closes/backtest: hand-written placeholders, so the UI shows "not backtested" (real ones come with DM1).
  }
  return report;
}

export const storedReport = () => withAmendments(adjudicate(fx("airline.report.json")));

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
  { phase: "verify", message: "15 findings replayed 5/5 · 0 class A, 15 class B (gold tasks 7, 18, 32)", muse: false },
  { phase: "done", message: "report stored as latest for airline", muse: false },
].map((e, i) => ({ ...e, tokens: 0, llm_calls: 0, tool_calls: Math.min(1486, 500 * i), holes: i >= 3 ? 15 : 0, t: [0.2, 1.1, 172.4, 174.1, 174.6][i] }));

const json = (body: unknown, status = 200) => ({ status, contentType: "application/json", body: JSON.stringify(body) });

// `partial` stops the event stream before `done`, to show a running audit. `stored: false` starts from the
// offline audit result (no amendments, C9 v1.2); place() then swaps in a stored report that carries them.
// A bench with one blind BFS row and `model: null` (01 v1.9): no Muse in it.
export const BFS_BENCH = { domain: "airline", budget: 2000, model: null, commit: "05bd65c", rows: [BENCH.rows[0]] };

// `fallback` serves the report as 01 v1.9 `bfs-fallback`: Muse requested, all 3 calls failed, model null.
// `fixture` serves that report file as it is, without adjudication; `edit` changes it; `bench` replaces the bench.
// CS-C3 v1.2 event files, built from the VZ1 spike transcripts until DM2 records real ones: fixtures/live/.
export const LIVE = ["csdemo-d1.json", "csdemo-d1-guard.json"];
const liveFx = (f: string) => fx(`live/${f}`);

// `live` lists the event files /api/live serves (default both fixtures); `liveEdit` changes one before it is served.
export async function mockApi(page: Page, { partial = false, stored = true, fallback = false, fixture = "", edit = (_: any) => {}, bench = BENCH as object, live = LIVE, liveEdit = (_file: string, _run: any) => {} } = {}) {
  let report = fixture ? fx(fixture) : stored ? storedReport() : adjudicate(fx("airline.report.json"));
  if (fallback) {
    report.run = { ...report.run, mode: "bfs-fallback", model: null };
    report.stats = { ...report.stats, llm_calls: 3, llm_errors: 3 };
  }
  edit(report);
  const ratified = fx("airline.ratified.json");
  const policy = fx("airline.policy.json");
  // csdemo policy and ratified store, from the API on bylaw/build (RA1, DM2), so its goals and lines resolve.
  const cs = { ratified: fx("csdemo.ratified.json"), policy: fx("csdemo.policy.json") };

  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const domain = url.searchParams.get("domain");
    const p = url.pathname;
    const hole = p.startsWith("/api/holes/") ? decodeURIComponent(p.split("/")[3]) : "";
    if (domain === "retail" && p !== "/api/audits") return route.fulfill(json({ detail: "no report for retail" }, 404));
    if (domain === "csdemo" && p === "/api/bench") return route.fulfill(json({ detail: "no bench for csdemo" }, 404));

    if (p === "/api/live") return route.fulfill(json(live.map((file) => ({ name: liveFx(file).name, guard: liveFx(file).guard, file }))));
    if (p.startsWith("/api/live/")) {
      const file = decodeURIComponent(p.slice("/api/live/".length));
      if (!live.includes(file)) return route.fulfill(json({ detail: `no live file ${file}` }, 404));
      const run = liveFx(file);
      liveEdit(file, run);
      return route.fulfill(json(run));
    }
    if (p === "/api/domains") return route.fulfill(json(["airline", "retail"]));
    if (p === "/api/policy") return route.fulfill(json(domain === "csdemo" ? cs.policy : policy));
    if (p === "/api/reports/latest") return route.fulfill(json(report));
    if (p === "/api/ratified") return route.fulfill(json(domain === "csdemo" ? cs.ratified : ratified));
    if (p === "/api/bench") return route.fulfill(json(bench));
    if (p === "/api/audits" && method === "POST") return route.fulfill(json({ id: "a1" }, 202));
    if (p === "/api/audits/a1") return route.fulfill(json({ id: "a1", domain: "airline", status: "done", report, error: null }));
    if (p === "/api/audits/a1/events") {
      const evs = partial ? EVENTS.slice(0, 3) : EVENTS;
      // retry: a closed stream must not reconnect during the test.
      return route.fulfill({ status: 200, contentType: "text/event-stream", body: "retry: 600000\n\n" + evs.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("") });
    }
    if (hole && p.endsWith("/ratify") && method === "POST") {
      const h = [...report.holes, ...report.contradictions].find((x: any) => x.key === hole);
      if (!h) return route.fulfill(json({ detail: "unknown hole" }, 404));
      if (!h.amendment) return route.fulfill(json({ detail: "no amendment" }, 409));
      // 03 v1.3: the store namespaces rule ids as <hole_key>/<rule_id>.
      const rule_patch = h.amendment.rule_patch.map((r: any) => ({ ...r, id: `${hole}/${r.id}` }));
      if (!ratified.amendments.some((a: any) => a.hole_key === hole))
        ratified.amendments.push({ ...h.amendment, rule_patch, hole_key: hole, ratified_at: "2026-10-27T09:12:00Z" });
      return route.fulfill(json({ ratified: true, amendment_id: h.amendment.id, rule_ids: rule_patch.map((r: any) => r.id) }));
    }
    if (hole) {
      const h = [...report.holes, ...report.contradictions, ...report.ambiguities].find((x: any) => x.key === hole);
      return route.fulfill(h ? json(h) : json({ detail: "not found" }, 404));
    }
    return route.fulfill(json({ detail: `mock has no ${method} ${p}` }, 404));
  });
  return { place: () => void (report = storedReport()) };
}
