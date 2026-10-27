# VD1 — Final video: script and storyboard

Status: draft for review, 2026-10-27. Nothing is rendered. Rendering waits for UI4 (redesign) and DM1 (live reports) to merge.

- Length: 3:00, 1920×1080, 30 fps. Narration in English, about 420 words.
- Format: a ≈50 s hook in motion graphics, then the real app, then a closing card.
- Style: the UI4 legal record. Serif headings, § numbers, "Exhibit" labels, the RATIFIED stamp, violet accent. The hook and the app use the same palette, so the cut from graphics to the app should not stand out. The hook is in dark theme. The app recordings are in light theme, plus one theme-toggle shot.
- Tone: plain statements, each tied to a measured figure. Do not use words like "revolutionary", "unprecedented" or "AI-powered", stock "AI" imagery, glowing brains, or a counter that runs up to a number nobody measured.

## Figure ledger

Only these figures may appear, on screen or in the narration. Each scene cites its figures by ledger id.

| Id | Figure | Source |
|---|---|---|
| F1 | Retail `R6:#W1068289`, Class A: payment switch, then cancel; 5/5 replays; money_delta $10,359.84 | `audit --domain retail --no-llm`, SR1 note `.artifacts/to-test/2026-10-27-sr1-retail-search.md` (branch `sr1-ff`, commit 0fc8caa), evidence `audit-retail-v18-stdout.txt` |
| F2 | Airline after gold adjudication: 0 Class A, 15 Class B, 2 Class C | `audit --domain airline --no-llm`, classified under contract 01 v1.7; decision `docs/plan/decisions-2026-10-27-gold-adjudication.md` |
| F3 | τ² gold tasks take the chains: task 7 (upgrade to business, then cancel), and tasks 32, 18 and 25 | same decision note; PX1 gold replay with the goal monitor (`docs/plan/04-proxy/99-close.md`) |
| F4 | Amendments: 15/15 close their goal; each blocks the gold task that sanctions it; baseline 0/43 | `amend report.json` at 74fce98, AM1 `amend-table.md` (`docs/plan/02-amend/99-close.md`) |
| F5 | Proxy, nothing ratified: airline gold 0/43 blocked | `replay --domain airline --gold`, PX1 (`docs/plan/04-proxy/99-close.md`) |
| F6 | Proxy, goal G1 monitored: hole `G1:1ERWZ8` step 0 allowed, step 1 BLOCKED | PX1 `replay-holes.txt` (`docs/plan/04-proxy/99-close.md`) |
| F7 | Bench, one run, Class A found, BFS vs Muse, at budgets 25/50/100/200/2000: 1/2, 4/4, 7/8, 9/38, 15/18; about 185k tokens and 7 LLM calls per Muse run | `bench --domain airline --modes bfs,muse` at c4c136f, PR1 `bench-summary.txt` (`docs/plan/01-engine/99-close.md`). Counted before v1.7, when every finding was Class A |
| [DM1] | Live-report figures: run time, tool calls, Muse tokens, compiler match rate, per-finding money | DM1 reports under `reports/`, not merged yet. Fill in each `[DM1]` slot from the committed files |

**Withdrawn, do not reuse:** "−$48,200" and every similar placeholder; "−$8,581"; "3 holes found" (insurance and passenger-count are Class C); "50/50" and "42/43 past cases replayed, 0 honest customers blocked" (each amendment blocks a gold task, see F4); the "0 tokens · 1M context" counter; "Muse Spark · video"; "Muse Spark Open / open weights / never leaves the building" (stretch goals, not built); the boarding-pass "cancel + rebook = changed" hole (Class C: Muse itself reads it as the permitted 24 h method).

**UI fixture figures:** the UI4 screenshots show offline fixture values ($840, $8,736, 412,880 tokens, 14 LLM calls, "1.4×"). They are not in the ledger. The recordings must run on the DM1 reports, and the narration never reads a per-row figure.

## Scene list

| # | Time | Dur | Part | Screen |
|---|---|---|---|---|
| S1 | 0:00–0:09 | 9 s | Hook | Motion: retail order exhibit, two allowed steps, refund twice |
| S2 | 0:09–0:16 | 7 s | Hook | Motion: money_delta and 5/5 replays |
| S3 | 0:16–0:24 | 8 s | Hook | Motion: "suspects cleared" (from v8) |
| S4 | 0:24–0:29 | 5 s | Hook | Motion: "The agent did nothing wrong. The law was wrong." (from v8) |
| S5 | 0:29–0:37 | 8 s | Hook | Motion: guardrails vs the law (from v8) |
| S6 | 0:37–0:50 | 13 s | Hook | Motion: you give / you get, "Built on Muse Spark" |
| S7 | 0:50–1:08 | 18 s | Product | App: Audit, live run on airline |
| S8 | 1:08–1:28 | 20 s | Product | App: Report hero, then a gold task 7 overlay |
| S9 | 1:28–1:42 | 14 s | Product | App: Report, Policy vs practice list |
| S10 | 1:42–1:58 | 16 s | Product | App: Finding page, trace replay, proof 5/5 |
| S11 | 1:58–2:16 | 18 s | Product | App: Amendment, backtest tiles, Ratify, stamp |
| S12 | 2:16–2:32 | 16 s | Product | Terminal: proxy replay, gold 0/43, then BLOCKED |
| S13 | 2:32–2:50 | 18 s | Product | App: Bench, plus a motion budget table |
| S14 | 2:50–3:00 | 10 s | Close | Motion: closing card |

