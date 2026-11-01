// Screenshots for review, not assertions. SHOTS=<dir> npx playwright test shots
import { expect, test } from "@playwright/test";
import { STATUS_ON, mockApi, sse } from "./mock";

const dir = process.env.SHOTS;
test.skip(!dir, "set SHOTS=<dir> to take screenshots");

const sizes: [number, number][] = [[1920, 1080], [1440, 900], [1280, 800], [1024, 768], [768, 1024], [390, 844]];

for (const [w, h] of sizes) {
  test(`replay D1 guard on at ${w}`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h });
    await mockApi(page);
    await page.goto("/?scenario=d1&step=-1");
    await page.waitForTimeout(2500);
    await page.screenshot({ path: `${dir}/${w}-d1-guard-on-end.png`, fullPage: w < 768 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBe(0);
  });
}

for (const [w, h] of [[1440, 900], [390, 844]] as [number, number][]) {
  test(`intro caption at ${w}`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h });
    await mockApi(page);
    await page.goto("/?tour=1");
    await expect(page.getByRole("region", { name: "Intro" })).toContainText("2 of 2", { timeout: 40_000 });
    await page.waitForTimeout(9000);
    await page.screenshot({ path: `${dir}/${w}-intro-act2.png` });
  });
}

test("live conversation at 1440", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, {
    status: STATUS_ON,
    turn: sse([
      { t: 0, type: "guardrail", name: "relevance_guardrail", passed: true, reasoning: "ok" },
      { t: 0.1, type: "guardrail", name: "jailbreak_guardrail", passed: true, reasoning: "ok" },
      { t: 1, type: "agent_message", agent: "Flight Information Agent", text: "Flight **FLT-123** is on time." },
    ]),
  });
  await page.goto("/?tour=0");
  await page.getByLabel("Message the airline assistant").fill("What's the status of FLT-123?");
  await page.keyboard.press("Enter");
  await expect(page.getByText("is on time.")).toBeVisible();
  await page.screenshot({ path: `${dir}/1440-live.png` });
});

test("live off start screen at 1440", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page);
  await page.goto("/?tour=0");
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${dir}/1440-start-live-off.png` });
});

test("reduced motion, D1 guard on at 1440", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page);
  await page.goto("/?scenario=d1&step=27");
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${dir}/1440-reduced-motion.png` });
  const anim = await page.locator(".br-step").first().evaluate((el) => getComputedStyle(el).animationName);
  expect(anim).toBe("none");
});

test("keyboard pass", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page);
  await page.goto("/?scenario=d1&tour=0");
  const seen: string[] = [];
  for (let i = 0; i < 30; i++) {
    await page.keyboard.press("Tab");
    seen.push(
      await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        const ring = getComputedStyle(el).outlineStyle !== "none" || getComputedStyle(el).boxShadow !== "none";
        return `${el.tagName}:${(el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 30)}:${ring ? "ring" : "NO-RING"}`;
      })
    );
    if (i === 14) await page.screenshot({ path: `${dir}/1440-keyboard-focus.png` });
  }
  console.log(seen.join("\n"));
});
