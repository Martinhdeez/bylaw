// RL1: the rules bylaw enforces, in the rail, from GET /api/ratified?domain=csdemo.
import { expect, test, type Page } from "@playwright/test";
import { mockApi, open, ratifiedBody } from "./mock";

const rail = (page: Page) => page.getByRole("complementary", { name: "bylaw guard" });
const rulesTab = (page: Page) => rail(page).getByRole("button", { name: "Rules bylaw enforces" });

test("before a conversation the rail shows the forbidden goals, the amendments in force and the base rules", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, { rules: true });
  await open(page, "/?scenario=d1&tour=0");
  await expect(rulesTab(page)).toHaveAttribute("aria-pressed", "true");
  const body = ratifiedBody();
  const list = rail(page).locator(".brr");
  for (const g of body.ruleset.forbidden_goals) await expect(list).toContainText(g.description);
  await expect(list).toContainText(`Amendments in force · ${body.amendments.length}`);
  for (const a of body.amendments) {
    const card = list.locator(`[data-key="a-${a.id}"]`);
    await expect(card).toContainText(a.policy_text);
    await expect(card).toContainText(a.rule_patch[0].tool);
    await expect(card).toContainText(a.rule_patch[0].id);
    await expect(card).toContainText("Ratified by a person");
  }
  const summary = list.locator(".brr-base summary");
  await expect(summary).toHaveText(/^8 base rules/);
  await summary.click();
  await expect(list.locator(".brr-base li")).toHaveCount(8);
  // the rules sit in the feed's place: the replay controls stay above the fold
  const play = rail(page).getByRole("button", { name: "Play" });
  expect((await play.boundingBox())!.y).toBeLessThan(900);
});

test("a block links to its rule; Enter on See rule opens the rules with that amendment marked", async ({ page }) => {
  await mockApi(page, { rules: true });
  await open(page, "/?scenario=d1&tour=0&step=30");
  await expect(rail(page).getByRole("button", { name: /^Checks/ })).toHaveAttribute("aria-pressed", "true");
  const link = rail(page).locator(".br-step[data-latest=true]").getByRole("button", { name: /See rule/ });
  await link.focus();
  await expect(link).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(rulesTab(page)).toHaveAttribute("aria-pressed", "true");
  const a6 = rail(page).locator('[data-key="a-A6"]');
  await expect(a6).toHaveAttribute("data-focus", "true");
  await expect(a6).toBeInViewport();
});

test("a block by a base rule opens the base rules on that rule", async ({ page }) => {
  await mockApi(page, { rules: true });
  await open(page, "/?scenario=d1&tour=0&step=14"); // the first get_matching_flights block, R-match-disrupted
  await rail(page).locator(".br-step[data-latest=true]").getByRole("button", { name: /See rule/ }).click();
  await expect(rail(page).locator(".brr-base")).toHaveAttribute("open", "");
  await expect(rail(page).locator('[data-key="r-R-match-disrupted"]')).toHaveAttribute("data-focus", "true");
});

test("on a phone the rules start collapsed behind the switch", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page, { rules: true });
  await open(page, "/?scenario=d1&tour=0");
  await expect(rulesTab(page)).toHaveAttribute("aria-pressed", "false");
  await expect(rail(page).locator(".brr")).toHaveCount(0);
  await rulesTab(page).click();
  await expect(rail(page).locator('[data-key="a-A12"]')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBe(0);
});

test("without /api/ratified the rail shows only the checks", async ({ page }) => {
  await mockApi(page);
  await open(page, "/?scenario=d1&tour=0");
  await expect(rail(page).locator(".br-tabs")).toHaveCount(0);
  await expect(rail(page).locator(".br-empty")).toContainText("Press Play");
});
