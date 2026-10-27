import { defineConfig } from "@playwright/test";
import { mkdirSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// Default: the real API (uvicorn from the repository root) behind the Vite dev proxy.
// E2E_MOCK=1: the Vite dev server only; specs answer /api/* from e2e/mock.ts.
const mock = !!process.env.E2E_MOCK;

// The API's stores (C9 v1.1) live in one tmp dir per run, so tests never touch reports/ or ratified/.
// Set in process.env so the workers, which load this file again, reuse the same dir.
const root = (process.env.BYLAW_E2E_DIR ??= mkdtempSync(join(tmpdir(), "bylaw-e2e-")));
const stores = { BYLAW_REPORTS_DIR: join(root, "reports"), BYLAW_CACHE_DIR: join(root, "cache"), BYLAW_RATIFIED_DIR: join(root, "ratified") };
Object.values(stores).forEach((d) => mkdirSync(d, { recursive: true }));
Object.assign(process.env, stores);

const vite = { command: "npm run dev -- --port 5173 --strictPort", url: "http://localhost:5173", reuseExistingServer: true };
const uvicorn = {
  command: "uv run uvicorn bylaw.api:app --port 8000",
  // BYLAW_API_ROOT runs the API from another checkout, e.g. an unmerged AP1 branch.
  cwd: process.env.BYLAW_API_ROOT ?? "..",
  url: "http://localhost:8000/api/domains",
  reuseExistingServer: false,
  timeout: 120_000,
  env: stores,
};

export default defineConfig({
  testDir: "e2e",
  timeout: mock ? 30_000 : 600_000,
  use: { baseURL: "http://localhost:5173", channel: "chrome", trace: "retain-on-failure" },
  webServer: mock ? [vite] : [uvicorn, vite],
});
