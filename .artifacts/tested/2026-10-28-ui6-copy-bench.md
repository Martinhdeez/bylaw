# UI6: copy and bench fixes on existing views

Branch `view/ui6-copy-bench` into `bylaw/build`. Iteration 06, REQ-UI6-1..4. No new layout: copy, two table columns, a per-group note line, and one colour rule.

## Changes

1. **REQ-UI6-1, Class B copy.** Class B copy no longer says the policy text forbids the outcome. The wording works for a policy gap (task 18) and for an ambiguity (tasks 7, 32): "A gold task reaches this outcome: the policy and the benchmark's practice disagree."
   - Report: the lede and the Policy vs practice section ("where the policy is silent or ambiguous, its practice reads it permissively").
   - Hole: the lede, the tag "Class B, policy vs practice", and the outcome verdict "forbidden goal, gold does it too".
   - Amendment: the lede and the trade-off line.

   The copy names no goal and no task by itself. It shows only the gold tasks the report names.
2. **REQ-UI6-2, bench classes.** The bench table gains Class B and Class C columns. A bench written before these keys existed shows "–". The lede states the budget and "one run per mode". When neither mode proves a Class A hole, the side panel compares the B and C counts per mode instead of saying only "no ratio". On `reports/airline.bench.json` it shows BFS 9 B / 2 C and Muse 7 B / 48 C at budget 200.
3. **REQ-UI6-3, no Muse accent without a model.** The bench now has one `color(mode)` used by the legend, the table, the chart lines, the dots, the end labels and the hover guide. A `muse` row in a bench with `model: null` is drawn in `--muted`, and its Muse area gradient is not drawn.
4. **REQ-UI6-4, Class C notes per goal.** The single note above the groups is gone. Each goal group's summary carries its own note, visible while the group is collapsed. The note comes from the chain, the same way `report.classify` decides it: a chain that cancels then rebooks is "the method the policy allows", and any other Class C goal (G7) is "pre-registered as an ambiguity, the policy is silent". The Hole screen's Class C lede uses the same helper (`classCWhy` in `ui.tsx`). Before, it also told G7 entries they were a cancel and rebook.
5. **Also fixed:** on the bench chart, the end labels of two modes with the same count overprinted each other ("0 mbse"). The second label now sits one line above.

## Tests

`web/e2e/ui6.spec.ts` has one test per requirement. I ran each against the old `src/` and each failed there, then passed on this branch. `E2E_MOCK=1 npx playwright test`: 30 passed (all specs).

## Screenshots

The screenshots are from the built app (`web/dist`) served by `uvicorn bylaw.api:app --port 8131` on the committed `reports/`, dark theme. The pairs are in `.artifacts/reports/ui6-{before,after}-*.png` and the full set is in `.scratch/after/ui6-copy-bench/`.

## Not checked

- Light theme (the change uses only existing tokens).
- Browsers other than Chrome.
- Widths other than 1440 and 390.
- The live API with a `muse` bench row whose `model` is null (covered by the mock only).
