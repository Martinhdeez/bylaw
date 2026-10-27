// REQ-UI2-2: open /, run an offline audit on airline, open the first Class A hole, step the trace replay,
// open its amendment, ratify, see the ratified state.
import { expect, test } from "@playwright/test";
import { mockApi } from "./mock";

test("offline audit to ratified amendment", async ({ page }) => {
  if (process.env.E2E_MOCK) await mockApi(page);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Audit a policy" })).toBeVisible();
  await page.getByRole("radio", { name: /Airline/ }).click();
  await page.getByLabel("Use Muse Spark").uncheck();
  await page.getByRole("button", { name: "Run audit" }).click();
  await expect(page.getByRole("link", { name: "Open report" })).toBeVisible({ timeout: 540_000 });
  await page.getByRole("link", { name: "Open report" }).click();

  await expect(page.getByRole("heading", { level: 1 })).toContainText("proven");
  const first = page.locator(".instances a").first();
  const id = (await first.locator(".k").textContent())!;
  expect(id).toBe("H1");
  await first.click();

  const steps = page.getByTestId("step");
  await expect(steps.first()).toBeVisible();
  const n = await steps.count();
  expect(n).toBeGreaterThan(0);
  // Let the autoplay reach the outcome, rewind to the first call, then step through by hand.
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

  await page.getByRole("link", { name: "Review amendment" }).click();
  await expect(page.getByText("Drafted by Muse Spark")).toBeVisible();
  await page.getByRole("button", { name: "Ratify" }).click();
  await expect(page.getByTestId("ratified")).toContainText("Enforced by MCP proxy");

  await page.getByRole("link", { name: "Back to report" }).click();
  await expect(page.locator(".instances a").first()).toContainText("Fixed");
  expect(errors).toEqual([]);
});
