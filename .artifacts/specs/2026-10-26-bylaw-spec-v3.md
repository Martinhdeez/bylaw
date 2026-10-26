# Bylaw — Product Spec v3

Status: v3, 2026-10-26. It replaces `2026-10-26-policy-firewall-spec.md`. Target: Meta Global AI Developer Hackathon (Indie). Submission is due Wed 2026-11-04 9:00 PM ET.

## 1. Product

**Problem.** Companies let AI agents act on customers: cancel, refund, rebook. Every agent obeys a policy written in natural language. Each step can comply with the policy while a *sequence* of steps reaches an outcome the policy forbids. Runtime guardrails check the agent. Nobody checks the law.

**What it does.** Bylaw audits the policy an agent runs on.
- Input: the agent's tools (MCP / OpenAPI / τ² toolkit), the policy, and a sandbox to execute in.
- Output:
  1. Confirmed holes, each with an executed trace.
  2. Drafted amendments.
  3. The measured cost of each amendment (honest past cases it would block).
  4. A proxy that enforces the ratified amendments at runtime.

**How it does it.**
1. Compile: Muse Spark turns the policy into per-tool rules and forbidden-outcome predicates.
2. Propose: Muse Spark plus a bounded BFS find chains of allowed calls that may reach a forbidden outcome.
3. Execute: each chain runs in the simulator.
4. Verify: deterministic code checks that every step passes its rule and the final state satisfies a forbidden predicate.
5. Amend: Muse drafts an amendment. It is backtested against the gold tasks.
6. Ratify: a human approves.
7. Enforce: the MCP proxy applies the amendment.

Line for the pitch: "The agent did nothing wrong. The law was wrong."

## 2. Hole classes

- **Class A — circumvention (counted).** Every step passes the per-tool rules the policy states. The final DB state satisfies a pre-registered forbidden predicate the policy states explicitly. This must be proven by execution.
- **Class B — contradiction.** Two policy clauses cannot both hold for some state. Reported, not counted.
- **Class C — silence / ambiguity.** The policy says nothing about an outcome. It is reported as "ambiguity", never as a hole.

## 3. Target: τ²-bench airline (verified by reading the code)

Facts:
- Repo `sierra-research/tau2-bench`, MIT license, Python `>=3.12,<3.14`, uses uv. Data under `data/`; set `TAU2_DATA_DIR`.
- Environment: `tau2.domains.airline.environment.get_environment(db=FlightDB.load(AIRLINE_DB_PATH))`. Tools are called directly with no LLM: `env.use_tool("cancel_reservation", reservation_id=...)` or `env.tools.<name>(...)`.
- State: `env.tools.db` is a pydantic `FlightDB` (2000 reservations, 500 users, 300 flights).
  - Snapshot: `db.model_copy(deep=True)` / `model_dump()`.
  - Compare: `env.get_db_hash()` or a dict diff.
  - Clock fixed at `2024-05-15T15:00:00`.
- Tools (14):
  - READ: `get_user_details`, `get_reservation_details`, `list_all_airports`, `search_direct_flight`, `search_onestop_flight`, `get_flight_status`.
  - WRITE: `book_reservation`, `cancel_reservation`, `update_reservation_flights`, `update_reservation_baggages`, `update_reservation_passengers`, `send_certificate`.
  - GENERIC: `calculate`, `transfer_to_human_agents`.
- The API enforces almost nothing. It only checks:
  - passenger count on `update_reservation_passengers`;
  - no certificate payment on updates;
  - flights must be `available` to book or reprice.

  Cancel conditions and the basic-economy no-change rule are agent-enforced: the policy says so explicitly.
- Tasks: 50 (`train` 30 / `test` 20). 43 of them carry gold `evaluation_criteria.actions` (name + arguments), which can be replayed for the backtest.

### Candidate holes (spike M0 confirms by execution)

