// REQ-UI2-2: open /, run an offline audit on airline, open the first finding, step the trace replay,
// open its amendment, ratify, see the ratified state.
// C9 v1.2: an offline audit drafts no amendments, so after it the test places a stored report that carries
// them in its own BYLAW_REPORTS_DIR, newer than the audit's, and ratifies on that one. Under 01 v1.7 the airline
// findings are Class B (gold tasks take them), so "first Class A hole" reads as the first finding: Class A when the
// report has one, else Class B.
import { expect, test } from "@playwright/test";
import { join } from "node:path";
import { utimesSync, writeFileSync } from "node:fs";
import { mockApi, storedReport } from "./mock";

test("offline audit to ratified amendment", async ({ page }) => {
  const mock = process.env.E2E_MOCK ? await mockApi(page, { stored: false }) : null;
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));

  // 1. Offline audit.
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Audit a policy" })).toBeVisible();
  await page.getByRole("radio", { name: /τ² Airline/ }).click();
  await page.getByLabel("Use Muse Spark").uncheck();
  await page.getByRole("button", { name: "Run audit" }).click();
  await expect(page.getByRole("link", { name: "Open report" })).toBeVisible({ timeout: 540_000 });
  await page.getByRole("link", { name: "Open report" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("holes in the airline policy");
  expect(await page.locator(".instances a").count()).toBeGreaterThan(0);
  await expect(page.locator(".instances a").first()).not.toContainText("Amendment ready");

  // 2. A stored report with amendments becomes the latest.
  if (mock) mock.place();
  else {
    const file = join(process.env.BYLAW_REPORTS_DIR!, "airline.json");
    writeFileSync(file, JSON.stringify(storedReport()));
    const later = new Date(Date.now() + 60_000);
    utimesSync(file, later, later);
  }
  await page.reload();
  const first = page.locator(".instances a").first();
  await expect(first).toContainText("Amendment ready");
  await expect(first.locator(".k")).toHaveText(/^[HB]1$/);
  await first.click();

  // 3. Step the trace: let the autoplay reach the outcome, rewind to the first call, step through by hand.
  const steps = page.getByTestId("step");
  await expect(steps.first()).toBeVisible();
  const n = await steps.count();
  await expect(page.getByTestId("outcome")).toContainText("forbidden");
  const prev = page.getByRole("button", { name: "Previous step" });
  while (await prev.isEnabled()) await prev.click();
  await expect(steps.first()).toHaveAttribute("data-state", "current");
  await expect(page.getByTestId("outcome")).not.toContainText("forbidden");
  for (let i = 1; i < n; i++) {
    await page.getByRole("button", { name: "Next step" }).click();
    await expect(steps.nth(i)).toHaveAttribute("data-state", "current");
    await expect(steps.nth(i)).toContainText("allowed");
  }
  await page.getByRole("button", { name: "Next step" }).click();
  await expect(page.getByTestId("outcome")).toContainText("forbidden");

  // 4. Amendment, ratify, ratified state.
  await page.getByRole("link", { name: "Review amendment" }).click();
  await expect(page.getByText("Drafted by Muse Spark")).toBeVisible();
  await page.getByRole("button", { name: "Ratify" }).click();
  await expect(page.getByTestId("ratified")).toContainText("Enforced by MCP proxy");
  await expect(page.getByTestId("ratified")).not.toContainText("/R-"); // 03 v1.3 namespaced ids shown bare

  await page.getByRole("link", { name: "Back to report" }).click();
  await expect(page.locator(".instances a").first()).toContainText(/Fixed|Ratified/);
  expect(errors).toEqual([]);
});
