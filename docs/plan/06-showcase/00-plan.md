# 06 — Showcase: scan and fix, visible (M6)

Goal: make Bylaw's two processes, **scan** and **fix**, visible step by step on a real, recognisable agent app, so the demo sells the argument: frontier models are powerful, and the way to improve them is to make them more deterministic and give the application more control over them. The model proposes; the application decides.

Target app: OpenAI's MIT-licensed `openai-cs-agents-demo` (airline customer service, Agents SDK + Next.js), kept locally in `.scratch/cs-demo` until the spike decides how to vendor it.

## Items

| Id | Item | Kind | Weight | Agent | Depends on |
|---|---|---|---|---|---|
| CS1 | Spike: clone, analyse the demo, Muse via Agents SDK, ChatKit check, go/no-go | evidence | light | assistant | — |
| UI6 | Copy and bench fixes from the DM1 review | view fix | full | designer, then reviewer | — |
| RM2 | `replay --monitor`: per-step goal monitor state | fix | light | builder | — |
| VZ1 | Prototype of the live Scan and Fix views | view | full | designer (prototype, then user approval) | — |
| CS2 | Bylaw target adapter for the demo: rules, goals, executor, guard on every tool call | feature | full | test-author + builder | CS1 go |
| VZ2 | Implement Scan and Fix views on the demo target | view | full | designer, then reviewer | VZ1 approved, CS2 contract |

CS2 and VZ2 are planned after CS1 reports; their requirements and contracts are written then.

## Visual direction (user, 2026-10-28)

"Make the process graphic, not just a load bar or something like that, we need something so visual." Scan and Fix are scenes, not progress indicators: tools as a graph, chains as paths travelling it, state as a live object, the hole as a crack; the fix as a rule slotting into the cut edge and the attack stopped at the proxy gate. Model moves read fluid and violet; application moves read rigid and stamped.

## Requirements

| Id | Requirement | Surface |
|---|---|---|
| REQ-UI6-1 | Class B findings never say the policy text forbids the outcome; the copy states that a gold task reaches the same goal (contradiction between policy and practice). | Report, Hole, Amendment screens |
| REQ-UI6-2 | The Bench screen compares Class B counts per mode as well as Class A. | Bench screen |
| REQ-UI6-3 | A bench row whose run has no model is not drawn in the Muse accent. | Bench screen |
| REQ-UI6-4 | Each Class C note sits in the group of the goal it describes. | Report screen |
| REQ-RM2-1 | `replay --hole ID --monitor` prints, after each step line, the goal monitor state for that step (goal id, reached yes/no, and its measured value such as money_delta); without `--monitor` output is unchanged. | CLI |

## Out of scope

Deploy (user go-ahead). Filing the upstream issue (user approval). Retail Muse search.
