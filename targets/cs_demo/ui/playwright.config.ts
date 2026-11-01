import { defineConfig } from "@playwright/test";

// A production build of the UI; every /api/* call is answered by the spec (e2e/mock.ts), so no Bylaw API and no Muse.
// Not the dev server: its hot reload can re-navigate a page mid-test on a loaded machine.
// E2E_PORT runs the server on its own port, so parallel checkouts do not reuse each other's server.
const port = process.env.E2E_PORT ?? "3399";

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  workers: 2,
  use: { baseURL: `http://localhost:${port}`, channel: "chrome", trace: "retain-on-failure" },
  webServer: {
    command: `npx next build && npx next start -p ${port}`,
    url: `http://localhost:${port}`,
    reuseExistingServer: !process.env.E2E_PORT,
    timeout: 300_000,
    env: { NEXT_TELEMETRY_DISABLED: "1" },
  },
});
