// UI5: Muse badges follow the data (01 v1.9, v1.10), Class C grouped by goal, bench copy follows the bench JSON.
// fixtures/airline.muse.report.json: a hand-made `muse` report (effort high, context_tokens, stats.per_goal)
// with 98 G7 ambiguities, one per user, built from airline.report.json.
import { expect, test } from "@playwright/test";
import { BFS_BENCH, mockApi } from "./mock";

const MUSE = "airline.muse.report.json";
test.skip(!process.env.E2E_MOCK, "these checks run on the mock's fixtures");

test("a muse run shows its model, effort and context in the badges and the run line", async ({ page }) => {
  await mockApi(page, { fixture: MUSE });
  await page.goto("/#/airline/report");
  await expect(page.getByText("Rules compiled by Muse Spark")).toBeVisible();
  await expect(page.getByText("Chains proposed by Muse Spark")).toBeVisible();
  const run = page.getByTestId("run-meta");
  await expect(run).toContainText("mode muse, model muse-spark-1.3, effort high");
  await expect(run).toContainText("peak context 41,230 tokens");
  await expect(page.locator(".meter")).toContainText("14 calls, muse-spark-1.3");
});

test("the amendment badge carries the run's effort", async ({ page }) => {
  await mockApi(page, { edit: (r) => (r.run.effort = "high") });
  await page.goto("/#/airline/report");
  await page.locator(".instances a", { hasText: "Amendment ready" }).first().click();
  await page.getByRole("link", { name: "Review amendment" }).click();
  await expect(page.getByText("Drafted by Muse Spark, high effort")).toBeVisible();
});

test("a report without context_tokens says unknown, never 0 (01 v1.10)", async ({ page }) => {
  await mockApi(page, { fixture: MUSE, edit: (r) => delete r.run.context_tokens });
  await page.goto("/#/airline/report");
  await expect(page.getByTestId("run-meta")).toContainText("peak context unknown");
});

test("bfs-fallback shows no Muse badge and a Muse unavailable note", async ({ page }) => {
  await mockApi(page, { fallback: true });
  await page.goto("/#/airline/report");
  await expect(page.getByTestId("muse-unavailable")).toContainText("Muse unavailable");
  await expect(page.getByText("Offline run: hand RuleSet, blind BFS")).toBeVisible();
  await expect(page.locator(".tags .muse", { hasText: "compiled" })).toHaveCount(0);
  await expect(page.getByTestId("run-meta")).not.toContainText("model");
  await expect(page.getByTestId("run-meta")).not.toContainText("context");
  await expect(page.locator(".meter")).toContainText("Muse unavailable, ran offline");
});

test("class C groups by goal, collapsed, with a count", async ({ page }) => {
  await mockApi(page, { fixture: MUSE });
  await page.goto("/#/airline/report");
  const groups = page.getByTestId("amb-goal");
  await expect(groups).toHaveCount(2);
  const g7 = groups.filter({ hasText: "G7" });
  await expect(g7.locator("summary")).toContainText("98");
  await expect(g7.locator("li").first()).toBeHidden();
  await g7.locator("summary").click();
  await expect(g7.locator("li")).toHaveCount(98);
  await expect(g7.locator("li").first()).toBeVisible();
  await expect(groups.filter({ hasText: "G1" }).locator("li").first()).toBeHidden();
});

test("a bench with model null claims no Muse", async ({ page }) => {
  await mockApi(page, { bench: BFS_BENCH });
  await page.goto("/#/airline/bench");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Blind BFS search");
  await expect(page.locator(".page")).not.toContainText("Muse Spark proposes");
  await expect(page.locator(".head .muse")).toHaveCount(0);
  await expect(page.locator(".ratio code")).toHaveText("--modes bfs,muse");
});

test("a bench whose Muse row got no model reads as Muse unavailable", async ({ page }) => {
  await mockApi(page, { bench: { ...BFS_BENCH, rows: [BFS_BENCH.rows[0], { ...BFS_BENCH.rows[0], mode: "muse", llm_calls: 3 }] } });
  await page.goto("/#/airline/bench");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Blind BFS search");
  await expect(page.locator(".page")).toContainText("Muse unavailable");
  await expect(page.locator(".ratio")).not.toContainText("more with Muse");
});

// UI5_SHOT=before|after names the files; the change note links them.
const OUT = `../.scratch/after/ui5-view-fixes/${process.env.UI5_SHOT ?? "after"}`;
for (const theme of ["dark", "light"] as const) {
  for (const [w, h] of [[1440, 900], [390, 844]]) {
    test(`ui5 screens, ${theme}, ${w}px`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: h });
      await page.addInitScript((t) => localStorage.setItem("bylaw.theme", t), theme);
      const shot = async (name: string, full = false) => {
        await page.mouse.move(w - 4, h - 4);
        await page.waitForTimeout(1200);
        expect(await page.evaluate(() => document.documentElement.scrollWidth), `${name} scrolls sideways`).toBeLessThanOrEqual(w);
        await page.screenshot({ path: `${OUT}-${theme}-${name}-${w}.png`, fullPage: full });
      };
      await mockApi(page, { fixture: MUSE, bench: BFS_BENCH });
      await page.goto("/#/airline/report");
      await expect(page.locator(".instances a").first()).toBeVisible();
      await shot("1-report-muse");
      await page.locator(".amb-panel").scrollIntoViewIfNeeded();
      await shot("2-report-class-c");
      await page.getByTestId("amb-goal").filter({ hasText: "G7" }).locator("summary").click();
      await shot("2b-report-class-c-open");
      await page.goto("/#/airline/bench");
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await shot("3-bench-bfs-only");
    });
  }
}
