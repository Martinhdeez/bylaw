// Prototype fixtures. Report, Hole and Step follow contract C4 (docs/plan/01-engine/contracts.md).
// Goal follows C2 forbidden_goals. Amendment and Bench are UI-side shapes until M2 freezes them.

export type Verdict = { rule_id: string; ok: boolean; policy_ref: string };
export type Step = { tool: string; args: Record<string, unknown>; ok: boolean; verdicts: Verdict[] };
export type Hole = {
  id: string;
  class: "A" | "C";
  goal: string;
  title: string;
  money_delta: number;
  chain: Step[];
  diff: Record<string, Record<string, [unknown, unknown]>>;
  goal_true: boolean;
  replays: string;
};
export type Report = {
  run: { commit: string; domain: string; model: string; mode: "bfs" | "muse"; started: string; budget: number; goals_commit: string };
  holes: Hole[];
  ambiguities: Hole[];
  stats: { chains_tried: number; tool_calls: number; llm_calls: number; tokens: number; seconds: number };
};
export type Goal = { id: string; name: string; policy_ref: string; description: string; predicate: string };
export type Amendment = {
  hole: string;
  section: string;
  context: string[];
  removed: string[];
  added: string[];
  rule: { id: string; tool: string; allow_if: string; policy_ref: string };
  backtest: { cases: number; blocked: number; blocked_cases: string[]; hole_closed: string; tokens: number };
  proxy_blocked_example: string;
};
export type BenchRow = { mode: "muse" | "bfs"; holes: number; tool_calls: number; llm_calls: number; seconds: number; found_at: { hole: string; call: number }[] };

const p = {
  beNoModify: "Basic economy flights cannot be modified.",
  cabinFlown: "Cabin cannot be changed if any flight in the reservation has already been flown.",
  cabinSame: "Cabin class must remain the same across all the flights in the same reservation; changing cabin for just one flight segment is not possible.",
  payProfile: "The payment method must already be in user profile for safety reasons.",
  cancelGrounds: "Otherwise, flight can be cancelled if any of the following is true: … It is a business flight",
  bagsAdd: "The user can add but not remove checked bags.",
  noInsurance: "The user cannot add insurance after initial booking.",
  paxCount: "The user can modify passengers but cannot modify the number of passengers.",
  within24: "The booking was made within the last 24 hrs",
  beBags: "0 free checked bag for each basic economy passenger",
};

const flightsRules = (ok = true): Verdict[] => [
  { rule_id: "R-flights-1", ok, policy_ref: p.beNoModify },
  { rule_id: "R-cabin-1", ok: true, policy_ref: p.cabinFlown },
  { rule_id: "R-cabin-2", ok: true, policy_ref: p.cabinSame },
  { rule_id: "R-pay-1", ok: true, policy_ref: p.payProfile },
];

export const GOALS: Record<string, Goal> = {
  G1: {
    id: "G1",
    name: "basic_economy_flights_changed",
    policy_ref: p.beNoModify,
    description: "A reservation booked in basic economy ends on different flights.",
    predicate: 'before.res.cabin == "basic_economy"\nand after.res.flights != before.res.flights',
  },
  G2: {
    id: "G2",
    name: "non_refundable_fare_refunded",
    policy_ref: "Otherwise, flight can be cancelled if any of the following is true: …",
    description: "An uninsured basic economy fare, booked over 24h ago, is refunded in full.",
    predicate: 'before.res.cabin == "basic_economy"\nand before.res.insurance == "no"\nand hours_between(before.res.created_at, now) > 24\nand refunded(chain) > charged(chain)',
  },
  G3: { id: "G3", name: "insurance_added_after_booking", policy_ref: p.noInsurance, description: "", predicate: 'before.res.insurance == "no" and after.res.insurance == "yes"' },
  G4: { id: "G4", name: "passenger_count_changed", policy_ref: p.paxCount, description: "", predicate: "len(after.res.passengers) != len(before.res.passengers)" },
  G5: {
    id: "G5",
    name: "free_bags_exceed_allowance",
    policy_ref: p.beBags,
    description: "A reservation keeps more free bags than its final cabin and tier allow.",
    predicate: "free = after.res.total_baggages - after.res.nonfree_baggages\nfree > allowance(after.res.cabin, user.membership) * len(after.res.passengers)",
  },
};

