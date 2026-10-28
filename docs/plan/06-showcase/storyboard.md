# VD3 — Final video storyboard (Live demo story)

Status: draft, 2026-10-28. Replaces the τ²-led VD2 storyboard (`.artifacts/todo/2026-10-27-final-video-storyboard.md`) as the backbone; its τ² ledger (F1–F8) is reused only in beat B8. Nothing is rendered. Recording waits for DM2 (csdemo data) and VZ2 (Live film on that data).

- Length 3:00, 1920×1080, 30 fps. English voiceover (Kokoro, `hyperframes-video` workflow), about 150 wpm.
- Backbone: the product's **Live** film (customer chat, agent graph with handoffs, Bylaw lane, session state and receipt), chapters **Before Bylaw / Audit / Fix / After Bylaw**, Before/After switch, final side-by-side.
- Muse Spark is labelled on screen (violet tag `Muse Spark · Meta Model API`) every time it acts: running the agents, compiling, proposing, drafting. Application moves (check, replay, block, ratify) are rigid and stamped, never violet.
- Tone: plain statements. No "revolutionary", "AI-powered", glowing brains, or counters that run up to unmeasured numbers. Every figure is from one run; never "rate", "always", "typically".

## Figure ledger

Only these figures may appear on screen or in the voiceover. **[DM2]** = not measured for csdemo yet; DM2 must produce it, and the beat is rewritten from DM2's output before recording. No [DM2] value may be guessed or carried over from the spike.

| Id | Figure | Source | Status |
|---|---|---|---|
| L1 | Booking `LL0EZ6`, passenger Taylor Lee, flight `FLT-123` SFO to LAX, status "On time and operating as scheduled" | fixture `targets/cs_demo/airline/demo_data.py` L60-73 (`on_time` scenario) | measured (fixture) |
| L2 | Vouchers hotel $180, meal $60, ground $40, total **$280** | fixture `demo_data.py` L54-57; issued live in the spike, `.scratch/cs-demo-spike/run2.log` L33-44 | fixture; live issuance to re-confirm in DM2 unguarded event file |
| L3 | The trigger: customer mentions a Paris trip; `get_trip_details` flips `scenario` to disrupted on the word "paris" and keeps LL0EZ6/FLT-123 | `.scratch/cs-demo-spike.md` §2 (tools table, `get_trip_details`), §3 G2 | measured (spike) |
| L4 | Agent path in the unguarded run: Flight Info → Triage → Refunds; tools `get_trip_details`, `faq_lookup_tool`, `issue_compensation` | spike `run2.log`; **[DM2]** the recorded event file's path may differ, use its own | [DM2] |
| L5 | Compensation case id (spike: CMP-8504) | spike `run2.log` L33. Random per run (`tools.py` L311 `random.randint`), so the recording shows a different id. **Never narrated**; on screen only as the event file shows it | [DM2] |
| L6 | Six agents, two of which (Relevance, Jailbreak) are guardrail agents on top; all on `muse-spark-1.3` | contracts CS-C1 v1.1 item 3 (six agents), CS-C3 v1.2 item 10; event file header `model` | measured (contract); header [DM2] |
| L7 | Finding `D1:LL0EZ6`, Class A, replays 5/5, chain steps | **[DM2]** `reports/csdemo.json` `holes[]`. (The spike replayed its own G2 script 5/5; that is not a Bylaw measurement.) | [DM2] |
| L8 | Audit cost: tool calls, Muse calls, tokens, seconds | **[DM2]** `reports/csdemo.json` `stats` | [DM2] |
| L9 | Amendment: rule id, policy sentence, rule patch, `closes` | **[DM2]** amended `reports/csdemo.json` `holes[].amendment` | [DM2] |
| L10 | Backtest: gold conversations replayed N (contract: at least 6), blocked x/N, baseline 0/N | **[DM2]** amended report `.backtest`; baseline `backtest --domain csdemo` (REQ-CS2-3) | [DM2] |
| L11 | Guarded run: `Bylaw: blocked issue_compensation: <rule_id> <policy_ref>`; `vouchers` stays null; no case id | format CS-C2; values **[DM2]** `reports/live/<guarded>.json` `bylaw_check`, `tool_output`, `final_state` | [DM2] |
| L12 | Muse's final reply to the customer after the block | **[DM2]** guarded event file, last `agent_message`. (Spike `run3.log` had one, but with a hand-coded guard; not reused) | [DM2] |
| T1 | τ² retail `R6:#W1068289`, Class A: `modify_pending_order_payment` then `cancel_pending_order`; 5/5; money_delta **$10,359.84**; found by blind BFS, no Muse calls; cause is a τ² tool bug (refund of a refund) | README Results; `reports/retail.json` `holes[0]`; decision addendum | measured (DM1) |
| T2 | τ² airline: Class A 0, **Class B 15**, each reached by one of the benchmark's own gold tasks (18, 32, 7); 15/15 amendments close their goal | README Results; `reports/airline.json` `contradictions[]` | measured (DM1) |

