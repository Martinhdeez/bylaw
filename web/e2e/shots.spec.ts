// Screenshots of every screen on the mock, for design review: SHOTS_DIR=<dir> E2E_MOCK=1 npx playwright test e2e/shots.spec.ts
import { test } from "@playwright/test";
import { mockApi, storedReport } from "./mock";

const dir = process.env.SHOTS_DIR;
const theme = process.env.SHOTS_THEME === "light" ? "light" : "dark";
test.skip(!dir || !process.env.E2E_MOCK, "set SHOTS_DIR and E2E_MOCK to take screenshots");

const first = (r: any, cls: "holes" | "contradictions") => r[cls][0]?.key as string;
const report = storedReport();
const key = encodeURIComponent(first(report, "contradictions") ?? first(report, "holes"));
const SCREENS: [string, string][] = [
  ["audit", "/#/"],
  ["report", "/#/airline/report"],
  ["hole", `/#/airline/holes/${key}`],
  ["amendment", `/#/airline/holes/${key}/amendment`],
  ["bench", "/#/airline/bench"],
  ["live", "/?at=43.5#/live"],
];

for (const width of [1440, 390])
  for (const [name, url] of SCREENS)
    test(`${name} at ${width}`, async ({ page }) => {
      await mockApi(page);
      if (theme === "light") await page.addInitScript(() => localStorage.setItem("bylaw.theme", "light"));
      await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
      await page.setViewportSize({ width, height: 900 });
      await page.goto(url);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(800);
      await page.screenshot({ path: `${dir}/${name}-${width}${theme === "light" ? "-light" : ""}.png`, fullPage: true });
    });
