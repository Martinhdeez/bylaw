// VZ2: the Live view on the CS-C3 fixture event files (fixtures/live/). SHOTS=1 also saves screenshots
// under .scratch/after/vz2-live/ at the repository root.
import { expect, test, type Page } from "@playwright/test";
import { mockApi } from "./mock";

test.skip(!process.env.E2E_MOCK, "these checks run on the mock's fixtures");

// The fixtures' timeline: without bylaw 0-25.9 s, with bylaw 25.9-48.7 s, result 48.7-54.7 s.
const AT = { before: 12, paid: 25, blocked: 43.5, result: 50 };
const WIDTHS = [1440, 1240, 390];
const shot = (page: Page, name: string) =>
  process.env.SHOTS ? page.screenshot({ path: `../.scratch/after/vz2-live/${name}.png`, fullPage: true }) : Promise.resolve();

async function open(page: Page, at: number, width = 1440, q = "") {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.setViewportSize({ width, height: 900 });
  await page.goto(`/?at=${at}${q}#/live`);
  await expect(page.locator('[data-slot="headline"]')).toBeVisible();
  return errors;
}

for (const width of WIDTHS) {
  test(`smoke at ${width}: both runs and the result render from the event files`, async ({ page }) => {
    await mockApi(page);
    const errors = await open(page, AT.paid, width);
    await expect(page.locator('[data-slot="headline"]')).toHaveText("Without bylaw. The agents pay $280 in vouchers.");
    await expect(page.getByTestId("paid")).toHaveText("$280");
    await expect(page.locator(".lv-row.free")).toContainText("Ran, not enforced");
    await shot(page, `before-${width}`);

    await page.getByRole("button", { name: "With bylaw" }).click();
    await expect(page.locator('[data-slot="headline"]')).toHaveText("With bylaw. The same action is stopped before it runs.");
    await expect(page.locator(".lv-row.blk")).toContainText("Blocked before it ran");
    await expect(page.locator(".lv-row.blk")).toContainText("R-comp-disrupted");
    await expect(page.getByTestId("paid")).toHaveText("$0");
    await shot(page, `after-${width}`);

    await page.getByRole("button", { name: "Result" }).click();
    await expect(page.locator('[data-slot="headline"]')).toHaveText("$280 without bylaw. $0 with it.");
    await expect(page.getByTestId("result-before")).toHaveText("$280");
    await expect(page.getByTestId("result-after")).toHaveText("$0");
    await shot(page, `result-${width}`);

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    expect(errors).toEqual([]);
  });
}

test("light theme keeps the receipt and the verdicts readable", async ({ page }) => {
  await mockApi(page);
  await page.addInitScript(() => localStorage.setItem("bylaw.theme", "light"));
  await open(page, AT.blocked);
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await shot(page, "after-1440-light");
});

// After any jump, scrub, toggle or play, each swapped slot shows exactly one element.
test("one visible element per slot after jumps and scrubs", async ({ page }) => {
  await mockApi(page);
  for (const width of WIDTHS) {
    await open(page, 0, width);
    const scrub = page.getByRole("slider", { name: "Timeline" });
    const actions: (() => Promise<unknown>)[] = [
      () => scrub.fill(String(AT.blocked)),
      () => page.getByRole("button", { name: "Without bylaw" }).click(),
      () => scrub.fill(String(AT.result)),
      () => page.getByRole("button", { name: "With bylaw" }).click(),
      () => scrub.fill("3"),
      () => page.getByRole("button", { name: "Result" }).click(),
      () => scrub.fill(String(AT.paid)),
      () => page.getByRole("button", { name: "Show tool calls" }).click(),
      () => scrub.fill(String(AT.before)),
      () => page.getByRole("button", { name: "Play", exact: true }).click(),
      () => page.waitForTimeout(400),
      () => page.getByRole("button", { name: "Pause", exact: true }).click(),
      () => scrub.fill("0"),
    ];
    for (const act of actions) {
      await act();
      const n = (s: string) => page.locator(s).evaluateAll((els) => els.filter((e) => (e as HTMLElement).checkVisibility()).length);
      expect(await n('[data-slot="headline"]')).toBe(1);
      expect(await n('[data-slot="narration"]')).toBe(1);
      expect(await n('[data-slot="status"]')).toBeLessThanOrEqual(1);
      expect(await n('[data-slot="chat"]')).toBeLessThanOrEqual(1);
      expect(await n(".lv-row.now")).toBeLessThanOrEqual(1);
    }
  }
});

