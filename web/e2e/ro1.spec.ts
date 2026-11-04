// RO1: on a read-only deployment (/api/config readonly) the Ratify button is off and says why.
import { expect, test } from "@playwright/test";
import { mockApi } from "./mock";

test.skip(!process.env.E2E_MOCK, "these checks run on the mock's fixtures");

const AMENDMENT = "/#/csdemo/holes/D1%3ALL0EZ6/amendment";

test("read-only: the Ratify button is disabled and labelled", async ({ page }) => {
  await mockApi(page, { fixture: "csdemo.report.json", readonly: true });
  await page.goto(AMENDMENT);
  const button = page.getByRole("button", { name: "Ratify is off on the public demo" });
  await expect(button).toBeVisible();
  await expect(button).toBeDisabled();
});
