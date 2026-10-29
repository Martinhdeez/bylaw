// RA2: csdemo (the OpenAI customer service demo, RA1) is a web domain: its routes, the Audit picker and Bench.
// fixtures/csdemo.report.json is reports/csdemo.json from DM2.
import { expect, test } from "@playwright/test";
import { mockApi } from "./mock";

test.skip(!process.env.E2E_MOCK, "these checks run on the mock's fixtures");

test("Ratify on a csdemo hole posts to the csdemo domain", async ({ page }) => {
  await mockApi(page, { fixture: "csdemo.report.json" });
  await page.goto("/#/csdemo/holes/D1%3ALL0EZ6/amendment");
  await expect(page.locator("h1")).toContainText("A6");
  const post = page.waitForRequest((r) => r.method() === "POST" && r.url().includes("/ratify"));
  await page.getByRole("button", { name: /ratify/i }).click();
  const url = new URL((await post).url());
  expect(decodeURIComponent(url.pathname)).toBe("/api/holes/D1:LL0EZ6/ratify");
  expect(url.searchParams.get("domain")).toBe("csdemo");
});

test("the Audit picker offers the customer service demo", async ({ page }) => {
  await mockApi(page);
  await page.goto("/#/");
  const demo = page.getByRole("radio", { name: /Airline customer service \(OpenAI demo\)/ });
  await expect(demo).toBeVisible();
  await demo.click();
  await expect(demo).toHaveAttribute("aria-checked", "true");
});

test("Bench on csdemo says there is no bench for this domain", async ({ page }) => {
  await mockApi(page, { fixture: "csdemo.report.json" });
  await page.goto("/#/csdemo/bench");
  await expect(page.locator("h1")).toHaveText("No bench for this domain");
  await expect(page.locator(".page")).not.toContainText("bylaw bench --domain csdemo");
});