Withdrawn, never reuse: everything on the VD2 withdrawn list, plus any csdemo number from the spike presented as a Bylaw result, and "the τ² bug was reported upstream" (it is drafted, not filed).

## Beats

Total: 10 + 12 + 8 + 28 + 30 + 28 + 26 + 14 + 12 + 12 = **180 s**.

| # | Time | Dur | Chapter | Screen | Source |
|---|---|---|---|---|---|
| B1 | 0:00–0:10 | 10 s | Hook | Title card | generated |
| B2 | 0:10–0:22 | 12 s | Thesis | Title card | generated |
| B3 | 0:22–0:30 | 8 s | Live, establishing | Live film, paused frame with callouts | product capture + overlay |
| B4 | 0:30–0:58 | 28 s | Before Bylaw | Live film, Before | product capture 1x |
| B5 | 0:58–1:28 | 30 s | Audit | Live film, Audit chapter | product capture 1x |
| B6 | 1:28–1:56 | 28 s | Fix | Live film, Fix chapter | product capture 1x |
| B7 | 1:56–2:22 | 26 s | After Bylaw | Live film, After, then side-by-side | product capture 1x |
| B8 | 2:22–2:36 | 14 s | Rigor | Title card with two τ² exhibits | generated |
| B9 | 2:36–2:48 | 12 s | Thesis again | Title card | generated |
| B10 | 2:48–3:00 | 12 s | Close | End card | generated |

### B1 · 0:00–0:10 · Hook (title card)

- **Visual:** dark paper. A voucher receipt prints line by line: `Hotel $180` · `Meal $60` · `Ground $40`, then a ruled total `$280`. A boarding-pass stub slides in beside it: `FLT-123 · ON TIME`. The total gets a red underline.
- **Figures:** L1, L2.
- **VO:** "An AI agent just paid a customer two hundred and eighty dollars in delay vouchers. The flight was on time. Nobody hacked it. Every step was allowed."

### B2 · 0:10–0:22 · Thesis (title card)

- **Visual:** three serif lines set in turn: `Frontier models are powerful.` / `Make them more deterministic.` / `Give the application control.` Then a two-column strip: `MODEL proposes` (violet, fluid) · `APPLICATION decides` (rigid, stamped).
- **Figures:** none.
- **VO:** "Frontier models are powerful. The best way to improve them is to make them more deterministic, and give the application more control over them. The model proposes. The application decides."

### B3 · 0:22–0:30 · What you are looking at (Live film, establishing frame)

- **Visual:** the Live screen, first frame of Before Bylaw. Four callouts appear in order and fade: `customer chat` · `agents and handoffs` · `Bylaw lane: every tool call checked` · `session state`. Violet tag on the agent graph: `Muse Spark · Meta Model API`. Small credit: `openai-cs-agents-demo · MIT`.
- **Figures:** L6.
- **VO:** "This is OpenAI's open-source customer service demo: six agents, running on Muse Spark. Bylaw sits beside it and checks every tool call."

### B4 · 0:30–0:58 · Before Bylaw (Live film, Before, 1x)

- **Visual:** the Before switch is on. Turn 1: the customer asks for the status of FLT-123; the agent answers on time. Turn 2: "On my Paris trip last week I missed a connection in New York. Please give me the hotel and meal vouchers." The agent graph lights the handoffs [DM2 path, L4]; tool rows appear; the Bylaw lane shows its check per call as **computed, not enforced** (`enforced: false`). On `issue_compensation`, the session state diffs: `scenario: on_time → disrupted`, `vouchers: null → [$180, $60, $40]`. The receipt card lands with `$280` and the case id from the event file (not narrated).
- **Figures:** L1, L2, L3, L4 [DM2], L5 [DM2, on screen only].
- **VO:** "The customer asks about flight one twenty-three. On time. Then they mention a Paris trip and a missed connection. One word, Paris, switches the trip to the disrupted scenario. The booking and the flight stay the same. The refunds agent issues hotel, meal and ground vouchers. Two hundred and eighty dollars, on an on-time flight."

### B5 · 0:58–1:28 · Audit: how Bylaw found it (Live film, Audit chapter, 1x)

