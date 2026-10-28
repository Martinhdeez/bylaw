# UI5: view fixes inside the UI4 design

Branch `view/ui5-fixes` into `bylaw/build`. No new layout or visual language: one native `<details>` row per goal in the existing Class C panel, reusing the `.amb` row grid, tokens and focus ring.

## Changes

1. **bfs-fallback (01 v1.9).** Already handled on `05bd65c`: the sidebar meter says "Muse unavailable, ran offline", the report shows the offline tag plus the "Muse unavailable" note, and the hole screen shows "Hand RuleSet". Nothing else branches on `run.mode === "muse"`. No code change. A new test checks that the run line names neither a model nor a context for this mode.
2. **Class C grouped by goal.** `Report.tsx` groups ambiguities by goal. Each group is collapsed by default and shows the goal id, the goal name and "N entries". Class A and B are unchanged.
3. **Bench copy follows the bench JSON.** If the top-level `model` is `null`, the bench has no Muse. The title becomes "Blind BFS search", the lede says "No Muse Spark in this bench", and the Muse badge and ratio claim go away. A `muse` row with `model: null` is labelled "Muse unavailable" in the legend, the table and the chart summary. A bench without a `model` key (written before v1.9) keeps the old behaviour.
4. **`--modes bfs,muse` hint.** The flag is now a `<code>` that cannot wrap (`.ratio code { white-space: nowrap }`).
5. **Tests.** New `web/e2e/ui5.spec.ts` with fixture `web/e2e/fixtures/airline.muse.report.json`: a `muse` run with effort `high`, `context_tokens` 41230, `stats.per_goal`, 4 Class A holes, and 100 Class C entries (98 of them G7, one per user, v1.11). It covers:
   - the model, effort and context badges and the run line
   - the amendment effort badge
   - a missing `context_tokens` shown as unknown
   - the bfs-fallback display
   - Class C grouping, collapse and expand
   - both bench copy cases
   - screenshots

   `mock.ts` gains the `fixture`, `edit` and `bench` options. `screens.spec.ts` opens the group before it clicks a Class C row.
6. **Run metadata.** For `muse` runs the Run tile adds "peak context N tokens", or "peak context unknown" when `run.context_tokens` is missing (never 0). `stats.per_goal` is not shown, because the Run tile has no room for a per-goal table.

## Verification

- `E2E_MOCK=1 npx playwright test`: 26 passed (all specs, mock API).
- `harness-gate` (`make check`: offline pytest + `npm run build`): `gate: GREEN at 4427533` (the code commit; the next commit adds only this note and the screenshots).

## Screenshots (`.artifacts/reports/`)

| | Dark | Light |
|---|---|---|
| Class C, before | `ui5-before-dark-2-report-class-c-1440.png` | `ui5-before-light-2-report-class-c-1440.png` |
| Class C, after (collapsed) | `ui5-after-dark-2-report-class-c-1440.png` | `ui5-after-light-2-report-class-c-1440.png` |
| Class C, after (G7 open) | `ui5-after-dark-2b-report-class-c-open-1440.png`, `-390.png` | `ui5-after-light-2b-report-class-c-open-1440.png` |
| Bench bfs-only, before | `ui5-before-dark-3-bench-bfs-only-1440.png` | `ui5-before-light-3-bench-bfs-only-1440.png` |
| Bench bfs-only, after | `ui5-after-dark-3-bench-bfs-only-1440.png` | `ui5-after-light-3-bench-bfs-only-1440.png`, `-390.png` |
| Muse report, after (run line) | `ui5-after-dark-1-report-muse-1440.png` | `ui5-after-light-1-report-muse-1440.png` |

The full set (1440 and 390, both themes) is in `.scratch/after/ui5-view-fixes/`.

## Not checked

- Browsers: Chrome only.
- Widths: 1440 and 390 only.
- The Playwright suite against the real API: it ran on the mock only.
- The Class C note ("Cancel and rebook…") still sits at panel level and describes G1 only. With a G7 group it reads as if it covered every group. Moving it into the G1 group is a one-line follow-up if wanted.
