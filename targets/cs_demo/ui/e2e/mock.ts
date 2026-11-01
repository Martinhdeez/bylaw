// Answers /api/* in the browser: replays from the committed reports/live files, live chat per test.
import type { Page, Route } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const LIVE_DIR = join(__dirname, "..", "..", "..", "..", "reports", "live");

export const STATUS_ON = { enabled: true, model: "muse-spark-1.3", tokens_used: 1200, token_cap: 300000, sessions: 1 };

export interface LiveMock {
  status?: object | number; // body, or an HTTP status for a refusal
  session?: number | { status: number; detail: string };
  turn?: string | { status: number; detail: string }; // SSE body, or a refusal
}

export function sse(events: object[], done = { current_agent: "Triage Agent", context: {} }) {
  return events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("") + `event: done\ndata: ${JSON.stringify(done)}\n\n`;
}

/** Navigate and wait until the app has hydrated and loaded its first recording (the rail footer appears then). */
export async function open(page: Page, url: string) {
  await page.goto(url);
  await page.locator(".br-foot").waitFor({ timeout: 30_000 });
}

const json = (route: Route, status: number, body: unknown) =>
  route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

export async function mockApi(page: Page, live: LiveMock = {}) {
  const calls = { session: [] as any[], turn: [] as any[] };
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();
    if (path === "/api/live/status") {
      const s = live.status ?? 404;
      return typeof s === "number" ? json(route, s, { detail: "Not Found" }) : json(route, 200, s);
    }
    if (path === "/api/csdemo/agents") return json(route, 404, { detail: "Not Found" });
    if (path === "/api/live/session" && method === "POST") {
      calls.session.push(route.request().postDataJSON());
      const s = live.session ?? 201;
      if (typeof s !== "number") return json(route, s.status, { detail: s.detail });
      const guard = route.request().postDataJSON().guard;
      return json(route, 201, { session: "s1", guard, model: "muse-spark-1.3", current_agent: "Triage Agent", context: {} });
    }
    if (/^\/api\/live\/session\/[^/]+\/turn$/.test(path)) {
      calls.turn.push(route.request().postDataJSON());
      const t = live.turn ?? sse([]);
      if (typeof t !== "string") return json(route, t.status, { detail: t.detail });
      return route.fulfill({ status: 200, contentType: "text/event-stream", body: t });
    }
    const m = path.match(/^\/api\/live\/([\w.-]+\.json)$/);
    if (m) {
      try {
        return route.fulfill({ status: 200, contentType: "application/json", body: readFileSync(join(LIVE_DIR, m[1]), "utf8") });
      } catch {
        return json(route, 404, { detail: "no live file" });
      }
    }
    return json(route, 404, { detail: "Not Found" });
  });
  return calls;
}
