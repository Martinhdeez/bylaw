# RA2: csdemo in the web UI

Branch `view/ra2-web-csdemo`, from `bylaw/build` at 68460d5 (after RA1, #43). This is a designer ask from the RA1 builder.

## What changed

- `web/src/api.ts`: `Domain` and `DOMAINS` now include `csdemo`. The router in `main.tsx` uses `DOMAINS`, so `#/csdemo/report`, `#/csdemo/holes/<key>[/amendment]` and `#/csdemo/bench` now resolve to csdemo. Before this change they fell back to the Audit page and the airline domain. Ratify on a csdemo hole now posts `?domain=csdemo`.
- `web/src/screens/Audit.tsx`: the picker has a third card, "Airline customer service (OpenAI demo)". It lists the demo's write tools.
- `web/src/screens/Bench.tsx`: on csdemo, the Bench page says "No bench for this domain" and explains that the demo is audited and enforced, not benchmarked. It does not suggest the bench command, because the API returns 404 for csdemo by design.
- `web/e2e/mock.ts`: the mock returns 404 on `/api/bench?domain=csdemo`, as the API does.
- `web/e2e/fixtures/csdemo.report.json`: a copy of `reports/csdemo.json` (DM2).
- `web/e2e/smoke.spec.ts`: the airline radio selector is now `/τ² Airline/`. Before, `/Airline/` also matched the new card.

## Tests

`web/e2e/ra2.spec.ts` has three tests:

1. Ratify on H6 `D1:LL0EZ6` posts to `/api/holes/D1:LL0EZ6/ratify?domain=csdemo`.
2. The Audit picker offers and selects the demo.
3. Bench on csdemo shows the "no bench" state.

All three fail on the old `web/src`, and all three pass with the change. The full mock suite passes: 45 tests.

## How to check

```
cd web && E2E_MOCK=1 npx playwright test e2e/ra2.spec.ts
```

Screenshots at 1440 and 390 are in `.scratch/after/ra2-web-csdemo/`: audit, report, amendment and bench, all on csdemo except audit.

## Not done

- Headings and crumbs show the domain id, as in "7 proven holes in the csdemo policy". A display name for each domain would touch every screen. It fits better with the UI7 restyle.
- In the ⌘K palette, "Switch to <other>" picks the first other domain. With three domains, it no longer reaches every domain.
- I did not check the real API end to end (`uvicorn` plus Ratify on csdemo). The mock serves the real report file.
