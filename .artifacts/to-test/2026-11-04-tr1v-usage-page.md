# TR1-V: Usage page in the console

## Problem

The user asked where to monitor the tokens and AI costs. The console showed only the latest report's token count in the rail. Nothing showed the public deploy's spend against its token cap, the cost of the recorded runs, or the price the estimates use.

## Change

- New screen `#/usage` (`web/src/screens/Usage.tsx`). It has a "Usage" item in the main nav and a ⌘K palette entry. It reads `GET /api/usage` (contract TR1 v1.0):
  - Price: input and output per 1M tokens, the model, the date the price was read, and a link to Meta's pricing page. It is a link only, so the page makes no third-party request.
  - Public deploy:
    - a meter of tokens used out of `token_cap`, split into input and output;
    - sessions and estimated cost;
    - refreshes every 5 s while the tab is visible;
    - a failed refresh keeps the last answer and says so;
    - `enabled: false` shows "Live runs off" and no meter;
    - the meter is amber from 80% of the cap and red at 100%.
  - Recorded runs: one row per ledger entry (stage, label, source path, calls, input, output, tokens, time, cost) and a totals row.
    - Fields the source does not record show "–".
    - When `low != high` the cost shows as a range with an asterisk, and a footnote explains why: only the total was recorded, not the input/output split.
    - With no entries the panel shows an empty state that names `reports/usage.json`.
  - All costs show 4 decimals and are labelled estimates. At phone width the ledger rows become stacked blocks of labelled figures.
- `web/src/api.ts`: `Usage` and `UsageEntry` types and `api.usage()`.
- Shell (`web/src/styles.css`): the sidebar's background now fills the whole page height on desktop. Before, it stopped at one viewport on tall pages. A `.shell::before` in the rail's grid cell paints the column under the sticky rail.
- Phone nav (`web/src/styles.css`): below 440 px the nav items drop their icons. Without this, the fifth item (Usage) made every screen 424 px wide on a 390 px phone, and the 390 px checks in `ui4.spec.ts` and `ui5.spec.ts` failed. This is a change from the approved screenshots, which were taken while the page still scrolled sideways.
- e2e mock: `/api/usage` is served from `web/e2e/fixtures/usage.json`, with a `usage` edit option. The fixture has 5 entries totalling 629,630 tokens, with costs computed by the contract's rule. The live counters grow on each request, so the refresh can be tested.

## Approved

The user approved the prototype as is on 2026-11-04: 4-decimal costs, amber at 80% and red at 100%, stacked blocks on phones. They asked for one fix, the sidebar height.

## Evidence

- Screenshots: `.scratch/after/tr1v/` (usage, usage-empty-off at 1440 and 390; also near-cap, light and error from the prototype round).
- `cd web && E2E_MOCK=1 npx playwright test`: the whole suite passes, including `e2e/tr1.spec.ts`.

## Tests added

- `web/e2e/tr1.spec.ts`: nav to `#/usage`, the price and its link, the meter and its 5 s refresh, the ledger rows and total, the range footnote, the empty ledger with live runs off, and a ledger with no ranges having no footnote.

## Not checked

- The screen against the real `/api/usage`. The builder's route is being built in parallel, so the spec runs on the mock only.
- Browsers other than Chrome. Widths other than 1440 and 390. A screen reader.
