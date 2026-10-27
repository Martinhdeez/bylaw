// UI3: the sidebar collapses and expands from its toggle, by mouse and keyboard, and remembers the choice.
import { expect, test } from "@playwright/test";
import { mockApi } from "./mock";

const OUT = "../.artifacts/reports/ui3";
test.use({ viewport: { width: 1440, height: 900 } });

test("sidebar collapses and expands", async ({ page }) => {
  if (process.env.E2E_MOCK) await mockApi(page);
  await page.goto("/");
  const rail = page.locator(".rail");
  const audit = page.getByRole("link", { name: "Audit" });
  await expect(audit).toBeVisible();
  const wide = (await rail.boundingBox())!.width;
  await page.screenshot({ path: `${OUT}-1-expanded.png` });

  await page.getByRole("button", { name: "Collapse sidebar" }).click();
  const expand = page.getByRole("button", { name: "Expand sidebar" });
  await expect(expand).toHaveCSS("opacity", "0");
  await expect.poll(async () => (await rail.boundingBox())!.width).toBeLessThan(wide / 2);
  await expect(audit).toBeVisible(); // icon-only, still named
  await page.mouse.move(800, 450);
  await page.screenshot({ path: `${OUT}-2-collapsed.png` });

  await page.locator(".lockup svg").hover({ force: true });
  await expect(expand).toHaveCSS("opacity", "1");
  await page.screenshot({ path: `${OUT}-3-collapsed-hover.png` });

  // The choice survives a reload.
  await page.reload();
  await expect(expand).toBeAttached();

  // Keyboard: Tab reaches the toggle, focus shows it, Enter expands.
  await page.mouse.move(800, 450);
  await page.keyboard.press("Tab"); // skip link
  await page.keyboard.press("Tab"); // home link
  await page.keyboard.press("Tab");
  await expect(expand).toBeFocused();
  await expect(expand).toHaveCSS("opacity", "1");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Collapse sidebar" })).toBeFocused();
  await expect.poll(async () => (await rail.boundingBox())!.width).toBe(wide);
});
