// Screenshots of every screen on the mock, for design review: SHOTS_DIR=<dir> E2E_MOCK=1 npx playwright test e2e/shots.spec.ts
// SHOTS_THEME=light takes the light theme; SHOTS_DOMAIN=csdemo takes the customer service demo's screens.
import { test } from "@playwright/test";
import { mockApi, storedReport } from "./mock";

const dir = process.env.SHOTS_DIR;
const theme = process.env.SHOTS_THEME === "light" ? "light" : "dark";
const cs = process.env.SHOTS_DOMAIN === "csdemo";
test.skip(!dir || !process.env.E2E_MOCK, "set SHOTS_DIR and E2E_MOCK to take screenshots");

const first = (r: any, cls: "holes" | "contradictions") => r[cls][0]?.key as string;
const report = storedReport();
const key = encodeURIComponent(first(report, "contradictions") ?? first(report, "holes"));
const H6 = encodeURIComponent("D1:LL0EZ6");
const SCREENS: [string, string][] = cs
  ? [["audit", "/#/csdemo/bench"], ["report", "/#/csdemo/report"], ["hole", `/#/csdemo/holes/${H6}`], ["amendment", `/#/csdemo/holes/${H6}/amendment`]]
  : [["audit", "/#/"], ["report", "/#/airline/report"], ["hole", `/#/airline/holes/${key}`], ["amendment", `/#/airline/holes/${key}/amendment`],
     ["bench", "/#/airline/bench"], ["live", "/?at=43.5#/live"]];

for (const width of [1440, 390])
  for (const [name, url] of SCREENS)
    test(`${name} at ${width}`, async ({ page }) => {
      await mockApi(page, cs ? { fixture: "csdemo.report.json" } : {});
      if (theme === "light") await page.addInitScript(() => localStorage.setItem("bylaw.theme", "light"));
      await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
      await page.setViewportSize({ width, height: 900 });
      await page.goto(url);
      // the Audit page has no domain in its route: the last domain visited (csdemo, via its bench) stays picked
      if (cs && name === "audit") await page.goto("/#/");
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(800);
      await page.screenshot({ path: `${dir}/${cs ? "csdemo-" : ""}${name}-${width}${theme === "light" ? "-light" : ""}.png`, fullPage: true });
    });
