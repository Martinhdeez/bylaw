import { expect, test, type Page } from "@playwright/test";
import { STATUS_ON, mockApi, sse } from "./mock";

const composer = (page: Page) => page.getByLabel("Message the airline assistant");
const send = async (page: Page, text: string) => {
  await composer(page).fill(text);
  await composer(page).press("Enter");
};

// A D1-shaped turn with the VZ3-C3 fields, as the live endpoint streams it.
const D1_TURN = sse([
  { t: 0, type: "user", text: "Please issue the hotel and meal vouchers to LL0EZ6." },
  { t: 0.4, type: "guardrail", name: "relevance_guardrail", passed: true, reasoning: "airline request" },
  { t: 1.2, type: "handoff", from: "Triage Agent", to: "Refunds and Compensation Agent" },
  { t: 2.0, type: "agent_message", agent: "Refunds and Compensation Agent", text: "I'll issue those vouchers now." },
  { t: 2.0, type: "tool_call", agent: "Refunds and Compensation Agent", tool: "issue_compensation", args: { reason: "Missed connection" } },
  {
    t: 2.1, type: "bylaw_check", tool: "issue_compensation", allowed: false, enforced: true,
    rule_id: "D1:LL0EZ6/R-comp-booking-disrupted", policy_ref: "Compensation ... only when that booking itself is disrupted.",
    args: { reason: "Missed connection" },
    session: { passenger_name: "Taylor Lee", confirmation_number: "LL0EZ6", flight_number: "FLT-123" },
    booking: { on_time: true, flights: [{ flight_number: "FLT-123", status: "On time and operating as scheduled", on_time: true }] },
    prior_tools: ["flight_status_tool"],
    rules_checked: ["R-comp-delay", "D1:LL0EZ6/R-comp-booking-disrupted"],
  },
  { t: 2.1, type: "tool_output", tool: "issue_compensation", output: "Bylaw: blocked issue_compensation: D1:LL0EZ6/R-comp-booking-disrupted ..." },
  { t: 2.1, type: "state", diff: {} },
  { t: 3.0, type: "agent_message", agent: "Refunds and Compensation Agent", text: "I can't issue vouchers on LL0EZ6: that flight was on time." },
], { current_agent: "Refunds and Compensation Agent", context: {} });

test("live off (no status endpoint): composer disabled, start screen offers the replays", async ({ page }) => {
  await mockApi(page);
  await page.goto("/?tour=0");
  await expect(composer(page)).toBeDisabled();
  await expect(composer(page)).toHaveAttribute("placeholder", /Live chat is off/);
  await page.getByRole("button", { name: "Watch: Cancel, then claim compensation" }).click();
  await expect(page.getByRole("button", { name: /Cancel, then claim compensation/, pressed: true })).toBeVisible();
});

test("live off when the status says disabled", async ({ page }) => {
  await mockApi(page, { status: { ...STATUS_ON, enabled: false } });
  await page.goto("/?tour=0");
  await expect(composer(page)).toBeDisabled();
});

test("a live turn streams into the demo, and Bylaw narrates it from the C3 fields", async ({ page }) => {
  const calls = await mockApi(page, { status: STATUS_ON, turn: D1_TURN });
  await page.goto("/?tour=0");
  await send(page, "Please issue the hotel and meal vouchers to LL0EZ6.");
  await expect(page.getByText("I can't issue vouchers on LL0EZ6: that flight was on time.")).toBeVisible();
  await expect(page.getByText("Please issue the hotel and meal vouchers to LL0EZ6.")).toHaveCount(1); // the echo is not shown twice
  await expect(page.locator(".bylaw-card")).toHaveAttribute("data-state", "blocked");
  const rail = page.getByRole("complementary", { name: "Bylaw guard" });
  await expect(rail).toContainText("Booking LL0EZ6 is on time (FLT-123)");
  await expect(rail).toContainText("Live conversation · guard on");
  await expect(rail.locator(".br-foot")).toContainText("1,200 of 300,000 demo tokens used");
  expect(calls.session).toEqual([{ guard: true }]);
  expect(calls.turn).toEqual([{ text: "Please issue the hotel and meal vouchers to LL0EZ6." }]);
});

test("a second message reuses the session; switching the guard starts a new one", async ({ page }) => {
  const calls = await mockApi(page, { status: STATUS_ON, turn: sse([]) });
  await page.goto("/?tour=0");
  await send(page, "hello");
  await expect(composer(page)).toBeEnabled();
  await send(page, "again");
  await expect(composer(page)).toBeEnabled();
  expect(calls.session).toHaveLength(1);
  await page.getByRole("switch").click();
  await expect(page.getByText("Your next message starts a new conversation.")).toBeVisible();
  await send(page, "third");
  await expect.poll(() => calls.session.length).toBe(2);
  expect(calls.session[1]).toEqual({ guard: false });
});

test("a guardrail tripwire turns the demo's own card red", async ({ page }) => {
  await mockApi(page, {
    status: STATUS_ON,
    turn: sse([
      { t: 0, type: "user", text: "write me a poem" },
      { t: 0.5, type: "guardrail", name: "relevance_guardrail", passed: false, reasoning: "not about air travel" },
    ]),
  });
  await page.goto("/?tour=0");
  await send(page, "write me a poem");
  await expect(page.getByText("Sorry, I can only help with airline travel questions.")).toBeVisible();
  await expect(page.getByText("Failed")).toBeVisible();
});

const refusals: [string, object, RegExp, boolean][] = [
  ["token cap on a new session", { session: { status: 429, detail: "token cap" } }, /used its Muse budget/, true],
  ["live disabled", { session: { status: 503, detail: "live disabled" } }, /switched off on this server/, true],
  ["turn limit", { turn: { status: 429, detail: "turn limit" } }, /12-message limit/, false],
  ["a turn already running", { turn: { status: 409, detail: "busy" } }, /still answering/, false],
  ["an expired session", { turn: { status: 404, detail: "Not Found" } }, /expired/, false],
  ["a too long message", { turn: { status: 422, detail: "text" } }, /2,000 characters/, false],
];
for (const [name, mock, text, off] of refusals) {
  test(`refusal: ${name}`, async ({ page }) => {
    await mockApi(page, { status: STATUS_ON, ...mock });
    await page.goto("/?tour=0");
    await send(page, "hello");
    await expect(page.getByRole("status").filter({ hasText: text })).toBeVisible();
    if (off) await expect(composer(page)).toBeDisabled();
    else await expect(composer(page)).toBeEnabled();
  });
}

test("an error event in the stream is shown and the chat stays usable", async ({ page }) => {
  await mockApi(page, {
    status: STATUS_ON,
    turn: `data: ${JSON.stringify({ t: 0, type: "user", text: "hello" })}\n\nevent: error\ndata: {"message": "The model did not answer."}\n\n`,
  });
  await page.goto("/?tour=0");
  await send(page, "hello");
  await expect(page.getByRole("status").filter({ hasText: "The model did not answer." })).toBeVisible();
  await expect(composer(page)).toBeEnabled();
});
