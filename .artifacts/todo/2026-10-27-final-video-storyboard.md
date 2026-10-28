# VD1 — Final video: script and storyboard

Status: VD2, 2026-10-28. Figures filled from the DM1 reports (PR #32, branch `data/dm1-demo`, commit c5e5af7), which are still under review. Nothing is rendered. Rendering waits for DM1 to merge.

- Length: 3:00, 1920×1080, 30 fps. Narration in English, about 410 words.
- Format: a ≈50 s hook in motion graphics, then the real app, then a closing card.
- Style: the UI4/UI5 legal record. Serif headings, § numbers, "Exhibit" labels, the RATIFIED stamp, violet accent. The hook and the app use the same palette, so the cut from graphics to the app should not stand out. The hook is in dark theme. The app recordings are in light theme, plus one theme-toggle shot.
- Tone: plain statements, each tied to a measured figure. Do not use words like "revolutionary", "unprecedented" or "AI-powered", stock "AI" imagery, glowing brains, or a counter that runs up to a number nobody measured.
- Every figure is from one run. Never say "rate", "always" or "typically" about a figure, and never imply it would repeat.

## The runs

| Run | Command | Commit | Model, effort |
|---|---|---|---|
| Airline audit + amend | `BYLAW_EFFORT=low uv run python -m bylaw audit --domain airline -o reports/airline.json`, then `amend reports/airline.json -o reports/airline.json` | 05bd65c | `muse-spark-1.3`, effort low, budget 2000 |
| Retail audit | `uv run python -m bylaw audit --domain retail --no-llm -o reports/retail.json` | 9f13ae2 | none (blind BFS, no Muse calls), budget 2000 |
| Airline bench | `BYLAW_EFFORT=low uv run python -m bylaw bench --domain airline --budget 200 -o reports/airline.bench.json` | 9f13ae2 | `muse-spark-1.3`, effort low, budget 200 |
| Proxy replays | `uv run python -m bylaw replay --domain airline --gold`; the G1-monitored hole replay below (F6) | bada101 | none |

The three JSON files are on `origin/data/dm1-demo`. Every figure from them was recounted with `python3 .scratch/vd2-figures.py <dir with the 3 JSON>` (output `.scratch/vd2-figures.txt`, not committed).

## Figure ledger

Only these figures may appear, on screen or in the narration. Each scene cites its figures by ledger id.

| Id | Figure | Source (JSON path) |
|---|---|---|
| F1 | Retail `R6:#W1068289`, Class A: `modify_pending_order_payment` then `cancel_pending_order`; replays 5/5; money_delta $10,359.84; afterwards the order's payment history holds 2 payments and 4 refunds, each $3,453.28. Found by blind BFS, no Muse calls | `retail.json` `holes[0].key`, `.chain[].tool`, `.replays`, `.money_delta`, `.diff.orders["#W1068289"].after.payment_history`; `run.mode` = bfs, `stats.llm_calls` = 0 |
| F1b | Cause of F1: a τ² tool bug. `cancel_pending_order` refunds every `payment_history` entry, refund entries included (τ² `tools.py` L191, loop L218). The upstream issue is drafted and **not filed**: never say it was reported | decision addendum `docs/plan/decisions-2026-10-27-gold-adjudication.md` |
| F2 | Airline: Class A 0, Class B 15 (G5 12, G1 2, G2 1), Class C 102 (G7 100, G1 2) | `airline.json` `len(holes)`, `len(contradictions)` and `.goal`, `len(ambiguities)` and `.goal` |
| F3 | The 15 Class B chains are taken by τ² gold tasks: task 18 (12 entries), task 32 (2), task 7 (1). The task-7 finding is `B6 G2:1ERWZ8` | `airline.json` `contradictions[].gold.tasks`, `contradictions[].id/key` |
| F3b | Tasks 7 and 32: the policy is ambiguous. Basic economy cannot be cancelled or changed (policy L110, L143-147), but L117 allows the cabin upgrade first, and practice reads it permissively. Task 18: a policy gap, the policy is silent on bags after a cabin change (L83-86) | decision addendum |
| F4 | Amendments: 15/15 close their goal; each blocks the gold task that sanctions it; 14 block that task only; one (B5, G1:1ERWZ8) blocks 5 gold tasks (7, 17, 22, 32, 44); baseline 0/43 | `airline.json` `contradictions[].closes`, `.backtest.blocked`, `.backtest.blocked_tasks`, `.backtest.baseline_blocked`, `.backtest.tasks` |
| F5 | Proxy, nothing ratified: airline gold 0/43 blocked, 1 unknown | `replay --domain airline --gold` at bada101, `.scratch/vd2-replay-gold.txt` |
| F6 | Proxy, goal G1 monitored, DM1 finding `G1:1ERWZ8`: step 0 ALLOWED, step 1 BLOCKED by G1 | `uv run python .scratch/vd2-monitor.py <airline.json>` (`Proxy(domain, monitor_goals=["G1"])`, as PX1 `measure.py`) at bada101, `.scratch/vd2-replay-hole-g1.txt` |
| F7 | Airline audit run: 1997 tool calls, 7 Muse calls, 120,756 tokens, 425 s (425.05) | `airline.json` `stats.tool_calls`, `.llm_calls`, `.tokens`, `.seconds` |
| F8 | Bench, one run, budget 200: BFS Class B 9, Muse Class B 7; Class A 0 for both; Class C BFS 2, Muse 48; tool calls 200 vs 199; Muse 7 calls | `airline.bench.json` `rows[].contradictions`, `.holes`, `.ambiguities`, `.tool_calls`, `.llm_calls` |
| F8b | The bench Muse row shows 0 tokens because all 7 proposer replies came from the cache the audit wrote. **0 is not Muse's cost**; the cost is the audit's 7 calls and 120,756 tokens (F7) | `airline.bench.json` `rows[1].tokens`; DM1 note `.artifacts/to-test/2026-10-28-dm1-demo-reports.md` |

**Withdrawn, do not reuse:** "−$48,200" and every similar placeholder; "−$8,581"; "3 holes found"; "50/50" and "42/43 past cases replayed, 0 honest customers blocked"; "refunded twice" (the order shows 4 refunds, F1); the old five-budget bench table (1/2, 4/4, 7/8, 9/38, 15/18), "38 against 9", "Muse ≥ BFS at every budget" and "≈185k tokens per Muse run" (counted before v1.7 and not reproduced by DM1); "Class C 2"; any claim that Muse beats BFS; "0 tokens" as Muse's cost; "Muse Spark, high reasoning" for these runs (they ran at effort low); the "0 tokens · 1M context" counter; "Muse Spark · video"; "Muse Spark Open / open weights / never leaves the building"; the boarding-pass "cancel + rebook = changed" hole; calling tasks 7, 32 or 18 gold "errors"; saying the τ² bug was reported upstream. Cite no gold task and no goal beyond those in F2 and F3.

**Per-row money:** the Report and Finding screens show per-entry money_delta (e.g. B1 $840, B2 $8,736). These come from the DM1 report, but the narration never reads a per-row figure and no shot zooms on that column.

## Scene list

| # | Time | Dur | Part | Screen |
|---|---|---|---|---|
| S1 | 0:00–0:09 | 9 s | Hook | Motion: retail order exhibit, two allowed steps, refund lines pile up |
| S2 | 0:09–0:16 | 7 s | Hook | Motion: money_delta and 5/5 replays |
| S3 | 0:16–0:24 | 8 s | Hook | Motion: "suspects cleared", the cancel tool named |
| S4 | 0:24–0:29 | 5 s | Hook | Motion: "Every step was allowed." |
| S5 | 0:29–0:37 | 8 s | Hook | Motion: guardrails vs the policy (from v8) |
| S6 | 0:37–0:50 | 13 s | Hook | Motion: you give / you get, "Built on Muse Spark" |
| S7 | 0:50–1:08 | 18 s | Product | App: Audit, run on airline |
| S8 | 1:08–1:28 | 20 s | Product | App: Report hero, then a gold task 7 overlay |
| S9 | 1:28–1:42 | 14 s | Product | App: Report, Policy vs practice list |
| S10 | 1:42–1:58 | 16 s | Product | App: Finding page, trace replay, proof 5/5 |
| S11 | 1:58–2:16 | 18 s | Product | App: Amendment, backtest tiles, Ratify, stamp |
| S12 | 2:16–2:32 | 16 s | Product | Terminal: proxy replay, gold 0/43, then BLOCKED |
| S13 | 2:32–2:50 | 18 s | Product | App: Bench, plus a motion table |
| S14 | 2:50–3:00 | 10 s | Close | Motion: closing card |

Hook S1–S6 = 50 s. Total 180 s (9+7+8+5+8+13+18+20+14+16+18+16+18+10).

## Storyboard and narration

### S1 · 0:00–0:09 · Cold open (motion)

- **Screen:** a retail order shown as a legal exhibit card ("EXHIBIT A · order #W1068289") on a dark paper background. Two ruled lines appear in turn, each stamped with a green ✓: `modify payment method` and `cancel order`. Below, the payment history prints: 2 payment lines, then 4 refund lines, all $3,453.28. The refund lines are underlined in red.
- **On screen:** `EXHIBIT A · #W1068289` · `✓ allowed` · `✓ allowed` · `2 payments · 4 refunds · $3,453.28 each`
- **Figures:** F1
- **VO:** "An agent switches the payment method on an order. Then it cancels the order. The store's policy allows each step. Four refunds come out."

### S2 · 0:09–0:16 · The amount

- **Screen:** the exhibit slides left. A large serif figure sets in like a ledger entry, and five small replay boxes tick on one at a time.
- **On screen:** `money_delta  $10,359.84` · `replays 5/5` · footnote `τ²-bench retail simulator · one run · audit --domain retail --no-llm · 9f13ae2`
- **Figures:** F1
- **VO:** "Ten thousand, three hundred and fifty-nine dollars paid out, in the tau-two retail simulator. Five replays out of five."

### S3 · 0:16–0:24 · Suspects cleared (from v8, last tile changed)

- **Screen:** the v8 sequence, restyled to the legal-record palette, so a strike-through replaces the crosshair. Three tiles (Jailbreak, Attacker, Agent bug) are crossed out one by one, `SUSPECTS CLEARED 1/3` to `3/3`. A fourth exhibit card sets in uncrossed: `cancel_pending_order · refunds every payment line, refunds included`.
- **On screen:** `Jailbreak` · `Attacker` · `Agent bug` · `SUSPECTS CLEARED 3/3` · `τ² cancel_pending_order`
- **Figures:** F1b
- **VO:** "No jailbreak. No attacker. No bug in the agent. The cancel tool refunds every payment line, refunds included."

### S4 · 0:24–0:29 · The line

- **Screen:** two serif lines on paper, typed out in turn.
- **On screen:** `The agent did nothing wrong.` / `Every step was allowed.`
- **VO:** "The agent did nothing wrong. Every step was allowed."

### S5 · 0:29–0:37 · Nobody checks the policy (from v8)

- **Screen:** the v8 split. On the left, "Guardrails → check the agent" with a shield. On the right, "The policy → checked by nobody". The right half then turns into the Bylaw wordmark.
- **On screen:** `Guardrails check the agent.` · `Nobody checks the policy.` · `bylaw`
- **VO:** "Guardrails check the agent against the policy. Nobody checks the policy itself. Bylaw does."

### S6 · 0:37–0:50 · What it is

- **Screen:** two columns, set like the § sections of a filing.
  - YOU GIVE: `the agent's tools` · `its policy` · `a sandbox`.
  - YOU GET: `§1 forbidden chains, executed` · `§2 amendments, drafted` · `§3 their cost, measured` · `§4 a proxy, enforcing`.
  - A violet tag sets at the end: `Built on Muse Spark · Meta Model API`.
- **VO:** "Give it an agent's tools, its policy and a sandbox. It returns the forbidden chains it executed, an amendment for each, what each amendment costs, and a proxy that enforces it."

### S7 · 0:50–1:08 · Audit (app, recording R1)

- **Screen:** Audit screen in light theme.
  1. Select the airline domain, Muse on, and click Run.
  2. Live progress streams: compile → search → verify.
  3. The sidebar "Muse Spark tokens" counter climbs during the run.
  4. Lower-third callouts point at the violet Muse labels.
- **On screen:** lower third `§ Compile · Muse Spark, structured output` → `§ Propose · Muse Spark` → `§ Verify · plain code, τ² simulator`. Corner, at the end: `1997 tool calls · 7 Muse calls · 120,756 tokens · 425 s` with footnote `one run · muse-spark-1.3 · effort low · 05bd65c`.
- **Figures:** F7
- **VO:** "Muse Spark does the reading. It turns the policy into rules a machine can check, and into forbidden goals. Then it proposes chains to try, goal by goal. A blind search fills the rest of the budget. Muse proposes; code decides."

### S8 · 1:08–1:28 · The twist (app, recording R2, plus an overlay)

- **Screen:**
  1. Cut to the Report hero, "No proven holes in the airline policy", with the stat cards.
  2. Hold on the cards: Class A 0, Class B 15, Class C 102. Below, the Class C group headers by goal: G7 100, G1 2.
  3. At "Then we read…", an exhibit overlay slides in: an excerpt of τ²'s gold task 7 scenario ("ask to upgrade to business first and then cancel"), with task numbers 32 and 18 stacked behind it.
- **On screen:** `Class A 0 · Class B 15 · Class C 102` · overlay `EXHIBIT · τ² gold task 7: upgrade, then cancel` · `also: task 32 (2 chains), task 18 (12 chains)`
- **Figures:** F2, F3
- **VO:** "On the tau-two airline policy, the search found fifteen chains that reach a forbidden goal. We expected holes. Then we read the benchmark's own gold tasks. Task seven upgrades a basic economy ticket, then cancels it. Task thirty-two upgrades, then changes flights. Task eighteen takes the other twelve."

### S9 · 1:28–1:42 · Policy vs practice (app, recording R3)

- **Screen:** scroll to the "Policy vs practice" section. The amber goal card stays on the left while the Class B list scrolls on the right. Hover `B6 G2:1ERWZ8`, the row task 7 takes. Do not zoom on the per-row $ column.
- **On screen:** `Class B · policy vs practice` · `tasks 7, 32: the policy is ambiguous (L117 allows the upgrade first)` · `task 18: the policy is silent on bags after a cabin change` · `a hole = no honest trajectory takes it`
- **Figures:** F3, F3b
- **VO:** "So these are not holes. On tasks seven and thirty-two the policy is ambiguous, and practice reads it permissively. On task eighteen it is silent. A hole is a chain no honest trajectory takes."

### S10 · 1:42–1:58 · The proof (app, recording R4)

- **Screen:** open `B6 G2:1ERWZ8`, the finding task 7 takes.
  1. Click Replay. Steps light up one by one, and each step shows its rule id, a ✓ and the cited policy quote.
  2. The final row shows the goal reached and "gold task 7 takes the same chain".
  3. Pan right to "§2 Proof · replays 5/5" and the five ticks.
- **On screen:** `EXHIBIT B6 · trace replay` · `every step: rule ✓ + policy line` · `replays 5/5 · same DB diff on a fresh env`
- **Figures:** the 5/5 replay rule (spec §4); `airline.json` `contradictions[5].replays` = 5/5. The finding's money figure is not narrated.
- **VO:** "Each finding is an executed trace. Every step shows the rule it passed and the policy line behind it. The verifier is plain code: the same database diff on a fresh environment, five times."

### S11 · 1:58–2:16 · Amend, measure, ratify (app, recording R5)

- **Screen:** click "Review amendment".
  1. The policy excerpt shows the inserted sentence underlined in green, with the label "Drafted by Muse Spark".
  2. The backtest tiles fill in: gold tasks replayed, gold tasks blocked, stops the chain.
  3. Click Ratify. The RATIFIED stamp lands, and "Enforced by MCP proxy" lights up.
- **On screen:** `15/15 amendments close their goal` · `each blocks the gold task that sanctions it` · `baseline: 0/43 gold tasks blocked` · `cost shown before ratification` · stamp `RATIFIED`
- **Figures:** F4
- **VO:** "For each finding, Muse drafts a policy sentence and a rule patch. Bylaw proves the patch closes the chain, then replays the gold tasks. Fifteen of fifteen close their goal. Each one blocks the gold task that takes it, against zero of forty-three before."

### S12 · 2:16–2:32 · Enforce (terminal, recording R6)

- **Screen:** a terminal set in the UI mono font on a paper-coloured background, so it matches the app.
  1. `replay --domain airline --gold`, nothing ratified: the 43 tasks scroll by and end with `blocked: 0/43`.
  2. The `G1:1ERWZ8` chain with goal G1 monitored: `0 ALLOWED update_reservation_flights`, then `1 BLOCKED update_reservation_flights BLOCKED G1: basic_economy_flights_changed`.
  3. A small diagram: `your agent → bylaw proxy → τ² tools`.
- **On screen:** `MCP proxy · nothing ratified: 0/43 gold blocked` · `goal G1 monitored: G1:1ERWZ8 BLOCKED at step 1`
- **Figures:** F5, F6
- **VO:** "Ratified rules go into an MCP proxy between the agent and its tools. With nothing ratified, it blocks none of the forty-three gold tasks. With the goal monitored, the chain stops at its second call."

### S13 · 2:32–2:50 · Does Muse earn its place? (app, recording R7, plus motion)

- **Screen:**
  1. The Bench screen, "Muse-guided search against blind BFS".
  2. A motion table sets in row by row, budget 200 tool calls:

     | | Class A | Class B | Class C | tool calls | Muse calls |
     |---|---|---|---|---|---|
     | BFS | 0 | 9 | 2 | 200 | 0 |
     | Muse | 0 | 7 | 48 | 199 | 7 |

     The Class B column is highlighted.
  3. A footnote row appears last.
- **On screen:** table as above · footnote `one run · budget 200 · muse-spark-1.3, effort low · 9f13ae2 · Muse replies served from the audit's cache; the audit cost 7 calls, 120,756 tokens`
- **Figures:** F8, F8b, F7
- **VO:** "Does Muse earn its place in the search? At two hundred tool calls, blind search found nine of these chains, and Muse found seven. One run settles nothing. The audit cost seven Muse calls and about a hundred and twenty-one thousand tokens."

### S14 · 2:50–3:00 · Close

- **Screen:**
  1. The paper background, with three serif lines setting in turn: "Muse proposes." / "Code decides." / "A human ratifies." The last line gets the violet RATIFIED stamp.
  2. Then the Bylaw wordmark, the repo URL and `Built on Muse Spark`.
- **On screen:** as above, plus `github.com/Martinhdeez/meta-hackathon` · `[DP1] live URL if deployed`
- **VO:** "Find the holes in the policy before your agents do. Bylaw. Built on Muse Spark."

## Narration word count

The narration is 408 words. Per scene, S1 to S14: 24, 19, 18, 9, 14, 31, 41, 48, 34, 34, 44, 35, 42, 15.

Command: `grep -o '\*\*VO:\*\* "[^"]*"' .artifacts/todo/2026-10-27-final-video-storyboard.md | sed 's/\*\*VO:\*\* //' | awk '{t+=NF; printf "%d ", NF}END{print "total",t}'`

That is 2.3 words per second on average. The densest scenes are S6 and S8, at about 2.4 w/s. If the generated voice runs long, cut the last S13 sentence, because its footnote carries that figure.

## Recordings from the real app, in order

All recordings run on the merged UI4/UI5 build and the DM1 reports, at 1440×900 (scaled to 1080p), light theme, with the cursor visible. Record each one as its own file.

| # | Scene | Screen | Action | Needs |
|---|---|---|---|---|
| R1 | S7 | Audit | Pick airline, Muse on, Run; capture the whole SSE progress (it gets sped up in the edit) and the token counter in the sidebar | DM1 cached run at `BYLAW_EFFORT=low`, which replays from `.cache/llm/` with no new calls; a different effort misses the cache and bills new tokens |
| R2 | S8 | Report | Land on the hero; hold 4 s on the stat cards and the Class C goal groups | DM1 airline report |
| R3 | S9 | Report | Slow scroll to Policy vs practice; hover `B6 G2:1ERWZ8` | DM1 airline report |
| R4 | S10 | Finding | Open `B6 G2:1ERWZ8`; Replay; step through; pan to §2 Proof | DM1 airline report |
| R5 | S11 | Amendment | Review amendment on B6; wait for the backtest tiles; Ratify; hold on the stamp | DM1 amended report |
| R6 | S12 | Terminal | `uv run python -m bylaw replay --domain airline --gold`, then the G1-monitored replay of `G1:1ERWZ8` (see open items) | no key; keep the terminal at the UI mono font |
| R7 | S13 | Bench | Land on Bench; hold on the chart | DM1 bench |
| R8 | S7 b-roll | Any | Theme toggle light → dark → light; sidebar collapse | UI4/UI5 |

Optional R9: `audit --domain retail --no-llm` ending on the `R6:#W1068289` line, as a 2 s insert under S2. The DM1 run took 372 s (`retail.json` `stats.seconds` 372.28), so record the final output only.

## Judging criteria this covers

| Criterion | Where | What the viewer sees |
|---|---|---|
| Muse Spark use | S6, S7, S11, S13 | Muse compiles the policy (structured output), proposes chains and drafts amendments; violet labels in the app; the audit's Muse cost (F7); the bench against blind search, reported as it came out (F8) |
| What is novel | S1–S5, S8–S9 | It audits the policy, not the agent; findings are proven by execution, not argued; the benchmark's own gold tasks take the chains the goals forbid, and Bylaw files them as policy vs practice instead of inflating a hole count (F2, F3, F3b) |
| The live product | S7–S13 | Real app screens (audit with live progress, report, trace replay, amendment with backtest, ratify), a working MCP proxy in a terminal, measured figures with sources |

## Open items before render

- DM1 (PR #32) merged. If the reports are regenerated, re-run `.scratch/vd2-figures.py` and update the ledger.
- R6 step 2: the `replay` CLI monitors only the goals of ratified amendments, and has no flag to monitor G1 alone. F6 was produced with a short script calling `Proxy(get_domain("airline"), monitor_goals=["G1"])` on the chain of `G1:1ERWZ8` from `reports/airline.json`. Either record that script's output, or add a `--monitor` flag (a builder item).
- REQ-DM1-1 also asks for retail amendments; the retail report is not amended. The video does not need them.
- Amend tokens are not recorded (the amend CLI does not print them), so no amendment cost in tokens is shown.
- A live URL for S14 only if DP1 is deployed with the user's go-ahead.
