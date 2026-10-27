# Decision: gold adjudication of holes (2026-10-27)

Made by the orchestrator under the user's delegation ("make you the decisions"); to be confirmed by the user.

- **Evidence:** PX1's gold replay with the goal monitor blocked airline gold tasks 7, 18, 25, 32. Reading `tasks.json`: task 7's user scenario says "ask to upgrade to business first and then cancel" a basic economy reservation; task 32 says "upgrade to economy in order to make the change" then change flights. The gold actions do exactly the M0 chains H2 and H1.
- **Consequence:** H1 (G1) and H2 (G2), and the G5 downgrade holes, are not holes by τ²'s own grading. They are contradictions between the policy text and the benchmark's gold.
- **Decision:** add Class B (gold-sanctioned contradiction); Class A requires that no gold task reaches the goal. Goals stay frozen; the rule is applied uniformly and reported.
- **Product framing:** Bylaw checks every finding against the ground truth the operator already has (gold / historical trajectories). A chain that honest practice also takes is a contradiction to resolve in the text, not an exploit. The retail R6 double refund (payment switch then cancel) has no gold trajectory and stays Class A.
- **Demo numbers:** placeholders such as "−$48,200" are withdrawn; only measured figures from the committed reports are used.

## Addendum (2026-10-27, from UP1 verification at τ² 0c69df4)

- Tasks 7 and 32: the policy text does not literally forbid the chain. Basic economy cannot be cancelled or modified (policy.md L110, L143-147), but L117 allows the cabin upgrade first, after which the rules for business apply. This is an ambiguity in which cabin the rule refers to (at booking or current), not a plain violation. Class B ("policy vs practice") stays, worded as "the policy is ambiguous and practice resolves it permissively".
- Task 18: the policy is silent on bags after a cabin change (L83-86). It is a policy gap, not a contradiction.
- Task 25: **false positive of G4**. L126-128 only forbid changing the passenger count of an existing reservation; task 25 books a separate new reservation, which is allowed. G4 is pre-registered and stays frozen; the demo must not cite G4 or task 25, and the close note records G4 as over-broad.
- Retail R6: the root cause is a τ² tool bug. `cancel_pending_order` (tools.py L191, loop L218) refunds every payment_history entry, including the refund entries. It is reproduced with plain τ² code.
- Upstream issue draft: `.artifacts/backlog/2026-10-27-upstream-tau2-issue-draft.md` (PR #25). Not filed; filing needs the user's approval.