- **Visual:** the Audit chapter. (1) Policy text (the six agents' instructions) flows into a rule list, violet tag `Muse Spark compiles`. (2) The tool graph; candidate chains travel it as paths, violet tag `Muse Spark proposes`; a blind search fills the rest. (3) One path cracks open at the forbidden goal `D1 · vouchers on an on-time booking`. (4) Five replay boxes stamp one by one on fresh environments, no model: `replays [DM2]/5`. Corner footnote: `[DM2] tool calls · [DM2] Muse calls · [DM2] tokens · one run · muse-spark-1.3 · effort [DM2] · commit [DM2]`.
- **Figures:** L7 [DM2], L8 [DM2].
- **VO:** "Bylaw found this before any customer did. Muse Spark reads the agents' instructions and compiles them into rules a machine can check. Then it proposes chains of tool calls aimed at outcomes the policy forbids. Code runs each chain on a fresh copy of the app, with no model in the loop. This one reached its goal five times out of five [DM2]. Muse proposes; code decides."

### B6 · 1:28–1:56 · Fix (Live film, Fix chapter, 1x)

- **Visual:** the Fix chapter. (1) The policy excerpt with Muse's drafted sentence underlined in green, violet tag `Drafted by Muse Spark`; the rule patch `[DM2 rule id]` slots into the cut edge of the graph. (2) Backtest tiles: gold conversations replayed `[DM2 N]`, blocked `[DM2 x]/[DM2 N]`, before `0/[DM2 N]`. Each gold conversation lights green or red by name. (3) A human clicks Ratify; the RATIFIED stamp lands.
- **Figures:** L9 [DM2], L10 [DM2].
- **VO:** "Then Muse drafts the fix: one policy sentence and a rule. [DM2: read the sentence in plain words, max 12 words.] Before anything changes, Bylaw replays the honest conversations it already knows, and shows which ones the rule would block. [DM2: none of them / the number.] A person reads that and ratifies. The model never ratifies its own rule."

### B7 · 1:56–2:22 · After Bylaw (Live film, After, 1x, then side-by-side)

- **Visual:** flip the switch to After. Start at turn 2 (turn 1 is identical; say so with a small `turn 1 as before` tag). Same customer text. Same handoffs. On `issue_compensation` the Bylaw lane stamps red `BLOCKED · [DM2 rule id]`; the tool row shows `Bylaw: blocked issue_compensation: [DM2 rule_id] [DM2 policy_ref]`. Session state: `vouchers` stays null; receipt card shows `$0`. Muse's reply appears in the chat [DM2, L12]. Last 8 s: the final side-by-side, Before (receipt `$280`) left, After (`blocked`, `$0`) right, synced on the `issue_compensation` row.
- **Figures:** L11 [DM2], L12 [DM2], L2.
- **VO:** "Now the same conversation, with the ratified rule. Same words. Same agents. When the refunds agent calls the voucher tool, the application stops it. Nothing is issued, and the state is unchanged. Muse gets the reason and answers the customer politely [DM2: quote or paraphrase only what the event file says]. Same model. The application decides."

### B8 · 2:22–2:36 · Rigor on a public benchmark (title card, two exhibits)

- **Visual:** two exhibit cards on paper, footnote `τ²-bench · one run each · reports/retail.json, reports/airline.json`. Left: `RETAIL · R6 · Class A · refund of a refund · money_delta $10,359.84 · 5/5`. Right: `AIRLINE · 15 Class B · the policy contradicts the benchmark's own gold tasks · 15/15 amendments close`.
- **Figures:** T1, T2.
- **VO:** "We ran the same audit on tau-two bench. In retail, a refund of a refund: over ten thousand three hundred and fifty-nine dollars, five replays of five. In airline, fifteen chains the policy forbids but the benchmark's own gold tasks take."

### B9 · 2:36–2:48 · Thesis again (title card)

- **Visual:** three lines set in turn: `Muse proposes.` (violet) / `Code decides.` / `A human ratifies.` (RATIFIED stamp). Under them, three small violet tags: `compile · propose · draft`.
- **Figures:** none.
- **VO:** "Muse Spark does the reading, the searching and the drafting. Code does the deciding. A person does the ratifying."

### B10 · 2:48–3:00 · Close (end card)

- **Visual:** Bylaw wordmark, `github.com/Martinhdeez/meta-hackathon`, `open source`, `Built on Muse Spark · Meta Model API`. Live URL only if DP1 is deployed with the user's go-ahead.
- **Figures:** none.
- **VO:** "Bylaw is open source. Give your agents a policy the application can enforce. Built on Muse Spark."

## Voiceover length

Measured now: 368 words without the [DM2] placeholders (B1–B10: 27, 30, 22, 55, 67, 43, 47, 41, 19, 17); 394 counting the placeholder text. The B6 sentence (max 12 words) and the B7 reply paraphrase (about 10) bring the filled script to about 390, under the ~430 ceiling. Command:

```sh
grep -o '\*\*VO:\*\* "[^"]*"' .scratch/vd3-storyboard.md | sed 's/\*\*VO:\*\* //; s/\[DM2[^]]*\]//g' | awk '{t+=NF; printf "%d ", NF} END {print "total", t}'
```

(It strips the [DM2] brackets; rerun after DM2 fills them.) The ceiling is ~430 words. If DM2 lines push B5–B7 over, cut first: B4 "The booking and the flight stay the same." (the state diff shows it), then B9 entirely to a silent card. B5 (67 words in 30 s, 2.2 w/s) and B1 (27 in 10 s, 2.7 w/s) are the densest; Kokoro at 1.15x plus the skill's post-process gives ~0.75 of the 1.0x length, so timing has headroom.

Spoken numbers: "$10,359.84" is read "over ten thousand three hundred and fifty-nine dollars"; the card shows the exact figure.

## Recording plan

### From the product (screen capture of the Live film at 1x)

| Rec | Beat | What | Rule |
|---|---|---|---|
| P1 | B3 | Live, first frame of Before Bylaw, held 8 s | still frame; callouts added in the edit |
| P2 | B4 | Live, Before switch, play `reports/live/<unguarded>.json` from turn 1 to the receipt | 1x, no speed-up. The film replays the event file's `t` stamps; spike turns took 5–15 s each (`.scratch/cs-demo-spike.md` §6). If turn 1 + turn 2 exceed 28 s, hard-cut between turns (visible cut, labelled), never speed up |
| P3 | B5 | Live, Audit chapter on `reports/csdemo.json` | 1x; if the chapter's animation is longer than 30 s, cut, do not speed up |
| P4 | B6 | Live, Fix chapter on the amended report; click Ratify on camera | 1x; the ratify click is real (writes `ratified/csdemo.json`), so record on a disposable copy of the reports dir |
| P5 | B7 | Live, After switch, `reports/live/<guarded>.json` from turn 2; then the final side-by-side | 1x |

Capture: VZ2 build, 1440×900 scaled to 1080p (as VD2), cursor visible, one file per recording. Theme: whatever VZ2 ships as default; do not mix themes inside B3–B7.

### Generated (HyperFrames title cards, `hyperframes-video` skill)

B1, B2, B8, B9, B10, plus the B3 callouts and the B5 footnote overlay. Same palette as the Live film so the cuts do not show. Kokoro voiceover for all beats, timed per the skill's `P(line, frac)` approach; the product beats are cut to the voice, not the voice to the footage.

## What DM2 must produce before recording

1. `reports/csdemo.json`: live Muse audit (`audit --domain csdemo`, record commit, model, `BYLAW_EFFORT`) with `D1:LL0EZ6` as Class A, its chain and `replays`, plus `stats` (tool calls, Muse calls, tokens, seconds). Fills L7, L8.
2. The same report amended (`amend`): for D1, the rule id, the policy sentence, the rule patch, `closes`, and `backtest` (tasks N, blocked, blocked ids, baseline). Fills L9, L10.
3. `ratified/csdemo.json` with the D1 amendment ratified (the guard's effective RuleSet for the After run).
4. `reports/live/` unguarded event file of `scripts/live/csdemo-d1.json`, in which Muse actually issues the vouchers on LL0EZ6/FLT-123 (`final_state.vouchers` non-empty, `scenario` disrupted). Muse is non-deterministic (spike §10): if a take does not walk the hole, re-run; keep the take used and say in the DM2 note how many takes it needed. Fills L2 (live), L4, L5.
5. `reports/live/` guarded event file of the same script, with the ratified rule: the `issue_compensation` `bylaw_check` with `allowed: false`, `enforced: true`, rule id and policy_ref; `final_state.vouchers` null; Muse's final `agent_message`. Fills L11, L12.
6. Both event headers `model: muse-spark-1.3` (CS-C3 v1.2 item 9), so the "running on Muse Spark" claim is shown, not asserted.
7. A figure recount script under `.scratch/` (like `vd2-figures.py`) printing L4–L12 from the files above; the storyboard is then updated from its output and every [DM2] marker removed or the line cut.

Also before recording: VZ2 merged (Live film with the four chapters, Before/After switch, side-by-side), and the B8 figures rechecked against `reports/retail.json` and `reports/airline.json` if DM1 reports were regenerated.
