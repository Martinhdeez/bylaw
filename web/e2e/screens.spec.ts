// REQ-UI2-3: a screenshot of each screen at 1440 and 390 width, saved to .artifacts/reports/.
import { expect, test, type Page } from "@playwright/test";
import { mockApi } from "./mock";

const OUT = "../.artifacts/reports/ui2";
const mock = !!process.env.E2E_MOCK;

for (const [w, h] of [[1440, 900], [390, 844]]) {
  test.describe(`${w}px`, () => {
    test.use({ viewport: { width: w, height: h } });
    const shot = async (page: Page, name: string) => {
      expect(await page.evaluate(() => document.documentElement.scrollWidth), `${name} scrolls sideways`).toBeLessThanOrEqual(w);
      await page.screenshot({ path: `${OUT}-${name}-${w}.png`, fullPage: w < 800 });
    };

    test("screens", async ({ page }) => {
      if (mock) await mockApi(page);
      await page.goto("/");
      await expect(page.getByRole("button", { name: "Run audit" })).toBeVisible();
      await shot(page, "1-audit");

      await page.goto("/#/airline/report");
      await expect(page.locator(".instances a").first()).toBeVisible();
      await shot(page, "2-report");

      const key = (await page.locator(".instances a", { has: page.locator(".k", { hasText: /^H5$/ }) }).getAttribute("href"))!;
      await page.goto("/" + key);
      await expect(page.getByTestId("outcome")).toContainText("forbidden", { timeout: 10_000 });
      await shot(page, "3-hole");

      await page.goto("/" + key + "/amendment");
      await expect(page.getByText("Drafted by Muse Spark")).toBeVisible();
      await shot(page, "4-amendment");

      await page.goto("/#/airline/bench");
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await shot(page, "5-bench");

      await page.goto("/#/retail/report");
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await shot(page, "2-report-retail");
    });

    test("audit running", async ({ page }) => {
      test.skip(!mock, "a partial event stream needs the mock");
      await mockApi(page, { partial: true });
      await page.goto("/");
      await page.getByLabel("Use Muse Spark").uncheck();
      await page.getByRole("button", { name: "Run audit" }).click();
      await expect(page.locator(".log")).toContainText("706 chains");
      await shot(page, "1-audit-running");
    });
  });
}
