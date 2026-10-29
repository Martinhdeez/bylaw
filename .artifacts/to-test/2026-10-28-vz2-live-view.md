# VZ2: Live view (web)

Branch `view/vz2-live`. The reference is the approved prototype `docs/plan/06-showcase/mocks/vz1-live-v4-3.html` (commit 23ecbff on `view/vz1-prototype`). The user approved it on 2026-10-28; the coordinator relayed the approval.

## What changed

- New route `#/live` with a "Live" nav entry and a palette item. The screen is `web/src/screens/Live.tsx` with `live.css`.
- Data comes from `GET /api/live` and `GET /api/live/{file}` (CS-C3 v1.2). The view pairs the unguarded and the guarded file of one script name. If one file is missing, it plays the other alone and shows the missing side as "not recorded".
- The timeline runs in three parts: without Bylaw, with Bylaw, then the result side by side. The player has play/pause, 1x/2x speed, a scrub bar, and Without / With / Result jumps. Without and With keep the same moment in the other run. "Show tool calls" reveals the literal call and the tool output.
- Layout:
  - Customer chat.
  - Action stream. Each tool call is one row: the agent's proposal sits beside Bylaw's decision, with counts above. A blocked row shows the rule id and the policy sentence and expands to what the agent was told. The focal row is the latest action. A handoff trail is shown.
  - Ledger. It is a neutral panel and turns paper (the receipt) once vouchers are issued.
- Figures come only from the event files: voucher strings, case id and booking from the state diffs and `final_state`. The face value is summed from the voucher strings only when every voucher states an amount. Otherwise it reads "not stated".
- `?film=1` hides the app rail and the player chrome, and autoplays. `?at=<seconds>` opens at a moment.
- The Live view defaults to dark when no theme is stored. Other screens still follow the system. The theme toggle and tokens are unchanged.
- Fira Sans and Fira Code are loaded for this screen only.
- On phones the nav items are tighter, so four items fit at 390 px.

## Review round (2026-10-29)

- The brand bar the user asked for now heads the Live view: the 72px mark with its crack, the wordmark and the tagline, next to the app rail. `Logo` takes a mask id, so the mark still renders when the rail is hidden in film mode.
- Fixes from an independent screenshot critique (impeccable-finish-reviewer) against v4.3:
  - The deciding row is the focal card: 22px title and a 16px verdict. A row that would be blocked but is not enforced gets a dashed outline.
  - A denied row names the rule id and the flight fact from the run's state. The policy sentence moves under "Policy source".
  - Counts use the rows' own words.
  - The headline has two tones, stays on one line and carries the stake from the data. The metadata sits under the subtitle.
  - Rows stack at 1240 px and below. Trail chips have no orphan connectors. The lists stay scrolled to the end after the fonts load.
  - The ledger shows ruled voucher rows with right-aligned amounts, and the total sits directly under them.
  - The result cards show Customer, Proposal, Flight data, Decision, then the figure with its explanation.
  - On phones the chat comes first.
- The Impeccable detector runs on the built page (Vite against a static copy of the fixtures) at 1440 for both runs and the result, and at 390. One finding remains: the app rail's 11 px data-source line, which was already there before this change. The glowing violet shadow on the active nav item was removed.

## Real API check (2026-10-29)

After CS3 merged, I checked the view against the real `uvicorn bylaw.api:app` with `BYLAW_REPORTS_DIR` set to a scratch dir. Its `live/` folder held the CS3 recording `cs3-csdemo-d1-guard.json`: a guarded run in which nothing was blocked and $280 was paid out.

- The list, the file and the playback all rendered from the real data, with no page errors and no horizontal scroll at 1440, 1240 and 390.
- One fix: with a single run recorded, the result headline now states what that run paid and that the other run is missing ("$280 with Bylaw. The run without it is not recorded."). Before, it read as if both runs were compared.
- No event file is committed.

## Deviations from the reference

- The reference's Audit and Fix chapters are not in this view. Event files carry no audit or amendment data, and their counts were placeholders. The view plays the two recorded runs and the result.
- Transport and seg labels say "Without Bylaw / With Bylaw / Result" instead of "Before / After".

## How to test

- `cd web && E2E_MOCK=1 npx playwright test e2e/live.spec.ts`. The suite covers:
  - Smoke at 1440, 1240 and 390.
  - The light theme.
  - One visible element per slot after 13 jumps, scrubs and toggles at three widths.
  - Film mode.
  - The empty state.
  - The one-run-only state.
- `SHOTS=1` also writes screenshots to `.scratch/after/vz2-live/`.
- Fixtures: `web/e2e/fixtures/live/csdemo-d1.json` and `csdemo-d1-guard.json` follow CS-C3 v1.2. They are rebuilt from the VZ1 spike transcripts until DM2 records real files. The rule id `R-comp-disrupted` is a placeholder.
- With the real API (after CS3 merges): record the files with `python -m bylaw live ... -o reports/live/<file>.json` and open `#/live`.

## Depends on

- CS3 (`feat/cs3-guard-live`) for `/api/live` on the integration branch.
- DM2 for real event files.
