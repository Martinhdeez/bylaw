# UI4 Redesign of the web app ("the policy as a legal record")

Implements the approved prototype (`view/ui4-prototype`, v3 at e4f0cf3: `.artifacts/pages/ui4-redesign-prototype.html`) in `web/src`.
Approved by the user on 2026-10-27 ("approve the prototype, but first do it with more contrast ... and a light theme", then "I approve the prototype").

## What changed

- **Identity:** Source Serif 4 titles and clause text, section marks (§ n) on panels, Art. I–V phases, Docket 01/02 domain cards, "Exhibit" label on the trace, redline insertion on the amendment, a RATIFIED stamp. Violet is the one accent; red = hole, amber = class B, green = allowed / ratified. No background patterns.
- **Themes:** dark (default from `prefers-color-scheme`) and light, on the same tokens. The toggle is a tile in the rail foot, and the choice is kept in `localStorage["bylaw.theme"]`. `index.html` sets `data-theme` before the first paint.
- **Sidebar:** active and hover states are rounded-square tiles with the logo's corner. The UI3 toggle and its key `bylaw.sidebar.collapsed` are unchanged. Collapsed items show tooltips.
- **Command palette:** a "Jump to…" button and ⌘K / Ctrl+K open it (native `<dialog>`).
- **Trace:** a node rail with a moving cursor, and a step bar. ←/→ step the trace. The outcome node is punched when the last call lands.
- **Amendment:** the stamp and the hole-closing seal animate only right after a ratify on that page. On later visits they are static.
- **Numbers:** tickers on the counters and stats. Every figure comes from the API (C9 unchanged). The prototype's sample Muse run is not in the app.
- **Bench:** the lines draw in and the found points pop in. A hover guide reads both modes' counts at any budget.
- **States:** skeleton loading per screen shape; the error, 404 and empty states are restyled.
- **Motion:** transform and opacity only; all of it is off under `prefers-reduced-motion`.
- **Logo:** `web/public/logo.svg` (also the favicon) has the violet hole ring and the wider crack (10 units). It uses a dark tile in light mode. `.artifacts/pages/bylaw-pitch.html` has no logo, so it is unchanged.
- **01 v1.9:** a `bfs-fallback` run reads as an offline run. The report shows the offline tag and an amber "Muse unavailable" notice with the failed call count, and the rail meter reads "Muse unavailable, ran offline". A null `run.model` is left out of the text; `run.effort` is shown when present.

## How to test

- Gate: `make check`.
- Mocked UI: `cd web && E2E_MOCK=1 npx playwright test`. That is 15 tests: the existing screens, sidebar and smoke specs, plus `e2e/ui4.spec.ts`. The new spec covers a bfs-fallback report (mock option `fallback`), the ratify stamp, ←/→ stepping, ⌘K, the theme toggle, and screenshots of both themes at 1440 and 390 with no sideways scroll.
- Real API: `cd web && npx playwright test` (starts uvicorn). Not run for this change: the machine was loaded with parallel gates.

Screenshots: `.artifacts/reports/ui4-app-{dark,light}-{1-audit,2-report,3-hole,4-amendment-ratified,5-bench}-{1440,390}.png` and `ui4-app-{dark,light}-6-collapsed-1440.png`.

## Not checked

- Firefox and Safari.
- Widths between 761 and 1080 px.
- A screen reader pass.
- The real-API Playwright run.
