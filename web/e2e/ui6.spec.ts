// UI6: Class B copy says policy vs practice, the bench compares classes per mode, Class C notes sit in their group.
import { expect, test } from "@playwright/test";
import { BFS_BENCH, mockApi } from "./mock";

test.skip(!process.env.E2E_MOCK, "these checks run on the mock's fixtures");

const PRACTICE = "the policy and the benchmark's practice disagree";
// The counts of reports/airline.bench.json (budget 200, one run per mode).
const row = { hole_keys: [], tokens: 0, found: [], holes: 0 };
const BENCH = {
  domain: "airline", budget: 200, model: "muse-spark-1.3", commit: "9f13ae2",
  rows: [
    { ...row, mode: "bfs", contradictions: 9, ambiguities: 2, tool_calls: 200, llm_calls: 0, seconds: 68.36 },
    { ...row, mode: "muse", contradictions: 7, ambiguities: 48, tool_calls: 199, llm_calls: 7, seconds: 117.4 },
  ],
};

test("Class B copy never says the policy text forbids the outcome (REQ-UI6-1)", async ({ page }) => {
  await mockApi(page);
  await page.goto("/#/airline/report");
  const lede = page.locator(".head .lede");
  await expect(lede).toContainText(PRACTICE);
  await expect(page.locator(".page")).not.toContainText(/policy text forbids|written policy forbids/);

  const key = (await page.locator('[aria-labelledby="g-G1-B"] .instances a').first().getAttribute("href"))!;
  await page.goto("/" + key);
  await expect(lede).toContainText(PRACTICE);
  await expect(page.locator(".page")).not.toContainText(/policy text forbids|forbidden by the text/);

  await page.goto("/" + key + "/amendment");
  await expect(lede).toContainText(PRACTICE);
  await expect(page.locator(".page")).not.toContainText("policy text forbids");
});

test("the bench compares Class B and C per mode and states budget and one run (REQ-UI6-2)", async ({ page }) => {
  await mockApi(page, { bench: BENCH });
  await page.goto("/#/airline/bench");
  await expect(page.locator(".head .lede")).toContainText("budget of 200 tool calls, same depth limit, one run per mode.");
  const head = page.locator(".btable thead th");
  await expect(head).toContainText(["Mode", "Class A holes", "Class B", "Class C"]);
  const cells = (i: number) => page.locator(".btable tbody tr").nth(i).locator("td");
  await expect(cells(0)).toContainText(["Blind BFS", "0", "9", "2"]);
  await expect(cells(1)).toContainText(["Muse-guided", "0", "7", "48"]);
  await expect(page.locator(".ratio")).toContainText("class B: Blind BFS 9, Muse-guided 7");
});

test("a Muse row without a model is not drawn in the Muse accent (REQ-UI6-3)", async ({ page }) => {
  const r = { ...BFS_BENCH.rows[0], found: BFS_BENCH.rows[0].found.slice(0, 3) };
  await mockApi(page, { bench: { ...BFS_BENCH, rows: [r, { ...r, mode: "muse", llm_calls: 3 }] } });
  await page.goto("/#/airline/bench");
  await expect(page.locator(".btable tbody tr")).toHaveCount(2);
  await expect(page.locator('.page [style*="violet"], .page [stroke*="violet"], .page [fill*="violet"], .page path.area')).toHaveCount(0);
});

test("each Class C note sits in the group of its goal (REQ-UI6-4)", async ({ page }) => {
  await mockApi(page, { fixture: "airline.muse.report.json" });
  await page.goto("/#/airline/report");
  await expect(page.locator(".amb-panel > .amb-note")).toHaveCount(0);
  const group = (g: string) => page.getByTestId("amb-goal").filter({ hasText: g }).getByTestId("amb-note");
  await expect(group("G1")).toContainText("Cancel and rebook");
  await expect(group("G7")).toContainText("silent");
  await expect(group("G7")).not.toContainText("rebook");
  await expect(group("G7")).toBeVisible(); // readable while the group is collapsed
});