Hook S1–S6 = 50 s.

## Storyboard and narration

### S1 · 0:00–0:09 · Cold open (motion, replaces the v8 boarding pass)

- **Screen:** a retail order shown as a legal exhibit card ("EXHIBIT A · order #W1068289") on a dark paper background. Two ruled lines appear in turn, each stamped with a green ✓: `modify payment method` and `cancel order`. A refund line then prints twice, and the second copy is underlined in red.
- **On screen:** `EXHIBIT A · #W1068289` · `✓ allowed` · `✓ allowed` · `refunded twice`
- **Figures:** F1
- **VO:** "An agent switches the payment method on an order. Then it cancels the order. The store's policy allows each step. The refund goes out twice."

### S2 · 0:09–0:16 · The amount

- **Screen:** the exhibit slides left. A large serif figure sets in like a ledger entry, and five small replay boxes tick on one at a time.
- **On screen:** `money_delta  $10,359.84` · `replays 5/5` · footnote `τ²-bench retail simulator · audit --domain retail`
- **Figures:** F1
- **VO:** "Ten thousand, three hundred and fifty-nine dollars, in the tau-two retail simulator. Five replays out of five."

### S3 · 0:16–0:24 · Suspects cleared (kept from v8)

- **Screen:** the v8 sequence. Three tiles (Jailbreak, Attacker, Agent bug) are crossed out one by one, and the counter goes from `SUSPECTS CLEARED 1/3` to `3/3`. Restyle from neon to the legal-record palette, so a strike-through replaces the crosshair.
- **On screen:** `Jailbreak` · `Attacker` · `Agent bug` · `SUSPECTS CLEARED 3/3`
- **VO:** "No jailbreak. No attacker. No bug in the agent. It followed every rule it was given."

### S4 · 0:24–0:29 · The line (kept from v8)

- **Screen:** two serif lines on paper. "The law was wr…" types out and finishes as "wrong."
- **On screen:** `The agent did nothing wrong.` / `The law was wrong.`
- **VO:** "The agent did nothing wrong. The law was wrong."

### S5 · 0:29–0:37 · Nobody checks the law (kept from v8)

- **Screen:** the v8 split. On the left, "Guardrails → check the agent" with a shield. On the right, "The policy → checked by nobody". The right half then turns into the Bylaw wordmark.
- **On screen:** `Guardrails check the agent.` · `Nobody checks the law.` · `bylaw`
- **VO:** "Guardrails check the agent against the policy. Nobody checks the policy itself. Bylaw does."

### S6 · 0:37–0:50 · What it is (rewritten from v9 "You give / You get")

- **Screen:** two columns, set like the § sections of a filing.
  - YOU GIVE: `the agent's tools` · `its policy` · `a sandbox`.
  - YOU GET: four items, in order: `§1 holes, executed` · `§2 amendments, drafted` · `§3 their cost, measured` · `§4 a proxy, enforcing`.
  - A violet tag sets at the end: `Built on Muse Spark · Meta Model API`.
- **On screen:** as above.
- **VO:** "Give it an agent's tools, its policy and a sandbox. It returns the forbidden chains it executed, an amendment for each, what each amendment costs, and a proxy that enforces it."

### S7 · 0:50–1:08 · Audit (app, recording R1)

- **Screen:** UI4 Audit screen in light theme.
  1. Select the airline domain, Muse on, and click Run.
  2. Live progress streams: compile → search → verify.
  3. The sidebar "Muse Spark tokens" counter climbs during the run.
  4. Lower-third callouts point at the violet labels "Compiled by Muse Spark" and "Chains proposed by Muse Spark, high reasoning".
- **On screen:** lower third `§ Compile · Muse Spark, structured output` → `§ Propose · Muse Spark, high reasoning` → `§ Verify · plain code, τ² simulator`. Corner: `[DM1] tool calls · [DM1] tokens · [DM1] s`. Optional, if DM1 reports it: `[DM1] compiler match rate`.
- **Figures:** [DM1] only
- **VO:** "Muse Spark does the reading. It compiles the policy text into rules a machine can check, and into forbidden goals. Then it proposes chains to try, goal by goal. A blind search fills the rest of the budget. Muse proposes; code decides."

