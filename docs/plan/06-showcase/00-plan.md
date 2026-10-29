# 06 — Showcase: scan and fix, visible (M6)

Goal: make Bylaw's two processes, **scan** and **fix**, visible step by step on a real, recognisable agent app, so the demo sells the argument: frontier models are powerful, and the way to improve them is to make them more deterministic and give the application more control over them. The model proposes; the application decides.

Target app: OpenAI's MIT-licensed `openai-cs-agents-demo` (airline customer service, Agents SDK + Next.js), kept locally in `.scratch/cs-demo` until the spike decides how to vendor it.

## Items

| Id | Item | Kind | Weight | Agent | Depends on |
|---|---|---|---|---|---|
| CS1 | Spike: clone, analyse the demo, Muse via Agents SDK, ChatKit check, go/no-go | evidence | light | assistant | — |
| UI6 | Copy and bench fixes from the DM1 review | view fix | full | designer, then reviewer | — |
| RM2 | `replay --monitor`: per-step goal monitor state | fix | light | builder | — |
| VZ1 | Prototype of the live Scan and Fix views | view | full | designer (prototype, then user approval) | — |
| VN1 | Vendor the demo backend into `targets/cs_demo/` (MIT notice, no OpenAI branding, pinned `openai-agents`) | chore | light | assistant | CS1 go |
| CS2 | `csdemo` domain: C1 plug-in, goals D1–D4, hand RuleSet, gold conversations; audit, amend, backtest work on it | feature | full | test-author + builder | VN1 |
| CS3 | Agents guard (ToolInputGuardrail from the effective RuleSet) and `live` runner recording a scripted conversation as an event file | feature | full | test-author + builder | VN1 |
| DM2 | Demo data for csdemo: live Muse audit and amend, ratify, live conversation unguarded and guarded; reports committed | data | light | builder | CS2, CS3 |
| VZ1 | Prototype of the live Scan and Fix views | view | full | designer (prototype, then user approval) | — |
| DM3 | Usefulness eval: the guard on the real demo agents (Muse) over a set of scripted conversations, attacks on D1–D4 and legitimate requests (disrupted-flight compensation, own-seat change, real cancellation); each run unguarded and guarded; table of attacks executed vs blocked and legitimate actions passed vs wrongly blocked; event files committed and listed in the Live view | evidence | light | builder | DM2 |
| RA1 | Ratify API and the web Ratify button accept `csdemo` (`bylaw/api.py` `Domain`), so the ratify step can be shot on camera | fix | full | builder, then reviewer | DM2 |
| VZ2 | Scan and Fix views on the csdemo data (agent app pane, Bylaw lane, scenes) | view | full | designer, then reviewer | VZ1 approved, CS2, CS3 contracts |

CS1 verdict (2026-10-28): go with changes (`.scratch/cs-demo-spike.md`). User decisions: scope cut to about 4 days (no ChatKit, no demo Next.js UI; Bylaw web shows the whole scene from recorded event files), vendor the backend only.

Contracts: `docs/plan/06-showcase/contracts.md` (v1.0).

## Visual direction (user, 2026-10-28)

"Make the process graphic, not just a load bar or something like that, we need something so visual." Scan and Fix are scenes, not progress indicators: tools as a graph, chains as paths travelling it, state as a live object, the hole as a crack; the fix as a rule slotting into the cut edge and the attack stopped at the proxy gate. Model moves read fluid and violet; application moves read rigid and stamped.

## Design decisions (user, 2026-10-28, after VZ1 v1)

- "The most useful part is the Live": Live (the agent app with Bylaw checking every action, without and with Bylaw) is the hero screen and the video's backbone; Scan and Fix are short sequences that feed it.
- "Remove the AI slop": the designer uses the Impeccable skill (installed for this project, not committed: `.claude/skills/impeccable/`) and the anti-slop ban list; detector must run clean.
- "I want to understand the application just by seeing it": the screen alone explains Bylaw to a newcomer.

## Overnight decisions (user, 2026-10-28)

- Design: mix of v4.2 B (paper record) with A's handoff trail and focal card; Session state removed; bigger brand bar and logo; dark default; player controls hidden with `?film=1`. Approved for VZ2 implementation.
- Order: CS2 and CS3 merge through reviewers, then DM2, DM3, VZ2, UI7. Gate cap 2. No deploy, no remote branch deletion.
- `main` may be updated from a green `bylaw/build` (user: "you could touch main, there isn't any customer").
- Goal: see the real app in action, Bylaw acting as the guardrail of the downloaded demo app, and measure whether it is really useful (DM3).