export const AIRLINE: Report = {
  run: { commit: "6dbd9e7", domain: "airline", model: "muse-spark", mode: "muse", started: "2026-10-26T21:14:08Z", budget: 2000, goals_commit: "6dbd9e7" },
  holes: [
    {
      id: "H1",
      class: "A",
      goal: "G1",
      title: "Basic economy flights changed by cabin hop",
      money_delta: 0,
      chain: [
        { tool: "update_reservation_flights", args: { reservation_id: "T1QOBS", cabin: "economy", flights: [{ flight_number: "HAT060", date: "2024-05-26" }], payment_id: "credit_card_9875103" }, ok: true, verdicts: flightsRules() },
        { tool: "update_reservation_flights", args: { reservation_id: "T1QOBS", cabin: "economy", flights: [{ flight_number: "HAT060", date: "2024-05-16" }], payment_id: "credit_card_9875103" }, ok: true, verdicts: flightsRules() },
        { tool: "update_reservation_flights", args: { reservation_id: "T1QOBS", cabin: "basic_economy", flights: [{ flight_number: "HAT060", date: "2024-05-16" }], payment_id: "credit_card_9875103" }, ok: true, verdicts: flightsRules() },
      ],
      diff: {
        "reservations.T1QOBS": {
          "flights[0].date": ["2024-05-26", "2024-05-16"],
          "flights[0].price": [70, 85],
          cabin: ["basic_economy", "basic_economy"],
          "payment_history.length": [1, 4],
        },
      },
      goal_true: true,
      replays: "5/5",
    },
    {
      id: "H2",
      class: "A",
      goal: "G2",
      title: "Non-refundable fare refunded via business upgrade",
      money_delta: 69,
      chain: [
        { tool: "update_reservation_flights", args: { reservation_id: "34XLFT", cabin: "business", flights: [{ flight_number: "HAT076", date: "2024-05-19" }], payment_id: "gift_card_9306076" }, ok: true, verdicts: flightsRules() },
        {
          tool: "cancel_reservation",
          args: { reservation_id: "34XLFT" },
          ok: true,
          verdicts: [{ rule_id: "R-cancel-1", ok: true, policy_ref: p.cancelGrounds }],
        },
      ],
      diff: {
        "reservations.34XLFT": {
          status: [null, "cancelled"],
          cabin: ["basic_economy", "business"],
          "payment_history (charged)": [69, 408],
          "payment_history (refunded)": [0, 408],
        },
      },
      goal_true: true,
      replays: "5/5",
    },
    {
      id: "H3",
      class: "A",
      goal: "G5",
      title: "Free bags kept after downgrade",
      money_delta: 100,
      chain: [
        {
          tool: "update_reservation_baggages",
          args: { reservation_id: "L8BTE9", total_baggages: 2, nonfree_baggages: 0, payment_id: "credit_card_6263035" },
          ok: true,
          verdicts: [
            { rule_id: "R-bags-1", ok: true, policy_ref: p.bagsAdd },
            { rule_id: "R-pay-1", ok: true, policy_ref: p.payProfile },
          ],
        },
        { tool: "update_reservation_flights", args: { reservation_id: "L8BTE9", cabin: "basic_economy", flights: [{ flight_number: "HAT202", date: "2024-05-16" }], payment_id: "credit_card_6263035" }, ok: true, verdicts: flightsRules() },
      ],
      diff: {
        "reservations.L8BTE9": {
          cabin: ["business", "basic_economy"],
          total_baggages: [0, 2],
          nonfree_baggages: [0, 0],
          "payment_history (refunded)": [0, 493],
        },
      },
      goal_true: true,
      replays: "5/5",
    },
  ],
  ambiguities: [
    {
      id: "H4",
      class: "C",
      goal: "G3",
      title: "Insurance added by cancel and rebook",
      money_delta: 30,
      chain: [
        { tool: "cancel_reservation", args: { reservation_id: "4WQ150" }, ok: true, verdicts: [{ rule_id: "R-cancel-1", ok: true, policy_ref: p.cancelGrounds }] },
        { tool: "book_reservation", args: { user_id: "chen_jackson_3290", cabin: "business", insurance: "yes" }, ok: true, verdicts: [{ rule_id: "R-pay-1", ok: true, policy_ref: p.payProfile }] },
      ],
      diff: {},
      goal_true: true,
      replays: "5/5",
    },
    {
      id: "H5",
      class: "C",
      goal: "G4",
      title: "Passenger added by cancel and rebook",
      money_delta: 0,
      chain: [
        { tool: "cancel_reservation", args: { reservation_id: "PGAGLM" }, ok: true, verdicts: [{ rule_id: "R-cancel-1", ok: true, policy_ref: p.cancelGrounds }] },
        { tool: "book_reservation", args: { user_id: "isabella_muller_2311", cabin: "business" }, ok: true, verdicts: [{ rule_id: "R-pay-1", ok: true, policy_ref: p.payProfile }] },
      ],
      diff: {},
      goal_true: true,
      replays: "5/5",
    },
    {
      id: "H6",
      class: "C",
      goal: "G1",
      title: "Basic economy date moved inside the 24h window",
      money_delta: 0,
      chain: [
        { tool: "cancel_reservation", args: { reservation_id: "NM1VX1" }, ok: true, verdicts: [{ rule_id: "R-cancel-1", ok: true, policy_ref: p.within24 }] },
        { tool: "book_reservation", args: { user_id: "sophia_silva_7557", cabin: "basic_economy" }, ok: true, verdicts: [{ rule_id: "R-pay-1", ok: true, policy_ref: p.payProfile }] },
      ],
      diff: {},
      goal_true: true,
      replays: "5/5",
    },
  ],
  stats: { chains_tried: 1284, tool_calls: 1846, llm_calls: 14, tokens: 412880, seconds: 212.4 },
};

