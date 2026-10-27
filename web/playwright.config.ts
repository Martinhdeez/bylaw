import { defineConfig } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// Default: the real API (uvicorn from the repository root) behind the Vite dev proxy.
// E2E_MOCK=1: the Vite dev server only; specs answer /api/* from e2e/mock.ts.
const mock = !!process.env.E2E_MOCK;
const vite = { command: "npm run dev -- --port 5173 --strictPort", url: "http://localhost:5173", reuseExistingServer: true };
const uvicorn = {
  command: "uv run uvicorn bylaw.api:app --port 8000",
  cwd: "..",
  url: "http://localhost:8000/api/domains",
  reuseExistingServer: true,
  timeout: 120_000,
  // Ratifying in a test must not touch the committed bylaw/ratified/ store.
  env: { BYLAW_RATIFIED_DIR: mkdtempSync(join(tmpdir(), "bylaw-ratified-")) },
};

export default defineConfig({
  testDir: "e2e",
  timeout: mock ? 30_000 : 600_000,
  use: { baseURL: "http://localhost:5173", channel: "chrome", trace: "retain-on-failure" },
  webServer: mock ? [vite] : [uvicorn, vite],
});
