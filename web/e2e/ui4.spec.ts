// UI4: the ratify stamp, ←/→ trace stepping, the ⌘K palette and the theme toggle; screenshots of both themes.
import { expect, test, type Page } from "@playwright/test";
import { mockApi } from "./mock";

const OUT = "../.artifacts/reports/ui4-app";
test.skip(!process.env.E2E_MOCK, "the stamp and stepping checks run on the mock's stored report");

const firstFinding = async (page: Page) => {
  await page.goto("/#/airline/report");
  const href = (await page.locator(".instances a").first().getAttribute("href"))!;
  return "/" + href;
};

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

// Routes registered later win, so this report replaces the stored one from beforeEach.
test("bfs-fallback reads as an offline run with Muse unavailable (01 v1.9)", async ({ page }) => {
  await mockApi(page, { fallback: true });
  await page.goto("/#/airline/report");
  await expect(page.getByTestId("muse-unavailable")).toContainText("Muse unavailable");
  await expect(page.getByText("Offline run: hand RuleSet, blind BFS")).toBeVisible();
  await expect(page.getByText("Rules compiled by Muse Spark")).toHaveCount(0);
  await expect(page.locator(".summary")).not.toContainText("model");
  await expect(page.locator(".meter")).toContainText("Muse unavailable");
  await page.locator(".instances a").first().click();
  await expect(page.getByTestId("outcome")).toBeVisible();
  await expect(page.getByText("Hand RuleSet", { exact: true })).toBeVisible();
});

test("ratify lands the stamp once, and the record keeps it", async ({ page }) => {
  await page.goto((await firstFinding(page)) + "/amendment");
  await expect(page.getByTestId("stamp")).toHaveCount(0);
  await page.getByRole("button", { name: "Ratify" }).click();
  const stamp = page.getByTestId("stamp");
  await expect(stamp).toContainText("Ratified");
  await expect(page.getByTestId("ratified")).toHaveClass(/fresh/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("closed");

  await page.reload();
  await expect(page.getByTestId("stamp")).toContainText("Ratified");
  await expect(page.getByTestId("ratified")).not.toHaveClass(/fresh/);
});

test("arrow keys step the trace", async ({ page }) => {
  await page.goto(await firstFinding(page));
  const steps = page.getByTestId("step");
  const outcome = page.getByTestId("outcome");
  await expect(outcome).toContainText("forbidden");
  const n = await steps.count();

  for (let i = 0; i < n; i++) await page.keyboard.press("ArrowLeft");
  await expect(steps.first()).toHaveAttribute("data-state", "current");
  await expect(outcome).not.toContainText("forbidden");
  await expect(page.getByRole("button", { name: "Previous step" })).toBeDisabled();

  await page.keyboard.press("ArrowRight");
  if (n > 1) await expect(steps.nth(1)).toHaveAttribute("data-state", "current");
  await expect(steps.first()).toHaveAttribute("data-state", "past");
  for (let i = 1; i < n; i++) await page.keyboard.press("ArrowRight");
  await expect(outcome).toContainText("forbidden");
});

test("⌘K jumps to a screen", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("ControlOrMeta+k");
  const dialog = page.getByRole("dialog", { name: "Jump to" });
  await expect(dialog).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Search screens and actions" })).toBeFocused();
  await page.keyboard.type("bench");
  await expect(dialog.getByRole("option")).toHaveCount(1);
  await page.keyboard.press("Enter");
  await expect(dialog).toBeHidden();
  await expect(page).toHaveURL(/#\/airline\/bench$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("blind BFS");

  // Escape closes it, and the sidebar button opens it too.
  await page.getByRole("button", { name: "Jump to a screen or action" }).click();
  await expect(dialog).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
});

test("theme toggle switches and remembers", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  const html = page.locator("html");
  await expect(html).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Switch to light theme" }).click();
  await expect(html).toHaveAttribute("data-theme", "light");
  await page.reload();
  await expect(html).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expect(html).toHaveAttribute("data-theme", "dark");
});

for (const theme of ["dark", "light"] as const) {
  for (const [w, h] of [[1440, 900], [390, 844]]) {
    test(`screens, ${theme}, ${w}px`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: h });
      await page.addInitScript((t) => localStorage.setItem("bylaw.theme", t), theme);
      const shot = async (name: string) => {
        await page.mouse.move(w - 4, h - 4);
        await page.waitForTimeout(1200); // let entry motion settle
        expect(await page.evaluate(() => document.documentElement.scrollWidth), `${name} scrolls sideways`).toBeLessThanOrEqual(w);
        await page.screenshot({ path: `${OUT}-${theme}-${name}-${w}.png` });
      };
      await page.goto("/");
      await expect(page.getByRole("button", { name: "Run audit" })).toBeVisible();
      await shot("1-audit");
      const hole = await firstFinding(page);
      await expect(page.locator(".instances a").first()).toBeVisible();
      await shot("2-report");
      await page.goto(hole);
      await expect(page.getByTestId("outcome")).toContainText("forbidden", { timeout: 10_000 });
      await shot("3-hole");
      await page.goto(hole + "/amendment");
      await page.getByRole("button", { name: "Ratify" }).click();
      await expect(page.getByTestId("stamp")).toBeVisible();
      await shot("4-amendment-ratified");
      await page.goto("/#/airline/bench");
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await shot("5-bench");
      if (w > 800) {
        await page.getByRole("button", { name: "Collapse sidebar" }).click();
        await shot("6-collapsed");
      }
    });
  }
}
