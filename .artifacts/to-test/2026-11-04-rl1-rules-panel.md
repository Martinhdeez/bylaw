# RL1: rules bylaw enforces, in the demo rail

## Problem

A person watching the demo at bylaw.martinhdeez.com could not see which rules bylaw enforces. The rail showed a rule id and reason only after a call was denied.

## Change

- `targets/cs_demo/ui/components/bylaw-rules.tsx` (new): reads `GET /api/ratified?domain=csdemo` (no API change) and lists the forbidden goals D1–D4, the ratified amendments in force (policy text, guarded tool, the goal it blocks, rule id, "Ratified by a person, <date>"), and the base `tool_rules` behind a native expand. The store has no `ratified_by` field; a name shows only if one is added.
- `bylaw-rail.tsx`: a "Checks / Rules bylaw enforces" switch above the feed. Rules show before a conversation, Checks from its first tool call. On phones (<= 480 px) the idle default is Checks, so the rules start collapsed behind the switch. A denied check whose rule is listed gets a "See rule" button that opens the rules with that entry marked (amendments matched by hole key, since recordings can predate a re-ratified rule id, e.g. D2's `R-seat-own-conf` vs A9's `seat-own-confirm-ci`).
- No API: if `/api/ratified` fails the switch is hidden and the rail is as before. Replays also need the API, so there is no offline mode to cover.
- `app/bylaw.css`: styles in the rail's existing tokens.
- `e2e/mock.ts`: opt-in `rules` serves `/api/ratified` built from `ratified/csdemo.json` and `bylaw/rulesets/csdemo.json`.

Approved by the user on 2026-11-04 (switch above the feed, goals first, collapsed on phones).

## Before / after

| Check | Before | After |
|---|---|---|
| Rules visible before a block | no | yes, `.scratch/after/rl1/1440-idle.png` |
| Block links to its rule | no | `.scratch/after/rl1/1440-d1-see-rule.png` |
| Replay controls at 1440x900 | bottom 372 px | unchanged, 372 px |
| cs_demo UI e2e | 23 passed | 28 passed (5 new in `e2e/rules.spec.ts`) |

Screenshots: `.scratch/after/rl1/` (1440 idle, D1 block, see rule, base rules open; 390 idle and D1 block).

## Tests added

- `targets/cs_demo/ui/e2e/rules.spec.ts`: rules content from the store, keyboard Enter on "See rule" marks A6, a base-rule block opens the base list, phone starts collapsed with no horizontal scroll, fallback without the route.

## Not checked

Browsers other than Chrome; widths 1024 and 768; live mode with a block.
