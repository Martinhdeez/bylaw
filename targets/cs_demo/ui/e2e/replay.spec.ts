import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { LIVE_DIR, mockApi, open } from "./mock";

const rail = (page: import("@playwright/test").Page) => page.getByRole("complementary", { name: "bylaw guard" });
const bylawCard = (page: import("@playwright/test").Page) => page.locator(".bylaw-card");

test("the page makes no third-party request (fonts are self-hosted)", async ({ page }) => {
  const hosts = new Set<string>();
  page.on("request", (r) => hosts.add(new URL(r.url()).hostname));
  await mockApi(page);
  await open(page, "/?scenario=d1&step=-1");
  await page.evaluate(() => document.fonts.ready);
  expect([...hosts]).toEqual(["localhost"]);
});

test("the replay buttons are D1, D4, D2, then the honest request", async ({ page }) => {
  await mockApi(page);
  await open(page, "/?tour=0");
  const titles = await rail(page).locator(".br-scn-title").allTextContents();
  expect(titles).toEqual([
    "Vouchers on an on-time flight",
    "Cancel, then claim compensation",
    "Someone else's seat",
    "A real missed connection",
  ]);
});

test("D1 guard on: Bylaw blocks the vouchers and $280 stays with the airline", async ({ page }) => {
  await mockApi(page);
  await open(page, "/?scenario=d1&step=-1");
  await expect(bylawCard(page)).toHaveAttribute("data-state", "blocked");
  await expect(bylawCard(page)).toContainText("LL0EZ6 is on time");
  const ledger = rail(page).locator(".br-ledger");
  await expect(ledger.locator("div").nth(0)).toContainText("$0");
  await expect(ledger.locator("div").nth(1)).toContainText("$280");
  await expect(rail(page)).toContainText("$280 stayed with the airline");
  await expect(rail(page)).toContainText("D1:LL0EZ6/R-comp-booking-disrupted");
  await expect(page.locator(".bylaw-runner[data-state=blocked]").first()).toBeVisible();
  await expect(rail(page).locator(".br-foot")).toContainText("guard on");
});

test("a blocked payout is priced by what the guard-off recording paid, not a fixed figure", async ({ page }) => {
  await mockApi(page);
  const off = JSON.parse(readFileSync(join(LIVE_DIR, "dm3-d1-vouchers.json"), "utf8"));
  for (const e of off.events)
    if (e.type === "tool_output" && e.tool === "issue_compensation") e.output = "Opened compensation case CMP-1. Issued: $50 meal voucher; $25 ground transport.";
  await page.route("**/api/live/dm3-d1-vouchers.json", (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify(off) }));
  await open(page, "/?scenario=d1&step=-1");
  await expect(rail(page).locator(".br-ledger div").nth(1)).toContainText("$75");
  await expect(rail(page)).toContainText("$75 stayed with the airline: what this agent paid without bylaw in the recorded run");
  await expect(rail(page)).not.toContainText("$280");
});

test("D1 guard off: Bylaw would block, but $280 leaves the airline", async ({ page }) => {
  await mockApi(page);
  await open(page, "/?scenario=d1&guard=off&step=-1");
  await expect(bylawCard(page)).toHaveAttribute("data-state", "would-block");
  await expect(rail(page).locator(".br-ledger div").nth(0)).toContainText("$280");
  await expect(rail(page)).toContainText("The guard is off, so the call ran anyway.");
  await expect(rail(page).locator(".br-stamp", { hasText: "Would block" })).toBeVisible();
});

test("D4 guard on: compensation after the passenger's own cancellation is blocked", async ({ page }) => {
  await mockApi(page);
  await open(page, "/?scenario=d4&step=-1");
  await expect(bylawCard(page)).toHaveAttribute("data-state", "blocked");
  await expect(rail(page)).toContainText("This chat already cancelled IR-D204");
});

test("the honest missed connection is allowed and paid in both modes", async ({ page }) => {
  await mockApi(page);
  await open(page, "/?scenario=legit&step=-1");
  await expect(rail(page).locator(".br-ledger div").nth(0)).toContainText("$280");
  await expect(rail(page).locator(".br-stamp", { hasText: "Blocked" })).toHaveCount(0);
});

test("Play runs a conversation to its end", async ({ page }) => {
  await mockApi(page);
  await open(page, "/?scenario=d2&speed=8&tour=0");
  await rail(page).getByRole("button", { name: "Play" }).click();
  await expect(page.getByText("Thanks. Please put me in seat 14A on confirmation IR-D204.")).toBeVisible();
  await expect(rail(page).locator(".br-end")).toBeVisible({ timeout: 30_000 });
  await expect(rail(page).getByRole("button", { name: "Replay", exact: true })).toBeVisible();
});

test("the guard switch works from the keyboard and changes the recording", async ({ page }) => {
  await mockApi(page);
  await open(page, "/?scenario=d1&tour=0");
  const sw = rail(page).getByRole("switch");
  await expect(sw).toHaveAttribute("aria-checked", "true");
  await sw.focus();
  await page.keyboard.press("Space");
  await expect(sw).toHaveAttribute("aria-checked", "false");
  await expect(rail(page).locator(".br-foot")).toContainText("guard off");
});

test("the intro plays guard off, then guard on, with captions; Esc skips it", async ({ page }) => {
  await mockApi(page);
  await open(page, "/?tour=1");
  const cap = page.getByRole("region", { name: "Intro" });
  await expect(cap).toContainText("1 of 2 · guard off");
  await expect(cap).toContainText("$280 in vouchers just left the airline", { timeout: 30_000 });
  await expect(cap).toContainText("2 of 2 · guard on", { timeout: 20_000 });
  await page.keyboard.press("Escape");
  await expect(cap).toHaveCount(0);
});

test("first visit starts the intro once; later visits do not", async ({ page }) => {
  await mockApi(page);
  await open(page, "/");
  await expect(page.getByRole("region", { name: "Intro" })).toBeVisible();
  await open(page, "/");
  await page.waitForTimeout(1500);
  await expect(page.getByRole("region", { name: "Intro" })).toHaveCount(0);
});