| # | Hole | Tool sequence | Policy lines | Status |
|---|------|---------------|--------------|--------|
| H1 | Basic economy flights changed | `update_reservation_flights(res, cabin=economy, same flights)` → `update_reservation_flights(res, economy, new flights)` → optionally the same call back to `basic_economy` | "Basic economy flights cannot be modified" vs "all reservations, including basic economy, can change cabin" + "Other reservations can be modified" | CONFIRMED-BY-READING (206 targets: basic economy, no insurance, >24h old, all flights available) |
| H2 | Non-refundable basic economy fully refunded | `update_reservation_flights(res, cabin=business, same flights)` → `cancel_reservation(res)`. The refund reverses *all* payments, including the original fare | Cancel allowed only if <24h / airline-cancelled / business / insured; "It is a business flight" becomes true after a legal cabin change | CONFIRMED-BY-READING (money leak) |
| H3 | Free bags kept after downgrade | business res: `update_reservation_baggages(total=N, nonfree=0)` within the business allowance → `update_reservation_flights(res, cabin=economy\|basic_economy, same flights)`; the fare difference is refunded and the bags stay free | Allowance table per cabin/membership; "can add but not remove checked bags" | CONFIRMED-BY-READING (money leak; the tool never re-prices bags) |
| H4 | Insurance added after booking | business res (cancellable anytime) or res <24h: `cancel_reservation` → `book_reservation(..., insurance="yes")` | "The user cannot add insurance after initial booking" | Reachable by reading; Class C (ambiguity) |
| H5 | Passenger count changed | business res: `cancel_reservation` → `book_reservation(same flights, passengers+1)` | "Even a human agent cannot modify the number of passengers" | Reachable by reading; Class C (ambiguity) |
| H6 | Basic economy changed via the 24h window | `cancel_reservation` → `book_reservation(new date)` | "Basic economy cannot be modified" | Reachable by reading; Class C (Muse: permitted method) |
| H7 | Delay compensation paid twice | delayed res: `update_reservation_flights` → `send_certificate(50×pax)` → change again → `send_certificate` | Policy is silent on "once per incident" | SPECULATIVE, likely Class C |
| H8 | Compensation eligibility bought by upgrading | regular basic economy on a cancelled flight → upgrade to business → `send_certificate(100×pax)` | "Only compensate if … flies business" | SPECULATIVE: the API rejects repricing a non-`available` flight, so it is probably unreachable |

The demo leads with H1, H2 and H3: no excuse, and H2/H3 leak money.

**Muse's own reading (live check, 2026-10-26).** Asked whether cancel+rebook within 24h on basic economy is a loophole, Muse answered: "No, cancel-and-rebook within 24h is the permitted method, not a loophole."
- H4, H5 and H6 are therefore **Class C (ambiguity), not counted**.
- They are reclassified as Class A only if a chain breaks the 24h condition itself, e.g. it rebooks after 24h by stacking cancel reasons such as the business-cabin hop of H2.
- Counted holes rest on H1, H2 and H3.

### Pre-registered forbidden goals (frozen before the search runs)

These are predicates over the `FlightDB` diff between `before` and `after` for a reservation `r` and user `u`:

- **G1 basic_economy_flights_changed:** `before[r].cabin == basic_economy and before[r].flights != after[r].flights`. A flight change is either a different (flight_number, date) set on the same id, or a cancel plus a new booking for the same user and O/D with a different date.
- **G2 nonrefundable_refunded:** `before[r].cabin == basic_economy and insurance == "no" and created_at older than 24h and after[r].status == "cancelled" and the refunds include the original fare`.
- **G3 insurance_added_after_booking:** the same user and itinerary go from `insurance == "no"` to an active reservation with `insurance == "yes"`.
- **G4 passenger_count_changed:** the same user and itinerary go from n to m≠n passengers on an active reservation.
- **G5 free_bags_over_allowance:** `after[r].total_baggages - after[r].nonfree_baggages > allowance(after[r].cabin, u.membership) × len(passengers)`.
- **G6 compensation_ineligible:** a new certificate is issued to `u` while `u.membership == regular and insurance == "no" and cabin != business` (cabin evaluated at the time of the incident).
- **G7 compensation_duplicated:** more than one certificate for the same reservation/incident. Pre-registered as Class C unless the policy is read as forbidding it.

## 4. Architecture

```
policy.md ──► Compiler (Muse Spark, structured output) ──► RuleSet {tool_rules[], forbidden_goals[]}
                                                               │
tools schema ──► Proposer (Muse Spark, reasoning=max) ──► candidate chains ◄── bounded BFS over WRITE tools (depth ≤4)
                                                               │
                                               Executor (τ² env, fresh DB copy per chain)
                                                               │
                                     Verifier (deterministic): per-step rule check + forbidden predicate on the DB diff
                                                               │
                                     Hole report JSON ──► Amendment drafter (Muse) ──► Backtest (43 gold tasks)
                                                               │
                                              Web UI (report · trace replay · diff · ratify) ──► MCP proxy (enforce)
```