### S8 · 1:08–1:28 · The twist (app, recording R2, plus an overlay)

- **Screen:**
  1. Cut to the Report hero, "No proven holes in the airline policy", with the stat cards.
  2. Hold on the cards: Class A 0, Class B 15, Class C 2.
  3. At "Then we checked…", an exhibit overlay slides in: an excerpt of τ²'s gold task 7 scenario ("ask to upgrade to business first and then cancel"), with task numbers 32, 18 and 25 stacked behind it.
- **On screen:** `Class A 0 · Class B 15 · Class C 2` · overlay `EXHIBIT · τ² gold task 7: upgrade, then cancel` · `also: tasks 32, 18, 25`
- **Figures:** F2, F3
- **VO:** "On the tau-two airline policy, the search found fifteen chains that reach outcomes the policy forbids. We expected holes. Then we read the benchmark's own gold tasks. Task seven upgrades a basic economy ticket, then cancels it. Tasks thirty-two, eighteen and twenty-five take the others."

### S9 · 1:28–1:42 · Policy vs practice (app, recording R3)

- **Screen:** scroll to the "Policy vs practice" section. The amber G-goal card stays on the left while the B-row list scrolls on the right. Hover the row whose chain task 7 takes. Do not zoom on the per-row $ column (fixture figures).
- **On screen:** `Class B · contradiction: the text forbids it, the gold does it` · `a hole = no honest trajectory takes it`
- **Figures:** F2
- **VO:** "So these are not holes. The written policy and the graded practice disagree. Bylaw files them as contradictions. A finding counts as a hole only when no honest trajectory takes it."

### S10 · 1:42–1:58 · The proof (app, recording R4)

- **Screen:** open the finding that task 7 sanctions.
  1. Click Replay. Steps light up one by one, and each step shows its rule id, a ✓ and the cited `policy.md:<line>` quote.
  2. The final row turns to "forbidden by the text, done by gold".
  3. Pan right to "§2 Proof · replays 5/5" and the five ticks.
- **On screen:** `EXHIBIT B·n · trace replay` · `every step: rule ✓ + policy line` · `replays 5/5 · same DB diff on a fresh env`
- **Figures:** the 5/5 replay rule (spec §4). The finding's own money figure stays [DM1] and is not narrated.
- **VO:** "Each finding is an executed trace. Every step shows the rule it passed and the policy line behind it. The verifier is plain code: the same database diff on a fresh environment, five times."

### S11 · 1:58–2:16 · Amend, measure, ratify (app, recording R5)

- **Screen:** click "Review amendment".
  1. The policy excerpt shows the inserted sentence underlined in green, with the label "Drafted by Muse Spark, high reasoning".
  2. The backtest tiles fill in: gold tasks replayed, gold tasks blocked, stops the chain.
  3. Click Ratify. The RATIFIED stamp lands, and "Enforced by MCP proxy" lights up.
- **On screen:** `15/15 amendments close their goal` · `each blocks the gold task that sanctions it` · `baseline: 0/43 gold tasks blocked` · `cost shown before ratification` · stamp `RATIFIED`
- **Figures:** F4
- **VO:** "For each finding, Muse drafts a policy sentence and a rule patch. Bylaw proves the patch closes the chain, then replays the gold tasks. Fifteen of fifteen close their goal. Each one blocks the gold task that sanctions it, against zero of forty-three before."

### S12 · 2:16–2:32 · Enforce (terminal, recording R6)

- **Screen:** a terminal set in the UI4 mono font on a paper-coloured background, so it matches the app.
  1. `replay --domain airline --gold`, nothing ratified: the 43 tasks scroll by and end with `0/43 blocked`.
  2. `replay --domain airline --hole G1:1ERWZ8` with G1 monitored: `step 0 allowed`, then `step 1 BLOCKED: G1`.
  3. A small diagram: `your agent → bylaw proxy → τ² tools`.
- **On screen:** `MCP proxy · nothing ratified: 0/43 gold blocked` · `goal G1 monitored: G1:1ERWZ8 BLOCKED at step 1`
- **Figures:** F5, F6
- **VO:** "Ratified rules go into an MCP proxy between the agent and its tools. With nothing ratified, it blocks none of the forty-three gold tasks. With the goal monitored, the chain stops at its second call."

### S13 · 2:32–2:50 · Does Muse earn its place? (app, recording R7, plus motion)

- **Screen:**
  1. The Bench screen, "Muse-guided search against blind BFS", with its step chart.
  2. A motion table replaces the chart's numbers, because the bench screen shows one budget and the ledger has five. The columns set one by one: budgets 25 / 50 / 100 / 200 / 2000; BFS 1 / 4 / 7 / 9 / 15; Muse 2 / 4 / 8 / 38 / 18. The 200 column is highlighted.
  3. A footnote row appears last.
