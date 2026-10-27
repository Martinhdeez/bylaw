import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API (contract C9) runs with `uv run uvicorn bylaw.api:app` on :8000; in production FastAPI serves web/dist itself.
const proxy = { "/api": process.env.BYLAW_API ?? "http://localhost:8000" };
export default defineConfig({ plugins: [react()], server: { proxy }, preview: { proxy } });
