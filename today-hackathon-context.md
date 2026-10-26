# Today's Hackathon: context handoff

Written 2026-10-24 for a new project session. Read this first.

## Situation

Martín is participating in a **separate, local hackathon today (Oct 24)** — not the Meta Global AI Developer Hackathon (build period starts Mon Oct 26). The goal is to build something today that:
- Is a **standalone project** (not the Meta firewall project, which cannot be started yet)
- Is **related** to the Meta project themes so the work has cross-over value
- Can be completed **in a single day**

## The Meta project (background only)

The Meta hackathon project is a **policy firewall for AI agents**: plain-language company rules compiled into deterministic code, enforced by an MCP proxy on every agent tool call. Prior work:
- **trace-it** (Hack Spain 2026, 1st place): turns plain-language operating policy into compiled, tested Python — process definitions and business rules.
- **Banana Bank** (t·Dots 2026, 1st place): AI bank assistant where the server enforces every financial rule deterministically.

## What was decided for today

The direction settled on is: **natural language → code**, applied to a specific, concrete domain.

### Options discussed (NL → code, specific use cases)

Three candidates are on the table. Martín has not yet chosen one:

| # | Idea | Input | Output | Pain solved |
|---|---|---|---|---|
| 1 | **NL → GitHub Actions** | "Run tests on PR, deploy to staging on merge to main" | Working `.github/workflows/ci.yml` | Developers hate writing CI YAML |
| 2 | **NL → SQL queries over your schema** | Paste your Postgres schema + describe what you want | Valid, runnable SQL query | Analysts speak English, not SQL |
| 3 | **NL → form validation rules** | "Email must be valid, password 8+ chars with a number" | Zod schema + React error messages | Designers write requirements, devs translate them |

**Recommended by Claude:** Option 2 (NL → SQL). Clearest before/after, output is immediately runnable, "analysts shouldn't need SQL" is universally felt.

**Explicitly ruled out:**
- Prompt injection benchmark (interesting but drifted away from)
- Generic policy/rule compiler (already done in trace-it — too similar)
- Hardware, simulators, robotics

## Martín's profile

- Final-year Computer Engineering student at UDC, 5x hackathon winner
- Strong in: Python/FastAPI, React/TypeScript, agents, MCP, end-to-end systems
- Works with Claude Code + Orca orchestration
- Prefers novel ideas that stand out; not another chatbot/copilot
- **English correction:** Martín is learning English and has asked Claude to correct every message he sends

## Next step

Martín needs to pick one of the 3 options above. Once chosen, define:
1. The exact use case / demo scenario
2. The stack (frontend + backend)
3. What the LLM does vs. what stays deterministic
4. An Excalidraw of the app flow
5. Build plan for the day