test("film mode hides the rail and the player chrome and plays on its own", async ({ page }) => {
  await mockApi(page);
  await open(page, 0, 1440, "&film=1");
  await expect(page.locator(".rail")).toBeHidden();
  await expect(page.locator(".lv-transport")).toBeHidden();
  await expect(page.locator(".lv-chat li").first()).toBeVisible({ timeout: 3000 });
  await shot(page, "film-1440");
});

test("no event files: says how to record them", async ({ page }) => {
  await mockApi(page, { live: [] });
  await page.goto("/#/live");
  await expect(page.getByText("No live runs recorded yet.")).toBeVisible();
  await expect(page.locator("pre")).toContainText("python -m bylaw live --domain csdemo");
});

test("one run only: the other side shows as not recorded, not as a number", async ({ page }) => {
  await mockApi(page, { live: ["csdemo-d1-guard.json"] });
  await open(page, 30);
  await expect(page.getByRole("button", { name: "Without bylaw" })).toHaveCount(0);
  await page.getByRole("button", { name: "Result" }).click();
  await expect(page.locator('[data-slot="headline"]')).toHaveText("$0 with bylaw. The run without it is not recorded.");
  await expect(page.getByLabel("Without bylaw", { exact: true })).toContainText("This run is not recorded.");
});

test("exactly one segment of the run switch is pressed", async ({ page }) => {
  await mockApi(page);
  await open(page, AT.blocked);
  const pressed = () => page.locator('.lv-seg button[aria-pressed="true"]');
  await expect(pressed()).toHaveText(["With bylaw"]);
  await page.getByRole("button", { name: "Result" }).click();
  await expect(pressed()).toHaveText(["Result"]);
  await page.getByRole("button", { name: "Without bylaw" }).click();
  await expect(pressed()).toHaveText(["Without bylaw"]);
});

// The unguarded run with one voucher that states no amount, in its state diffs and its final state.
const unstated = (file: string, run: any) => {
  if (file !== "csdemo-d1.json") return;
  const strip = (v: string[]) => v.map((x, i) => (i === 0 ? "Overnight hotel near JFK Terminal 5 partner hotel" : x));
  for (const e of run.events) if (e.type === "state" && e.diff.context?.session?.after?.vouchers) e.diff.context.session.after.vouchers = strip(e.diff.context.session.after.vouchers);
  run.final_state.vouchers = strip(run.final_state.vouchers);
};

test("a voucher without an amount makes the face value not stated", async ({ page }) => {
  await mockApi(page, { liveEdit: unstated });
  await open(page, AT.paid);
  await expect(page.getByTestId("paid")).toHaveText("not stated");
  await expect(page.locator(".lv-ledger li").first()).toContainText("not stated");
});

test("both runs recorded, one amount not stated: the headline says so, not $0 or a missing run", async ({ page }) => {
  await mockApi(page, { liveEdit: unstated });
  await open(page, AT.result);
  await expect(page.locator('[data-slot="headline"]')).toHaveText("Without bylaw: not stated. With it: $0.");
  await expect(page.getByTestId("result-before")).toHaveText("not stated");
});

test("guarded run only, no final state: the headline names the missing run, not side by side", async ({ page }) => {
  await mockApi(page, { live: ["csdemo-d1-guard.json"], liveEdit: (_f, run) => void (run.final_state = null) });
  await open(page, 30);
  await expect(page.locator('[data-slot="headline"]')).toHaveText("With bylaw: not stated. The run without it is not recorded.");
  await expect(page.getByTestId("result-after")).toHaveText("not recorded");
});

test("agent markdown renders as bold and bullets, never as raw asterisks or HTML", async ({ page }) => {
  const text = "Flight **FLT-123** is on time.\n\n* **Gate:** A10\n- <img src=x onerror=alert(1)>";
  await mockApi(page, { liveEdit: (_f, run) => void run.events.unshift({ t: 0, type: "agent_message", agent: "Triage Agent", text }) });
  await open(page, AT.before);
  const msg = page.locator(".lv-chat .ag").filter({ hasText: "FLT-123" }).first();
  await expect(msg.locator("b").first()).toHaveText("FLT-123");
  await expect(msg.locator("ul li")).toHaveCount(2);
  await expect(msg).not.toContainText("**");
  await expect(msg.locator("img")).toHaveCount(0);
  await expect(msg.locator("ul li").nth(1)).toHaveText("<img src=x onerror=alert(1)>");
});

test("with bylaw, the headline says stopped only once the block has happened", async ({ page }) => {
  await mockApi(page);
  await open(page, 27);
  await expect(page.locator('[data-slot="headline"]')).toHaveText("With bylaw. Every action is checked before it runs.");
  await open(page, AT.blocked);
  await expect(page.locator('[data-slot="headline"]')).toHaveText("With bylaw. The same action is stopped before it runs.");
});
