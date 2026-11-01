# Notice

`targets/cs_demo/ui/` is vendored from the OpenAI Customer Service Agents Demo.

- Origin: https://github.com/openai/openai-cs-agents-demo, directory `ui/`
- Commit: `bd7bfca0f5abf50529370814c3e7c88542011925` (2025-12-11)
- Vendored: 2026-11-01 (VZ3 prototype). The first commit on `view/vz3-real-ui` is the unmodified copy, so `git diff` from it shows every change.
- Licence: MIT, "Copyright 2025 OpenAI", in `LICENSE` (verbatim)

## Changes

- ChatKit removed (it loads from OpenAI's CDN, calls chatgpt.com and needs a domain allowlist): `components/chatkit-panel.tsx` and `lib/api.ts` deleted, the ChatKit script tag dropped from `app/layout.tsx`, `@openai/chatkit*`, `openai`, `wavtools`, `react-syntax-highlighter` and `concurrently` dropped from `package.json`. `components/chat-panel.tsx` is a plain chat box in the same frame, with the same greeting and prompts.
- `app/page.tsx` drives the panels from recorded Bylaw event files (`reports/live/*.json`, served by `bylaw/api.py` at `/api/live`) instead of a ChatKit thread. `next.config.mjs` proxies `/api/*` to the Bylaw API (`BYLAW_API_URL`, default `http://127.0.0.1:8000`).
- Added, all Bylaw's: `components/bylaw-rail.tsx`, `bylaw-card.tsx`, `bylaw-mark.tsx`, `lib/replay.ts`, `lib/agents.ts`, `app/bylaw.css`; the Fira Sans and Fira Code fonts for Bylaw's elements.
- Small edits to upstream components: `guardrails.tsx` renders the Bylaw card as a third guardrail; `runner-output.tsx` shows the Bylaw check between a tool call and its output; `conversation-context.tsx` flashes keys a tool call changed; `agent-panel.tsx` places Guardrails above Conversation Context; `agents-list.tsx` and `guardrails.tsx` use two columns on phones; `lib/types.ts` gains the `bylaw_check` event.
- The page title says "guarded by Bylaw". OpenAI's logo stays as the demo's own favicon, as upstream.