## Requirements

| Id | Requirement | Surface |
|---|---|---|
| REQ-UI6-1 | Class B findings never say the policy text forbids the outcome; the copy states that a gold task reaches the same goal (contradiction between policy and practice). | Report, Hole, Amendment screens |
| REQ-UI6-2 | The Bench screen compares Class B counts per mode as well as Class A. | Bench screen |
| REQ-UI6-3 | A bench row whose run has no model is not drawn in the Muse accent. | Bench screen |
| REQ-UI6-4 | Each Class C note sits in the group of the goal it describes. | Report screen |
| REQ-CS2-1 | `get_domain("csdemo")` returns a C1 domain over the vendored demo: fresh state per env, direct tool calls (no LLM), snapshot per contract CS-C1. | Python |
| REQ-CS2-2 | `audit --domain csdemo --no-llm` finds D1 (vouchers on an on-time booking) and D2 (seat written to a confirmation that is not the passenger's) as Class A, each replaying 5/5. | CLI + report JSON |
| REQ-CS2-3 | No gold conversation reaches a forbidden goal, and the hand RuleSet blocks none of them (`backtest --domain csdemo` prints blocked 0/N). | CLI |
| REQ-CS2-4 | `amend` on the csdemo report produces, per Class A finding, an amendment whose patch closes the chain; its backtest names the gold conversations it would block. | CLI + JSON |
| REQ-CS3-1 | With the guard on, a tool call that the effective RuleSet forbids is not executed: the agent receives `Bylaw: blocked <tool>: <rule_id> <policy_ref>` as the tool output and the state is unchanged. | Python |
| REQ-CS3-2 | `live --domain csdemo --script FILE [--guard] -o OUT` plays the scripted customer turns against the demo agents on Muse and writes an event file per CS-C3 in which every tool call has a `bylaw_check` event. | CLI + JSON |
| REQ-CS3-3 | `GET /api/live` lists the event files in `reports/live/`; `GET /api/live/{name}` returns one. | API |
| REQ-RM2-1 | `replay --hole ID --monitor` prints, after each step line, the goal monitor state for that step (goal id, reached yes/no, and its measured value such as money_delta); without `--monitor` output is unchanged. | CLI |

## Out of scope

Deploy (user go-ahead). Filing the upstream issue (user approval). Retail Muse search.

## Open findings (for UI7)

From the UI6 review (PR #34, merged 1565cec):
1. `web/src/ui.tsx` `classCWhy` calls retail R5 "the policy is silent"; R5 is an ambiguity about the once-only line (`bylaw/goals_retail.py`).
2. `classCWhy` checks the chain before the pre-registered goal class and ignores the same-user condition, the reverse of `report.classify`.
3. `web/src/screens/Report.tsx` takes the Class C note from the group's first entry only.
4. `web/e2e/ui6.spec.ts` exercises one Class B finding (task 32) only.

From the CS2 review (PR #38, merged 3b93a37), for DM2/DM3:
1. REQ-CS2-4 is not met for D1 on the only live amend run (H5 `closes False`): Muse's patch reads the session itinerary, which `update_seat` leaves disrupted; `RULE_NAMES` in `bylaw/env/cs_demo.py` presents `itinerary` as the booking's. Re-run, or add a `RULE_NAMES` hint, before DM2 ratifies.
2. The claim that a rule on the confirmation at payment closes D1 rests on a test that hardcodes `confirmation_number == 'IR-D204'`; say so wherever it is quoted.
3. `_call` drops arguments the tool schema lacks but traces them as given; a rule can see arguments the tool never used.
4. `payment_session` replays with a fresh `Random(0)`; exact only from a fresh env.

From the DM2 review (PR #41, merged c34d698):
1. H4 D2:IR-D204 has `closes False` in `reports/csdemo.json` (6 of 7 holes close); the live `test_REQ_CS2_4` asserts every hole closes and would fail on this data. Only D1 was required and ratified.
2. `POST` ratify returns 422 for `csdemo` (`bylaw/api.py` `Domain` is airline/retail); DM2 ratified through `bylaw.ratified.ratify`. Item RA1.
3. The unguarded recording carries 1 denied, not enforced check, as CS-C3 specifies; the Live view may show it as what Bylaw would have blocked.