- **On screen:** table as above · footnote `one run per budget · ≈185k tokens, 7 Muse calls per run · counted before gold adjudication`
- **Figures:** F7
- **VO:** "Does Muse earn its place? The same budget, Muse-guided against blind search. At two hundred tool calls, Muse proved thirty-eight findings, against nine. At every budget it found at least as many. One run each, about a hundred and eighty-five thousand tokens."

### S14 · 2:50–3:00 · Close

- **Screen:**
  1. The paper background, with three serif lines setting in turn: "Muse proposes." / "Code decides." / "A human ratifies." The last line gets the violet RATIFIED stamp.
  2. Then the Bylaw wordmark, the repo URL and `Built on Muse Spark`.
- **On screen:** as above, plus `github.com/Martinhdeez/meta-hackathon` · `[DM1/DP1] live URL if deployed`
- **VO:** "Find the holes in the law before your agents do. Bylaw. Built on Muse Spark."

## Narration word count

The narration is 400 words. Per scene, S1 to S14: 25, 17, 16, 9, 14, 31, 42, 45, 31, 34, 44, 35, 42, 15.

Command: `grep -o '\*\*VO:\*\* "[^"]*"' .artifacts/todo/2026-10-27-final-video-storyboard.md | sed 's/\*\*VO:\*\* //' | awk '{t+=NF; printf "%d ", NF}END{print "total",t}'`

That is 2.2 words per second on average. The densest scenes are S6 and S11, at about 2.4 w/s. If the generated voice runs long, cut the S13 last sentence ("One run each…"), because its footnote already carries that figure.

## Recordings from the real app, in order

All recordings run on the merged UI4 build and the DM1 reports, at 1440×900 (scaled to 1080p), light theme, with the cursor visible. Record each one as its own file.

| # | Scene | Screen | Action | Needs |
|---|---|---|---|---|
| R1 | S7 | Audit | Pick airline, Muse on, Run; capture the whole SSE progress (it gets sped up in the edit) and the token counter in the sidebar | UI4, live key (or the DM1 cached run, which replays from `.cache/llm/` with no new calls) |
| R2 | S8 | Report | Land on the hero; hold 4 s on the stat cards | DM1 airline report |
| R3 | S9 | Report | Slow scroll to Policy vs practice; hover the task-7 row | DM1 airline report |
| R4 | S10 | Finding | Open the task-7 finding; Replay; step through; pan to §2 Proof | DM1 airline report |
| R5 | S11 | Amendment | Review amendment; wait for the backtest tiles; Ratify; hold on the stamp | DM1 amended report |
| R6 | S12 | Terminal | `uv run python -m bylaw replay --domain airline --gold`, then `... replay --domain airline --hole G1:1ERWZ8` with G1 monitored | no key; keep the terminal at the UI4 mono font |
| R7 | S13 | Bench | Land on Bench; hold on the chart | DM1 bench |
| R8 | S7 b-roll | Any | Theme toggle light → dark → light; sidebar collapse | UI4 |

Optional R9: `audit --domain retail --no-llm` ending on the `R6:#W1068289` line, as a 2 s insert under S2. Take it only if the S1–S2 motion graphic needs proof on screen. The run took 361 s on a loaded machine, so record the final output only.

## Judging criteria this covers

| Criterion | Where | What the viewer sees |
|---|---|---|
| Muse Spark use | S6, S7, S11, S13 | Muse compiles the policy (structured output), proposes chains (high reasoning effort) and drafts amendments; violet labels in the app; the Muse vs blind-search bench with tokens and call count (F7) |
| What is novel | S1–S5, S8–S9 | It audits the policy, not the agent; holes are proven by execution, not argued; the gold-adjudication finding (F2, F3): the benchmark's own graded practice takes chains its text forbids, and Bylaw separates contradictions from holes instead of inflating a count |
| The live product | S7–S13 | Real app screens (audit with live progress, report, trace replay, amendment with backtest, ratify), a working MCP proxy in a terminal, measured figures with sources |

## Open items before render

- UI4 merged; DM1 reports committed. Fill every `[DM1]` slot from those files.
- Check the F1 wording ("refunded twice", "money_delta $10,359.84") against the SR1 hole record before the voice-over is generated, in case the refund is not the full amount twice.
- Confirm that the task-7 finding id in the DM1 report exists, and use it for R3 and R4.
- The UI4 prototype HTML and the `ui4-v2-*.png` screenshots named in the brief were not found. This storyboard follows the UI4 app screenshots `ui4-app-{light,dark}-*-1440.png` in the `view/ui4-redesign` worktree's `.artifacts/reports/`.
- A live URL for S14 only if DP1 is deployed with the user's go-ahead.
