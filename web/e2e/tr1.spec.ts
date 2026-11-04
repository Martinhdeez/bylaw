// TR1-V: the Usage screen shows the Muse Spark price, the deploy's live counters against the cap, and the recorded ledger.
// SHOTS_DIR=<dir> also saves a screenshot of each state at 1440 and 390 width.
import { expect, test, type Page } from "@playwright/test";
import { mockApi } from "./mock";

test.skip(!process.env.E2E_MOCK, "these checks run on the mock's fixtures");

const dir = process.env.SHOTS_DIR;
const shot = async (page: Page, name: string) => {
  if (!dir) return;
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth), `${name} scrolls sideways at ${width}`).toBeLessThanOrEqual(width);
    await page.screenshot({ path: `${dir}/${name}-${width}.png`, fullPage: true });
  }
};

test("the nav opens Usage with the price, the cap meter and the ledger", async ({ page }) => {
  await mockApi(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Usage" }).click();
  await expect(page).toHaveURL(/#\/usage$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Muse Spark usage and cost");

  const price = page.getByRole("region", { name: "Muse Spark price" });
  await expect(price).toContainText("$1.25");
  await expect(price).toContainText("$4.25");
  await expect(price.getByRole("link", { name: /Pricing page/ })).toHaveAttribute("href", "https://dev.meta.ai/docs/pricing-rate-limits");

  const meter = page.getByRole("meter", { name: "Tokens used of the cap" });
  await expect(meter).toHaveAttribute("aria-valuemax", "300000");
  await expect(page.getByText("Refreshing every 5 s")).toBeVisible();
  // The mock adds one Muse turn per request, so a refresh after 5 s raises the counter.
  const first = Number(await meter.getAttribute("aria-valuenow"));
  await expect.poll(async () => Number(await meter.getAttribute("aria-valuenow")), { timeout: 12_000 }).toBeGreaterThan(first);

  const rows = page.locator(".ledger tbody tr");
  await expect(rows).toHaveCount(5);
  await expect(rows.filter({ hasText: "csdemo audit, Muse-guided search" })).toContainText("$0.0395–$0.1344");
  await expect(rows.filter({ hasText: "customer service policy compiled" })).toContainText("$0.0250");
  await expect(rows.first()).toContainText("reports/csdemo.json");
  const total = page.locator(".ledger tfoot tr");
  await expect(total).toContainText("629,630");
  await expect(total).toContainText("$0.8330–$2.4913");
  await expect(page.locator(".foot-note")).toContainText("record only the total tokens");
  await shot(page, "usage");
});

test("no ledger and live runs off: an empty state and no meter", async ({ page }) => {
  await mockApi(page, {
    usage: (u) => {
      u.recorded = { entries: [], total: { calls: 0, tokens: 0, cost_usd: { low: 0, high: 0 } } };
      u.live = { ...u.live, enabled: false, sessions: 0, input_tokens: 0, output_tokens: 0, tokens_used: 0, cost_usd: 0 };
    },
  });
  await page.goto("/#/usage");
  await expect(page.getByText("Live runs off")).toBeVisible();
  await expect(page.getByRole("meter")).toHaveCount(0);
  await expect(page.getByText("No recorded runs.")).toBeVisible();
  await expect(page.locator(".ledger")).toHaveCount(0);
  await expect(page.locator(".foot-note")).toHaveCount(0);
  await shot(page, "usage-empty-off");
});

test("ledger with only split entries: exact costs and no range footnote", async ({ page }) => {
  await mockApi(page, { usage: (u) => { u.recorded.entries = u.recorded.entries.filter((e: any) => e.input_tokens !== null); } });
  await page.goto("/#/usage");
  await expect(page.locator(".ledger tbody tr")).toHaveCount(2);
  await expect(page.locator(".foot-note")).toHaveCount(0);
});
