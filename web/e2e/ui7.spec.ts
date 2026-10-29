// UI7: the Class C reason follows report.classify (pre-registered class first, then a same-user cancel and rebook),
// R5 reads as the once-only ambiguity, and the Report shows the reason per entry. Open findings of the UI6 review.
import { expect, test } from "@playwright/test";
import { mockApi } from "./mock";

test.skip(!process.env.E2E_MOCK, "these checks run on the mock's fixtures");

const clone = (x: unknown) => JSON.parse(JSON.stringify(x));
const g1 = (r: any) => r.ambiguities.filter((a: any) => a.goal === "G1");
const bookStep = (h: any) => h.chain.find((s: any) => s.tool === "book_reservation");

test("R5 reads as the once-only ambiguity, not as a silent policy", async ({ page }) => {
  await mockApi(page, {
    fixture: "airline.muse.report.json",
    edit: (r) => r.ambiguities.push({ ...clone(r.ambiguities.find((a: any) => a.goal === "G7")), id: "C900", goal: "R5", key: "R5:#W1", title: "order_modified_more_than_once on #W1" }),
  });
  await page.goto("/#/airline/report");
  const note = page.getByTestId("amb-goal").filter({ hasText: "R5" }).getByTestId("amb-note");
  await expect(note).toContainText("once-only line");
  await expect(note).not.toContainText("silent");
});

test("a goal pre-registered as Class C gives its own reason even when the chain cancels and rebooks", async ({ page }) => {
  await mockApi(page, {
    fixture: "airline.muse.report.json",
    edit: (r) => r.ambiguities.push({ ...clone(g1(r)[0]), id: "C901", goal: "G7", key: "G7:PRE1" }),
  });
  await page.goto("/#/airline/holes/G7%3APRE1");
  const lede = page.locator(".head .lede");
  await expect(lede).toContainText("pre-registered as an ambiguity");
  await expect(lede).not.toContainText("rebook");
});

test("a rebook for another user is not the permitted cancel and rebook", async ({ page }) => {
  let key = "";
  await mockApi(page, {
    fixture: "airline.muse.report.json",
    edit: (r) => {
      key = g1(r)[0].key;
      bookStep(g1(r)[0]).args.user_id = "someone_else_1";
    },
  });
  await page.goto(`/#/airline/holes/${encodeURIComponent(key)}`);
  const lede = page.locator(".head .lede");
  await expect(lede).toContainText("listed as an ambiguity for review");
  await expect(lede).not.toContainText("rebook");
});

test("the Report gives the reason per entry when entries of one goal differ", async ({ page }) => {
  await mockApi(page, {
    fixture: "airline.muse.report.json",
    edit: (r) => void (bookStep(g1(r)[1]).args.user_id = "someone_else_1"),
  });
  await page.goto("/#/airline/report");
  const group = page.getByTestId("amb-goal").filter({ hasText: "G1" });
  await expect(group.getByTestId("amb-note")).toHaveText("The reason differs by entry, see each one.");
  await group.locator("summary").click();
  const notes = group.getByTestId("amb-entry-note");
  await expect(notes).toHaveCount(2);
  await expect(notes.nth(0)).toContainText("Cancel and rebook for the same user");
  await expect(notes.nth(1)).toHaveText("It was listed as an ambiguity for review.");
});