- **Compiler.** The policy text becomes JSON. `tool_rules` are preconditions per tool, using a small, safe expression language over (args, db, now). Each `forbidden_goal` is one G-predicate. The LLM output is validated by a JSON schema. The predicates themselves are hand-reviewed Python for the τ² airline target.
- **Rule checker.** Evaluates the `tool_rules` before each call. This is the "every step legal" proof.
- **Proposer + BFS.**
  - Muse proposes abstract chains (tool names plus argument intents) per forbidden goal.
  - The BFS instantiates the arguments from the DB (targets matching each goal's preconditions) and enumerates WRITE-tool chains up to depth 4. Pruning keeps only chains where the rule checker passes.
- **Executor.** A deep-copied env per chain. Records each call, its result and any exception.
- **Verifier.** A chain is a Class A hole iff all steps pass the rules, no tool raised, and the forbidden predicate holds on the diff. Each hole is replayed 5× (deterministic, so 5/5 is expected; the number goes in the report).
- **Amendment drafter.** Muse proposes a policy sentence plus the corresponding `tool_rule` patch.
- **Backtest.** Replay the gold actions of the 43 tasks through the patched rule checker. Report "blocked honest cases". Target: 0.
- **Report JSON** per hole: id, class, goal, chain, per-step rule verdicts, DB diff, amendment, backtest numbers.
- **Web UI.** Report list → hole page (trace replay animation, policy lines highlighted) → amendment diff → Ratify button.
- **MCP proxy.** An MCP server wrapping the τ² tools. On each call it evaluates the ratified rules plus a session-level goal monitor (it blocks the call that would complete a forbidden chain). It returns `BLOCKED: <amendment id>`.

## 5. LLM client (provider-agnostic)

Meta API, verified live on 2026-10-26:
- `MODEL_API_KEY` is in `.env`. Load it with python-dotenv and never print it.
- Models: `muse-spark-1.3`, `muse-spark-1.2`, `muse-spark-1.1`, `muse-spark-1.3-contributor`, `muse-spark-1.2-contributor`, `muse-wonder-1.0`, `muse-image-1.0`, `muse-voice-transcribe-1.0`, `sam-3.1`.
- `muse-spark-1.3` is a reasoning model. Even "hello" spends ~400 reasoning tokens, so use **`max_tokens` ≥ 2000**. At 400, the call returns `finish_reason="length"` with empty content.
- Latency is 3–6 s per short call.
- `reasoning_effort="high"` is accepted.
- `response_format` `json_schema` with `strict=true` works.
- There is no Baseten key yet, so Muse Spark Open (open weights) is a **stretch goal**.
- Smoke tests: `.scratch/apitest.py` and `.scratch/apitest2.py` (`uv run --no-project --with python-dotenv python .scratch/apitest.py`).

- OpenAI-compatible chat client. `BASE_URL` defaults to `https://api.meta.ai/v1`, `MODEL` defaults to `muse-spark-1.3`, and `MODEL_API_KEY` comes from the environment (`.env`, never committed).
- A capability table per model sets `reasoning_effort` (max/none), `video_input`, `context_tokens` and `structured_output`. A step that needs a missing capability degrades: no reasoning effort means a plain prompt, no structured output means JSON-mode parse plus a retry.
- Swapping the model changes how many holes are *found*, never whether a reported hole is *real*, because the verifier is code.

## 6. Meta tooling that carries load (labelled in the UI)

| Capability | Where it is used | UI label |
|---|---|---|
| Muse Spark structured output | Policy compiler | "Compiled by Muse Spark" |
| Muse Spark reasoning effort = max | Proposer | "Muse Spark · max reasoning" |
| Muse Spark 1M context | Whole policy + all 50 tasks + tool schemas in one prompt | token counter |
| Muse Spark video input (stretch) | Ops screen recording → extra tool rules, cited by timestamp | "from video @0:42" |
| Muse Spark Open (open weights, Baseten) — stretch, no key yet | Same pipeline, self-hosted switch | "runs on Muse Spark Open" toggle |

The README states that the code was written with Claude Code. The product's reasoning runs on Muse.

## 7. Rigor

- Forbidden goals are pre-registered: §3 is frozen and committed before the first search run (commit hash in the report).
- Blind reviewer: a separate LLM session or a human gets only the policy and the trace, and must answer "does this outcome violate the policy?". The agreement rate is reported.
- Coverage is stated over abstract argument classes (cabin × membership × insurance × age bucket × status), not claimed as complete.
- Upstream: a GitHub issue on tau2-bench with H1/H2/H3 traces. This is drafted, and filed only with the user's approval.

## 8. Out of scope

Telecom/retail domains (stretch only), multi-tenant SaaS, auth, billing.
