# UI7 part 1: Class C reasons and Class B coverage

Branch `view/ui7`. This fixes the four UI6 findings listed under "Open findings (for UI7)" in `docs/plan/06-showcase/00-plan.md`. Part 2, the restyle of the other screens, is a prototype on `view/ui7-restyle`. It waits for the user's approval and is not in this change.

## What changed

1. `classCWhy` in `web/src/ui.tsx` no longer calls R5 "the policy is silent". Each goal pre-registered as Class C now has its own reason:
   - G7: the policy is silent on a second certificate.
   - R5: the once-only line may cover only item changes.
   - R8: the refund target sits under returns.
2. `classCWhy` follows `report.classify` in the same order:
   - First, the goal's pre-registered class.
   - Then a cancel followed by a rebook for the same user. The user comes from the cancelled reservation in the hole's diff.
   - Anything else reads "it was listed as an ambiguity for review".
   - The report does not carry a goal's registered class, so the list is copied from `CLASS_C_GOALS` and the `cls="C"` retail goals. A `ponytail:` comment marks the copy.
3. `Report.tsx` gives the Class C reason on each entry. The group summary shows the shared reason, or "The reason differs by entry, see each one."
4. `ui6.spec.ts` now checks the Class B copy on the first finding of every Class B group: tasks 32, 7 and 18 in the mock, not task 32 alone.

## How to test

- Run `cd web && E2E_MOCK=1 npx playwright test e2e/ui6.spec.ts e2e/ui7.spec.ts`.
- The four tests in `ui7.spec.ts` fail on the old `ui.tsx` and `Report.tsx`. I checked this by restoring both files from HEAD: 4 failed.