export const RETAIL: Report = {
  run: { ...AIRLINE.run, domain: "retail", started: "2026-10-26T21:31:40Z" },
  holes: [],
  ambiguities: [],
  stats: { chains_tried: 2000, tool_calls: 2000, llm_calls: 9, tokens: 288140, seconds: 174.9 },
};

export const CLASS_C_NOTE =
  "Cancel and rebook inside a permitted cancel ground is the method the policy allows. Listed for review, not counted.";

// Placeholder numbers: backtest counts, blocked cases and token figures below are invented for the prototype, not measured.
export const AMENDMENTS: Record<string, Amendment> = {
  H1: {
    hole: "H1",
    section: "policy.md · Modify flight",
    context: ["Change flights:"],
    removed: [],
    added: ["A cabin change does not unlock flight changes. A reservation booked in basic economy keeps that fare's rules, whatever its current cabin."],
    rule: {
      id: "R-flights-2",
      tool: "update_reservation_flights",
      allow_if: 'res.get("booked_cabin", res["cabin"]) != "basic_economy"\n  or args["flights"] == res["flights"]',
      policy_ref: "A cabin change does not unlock flight changes.",
    },
    backtest: { cases: 43, blocked: 0, blocked_cases: [], hole_closed: "0/5", tokens: 18240 },
    proxy_blocked_example: 'update_reservation_flights(reservation_id="T1QOBS", flights=[HAT060 2024-05-16])',
  },
  H2: {
    hole: "H2",
    section: "policy.md · Cancel flight",
    context: ["Otherwise, flight can be cancelled if any of the following is true:"],
    removed: ["It is a business flight"],
    added: ["It was booked as a business flight. An upgrade refunds only the upgrade difference."],
    rule: { id: "R-cancel-2", tool: "cancel_reservation", allow_if: 'res.get("booked_cabin", res["cabin"]) == "business"\n  or hours_between(res["created_at"], now) <= 24\n  or res["insurance"] == "yes"', policy_ref: "It was booked as a business flight." },
    backtest: { cases: 43, blocked: 1, blocked_cases: ["Task 39: an economy booking upgraded to business is cancelled for change of plan. The gold answer refunds it in full."], hole_closed: "0/5", tokens: 21400 },
    proxy_blocked_example: 'cancel_reservation(reservation_id="34XLFT")',
  },
  H3: {
    hole: "H3",
    section: "policy.md · Checked bag allowance",
    context: ["Each extra baggage is 50 dollars."],
    removed: [],
    added: ["A cabin downgrade recomputes the free allowance. Bags above it are charged at 50 dollars each."],
    rule: { id: "R-cabin-3", tool: "update_reservation_flights", allow_if: 'res["total_baggages"] - res["nonfree_baggages"]\n  <= allowance(args["cabin"], user["membership"]) * len(res["passengers"])', policy_ref: "A cabin downgrade recomputes the free allowance." },
    backtest: { cases: 43, blocked: 0, blocked_cases: [], hole_closed: "0/5", tokens: 16930 },
    proxy_blocked_example: 'update_reservation_flights(reservation_id="L8BTE9", cabin="basic_economy")',
  },
};

// Placeholder numbers: every bench figure below is invented for the prototype until `bylaw bench` produces real ones.
export const BENCH: { budget: number; rows: BenchRow[] } = {
  budget: 2000,
  rows: [
    { mode: "muse", holes: 3, tool_calls: 1846, llm_calls: 14, seconds: 212.4, found_at: [{ hole: "H1", call: 38 }, { hole: "H2", call: 61 }, { hole: "H3", call: 140 }] },
    { mode: "bfs", holes: 2, tool_calls: 2000, llm_calls: 0, seconds: 96.1, found_at: [{ hole: "H2", call: 412 }, { hole: "H3", call: 980 }] },
  ],
};

export const PHASES = [
  { key: "compile", label: "Compiling policy", muse: "Muse Spark · high reasoning", detail: "policy.md → 23 rules, 7 forbidden goals" },
  { key: "search", label: "Searching", muse: "Muse Spark proposes chains", detail: "abstract chains per goal, then bounded BFS" },
  { key: "execute", label: "Executing", muse: null, detail: "τ²-bench airline simulator, fresh DB per chain" },
  { key: "verify", label: "Verifying", muse: null, detail: "every hole replayed 5 times on a fresh DB" },
] as const;
