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

## Deviations from the reference

- The reference's Audit and Fix chapters are not in this view. Event files carry no audit or amendment data, and their counts were placeholders. The view plays the two recorded runs and the result.
- Transport and seg labels say "Without Bylaw / With Bylaw / Result" instead of "Before / After".
- The brand bar stays the app's rail: the screen lives inside the app.

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
