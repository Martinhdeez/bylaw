# CP1 Policy compiler (Muse → RuleSet JSON)

- **Branch:** `feat/cp1-compiler` · **Pull request:** #1 (round 3, after review)
- **Measured against:** REQ-CP1-1, REQ-CP1-2, REQ-CP1-3. Contracts: C2 (v1.1 conversation facts, v1.3 expression language, v1.4 cancel reason vocabulary, v1.5 evaluation budget), C3 (v1.1 `llm=` injection) and C5 (`compile`).

## Problem

Bylaw claims that "Muse writes the law into checks", but nothing turned a policy into checks. There was no `bylaw.compiler` and no `python -m bylaw`, so REQ-CP1-1..3 had no implementation.

The review of round 1 found the following:

- An interim copy of C2 existed in `bylaw/ruleset_schema.py`.
- `except ImportError` hid broken imports.
- `match_rate` could crash on a hand rule that does not parse.
- The probes were too weak: on EN1's `airline.json`, 11 of 26 hand rules were constant on them, and an all-True compiled set scored 0.27.
- Four mutants survived.

The round-2 review found three more problems:

- `match_rate` crashed on retail (`KeyError: 'reservation_id'`).
- Retail probes never named a real order, so `res` could not be reached.
- The alternative-itinerary candidates for `flights` were not shown to be needed by any test.

## Root cause

- Round 1 was written before EN1 existed, so it carried its own C2 and a domain fallback.
- The round-1 probes (old `bylaw/compiler.py:123`) only copied record fields and rule literals into `args`. Structured arguments (`flights`, `passengers`, `payment_methods`, `payment_id`) were never built. Without them, the rules that read those arguments always raised or were always true.

## Change

1. **C2 comes from EN1.** `bylaw/ruleset_schema.py` is deleted, and the compiler imports `RULESET_SCHEMA`, `validate`, `check`, `RuleError`, `FUNCS` and `hours_between` from `bylaw.rules`. The domain comes from `bylaw.domain.get_domain`, with no fallback. Built on the reviewer's rebase `review/cp1-rebase-r2` (the BT1 CLI structure: `cmd_compile` + `set_defaults`), then rebased onto `bylaw/build` 75ec23f, which carries RT1 (#5), BT1 (#7) and contracts v1.5.
2. **`compile_policy(domain, model=None, llm=None)`** (C3 v1.1).
   - One Muse call carries the policy, the tool schemas and trimmed DB record shapes. It uses structured output, `RULESET_SCHEMA`, `effort="high"` and `max_tokens=64000`; at 32000 the reasoning used up the whole budget and the reply came back empty (see `live-compile-v2.txt` history below).
   - The prompt states:
     - the v1.3 expression language;
     - the conversation facts: `args["reason"]` with the v1.4 vocabulary, `args["reservation_id"]` and `args["complaint"]`;
     - verbatim `policy_ref` quotes, and forbidden goals as end states;
     - rule-writing conventions: one rule per policy condition, a rule that the record exists and is active, implications for conditions that apply to only some calls, flown statuses read from the DB, conditions the API does not check encoded completely.
   - A result that fails `validate` or names an unknown tool goes back to Muse once, with the reason. The result's `domain` is set to the domain name.
3. **Probes** (`bylaw/compiler.py`, `probes` / `_candidates`).
   - The record collection comes from the snapshot (`_record_kind`): the collection, other than users, whose records carry their own id in a `*_id` field and a `user_id`. That is `reservation_id` → reservations on airline and `order_id` → orders on retail. A rule that reads `res` makes the probes name such a record.
   - For a sample of those records (a stride sample plus every booking within 72h of `now`), each tool parameter gets candidate values built from the record:
     - its flights, plus same-route alternatives from other records, a broken itinerary and an empty list;
     - its passengers, one more, one fewer, and six;
     - the user's payment ids and a missing one;
     - its bags and the bags ±n;
     - amounts of 100×n and 50×n;
     - other users, a missing record and other records;
     - retail `item_ids`: the order's items, one item, none, a duplicate, and an item of another product;
     - retail `new_item_ids`: an available other variant of the same product, the same items, an unavailable variant, and a list of the wrong length;
     - `payment_method_id`: the order's original payment method, the user's other methods, and one outside the profile.
   - Conversation facts (args keys the rules read that the schema lacks) get "absent", the rules' literals, True and False.
   - Each record gives its own call, every one-key variant, and 12 seeded random multi-key combinations.
4. **`match_report` / `match_rate`.**
   - The verdicts are C2 `check` verdicts: a rule that raises denies.
   - A hand rule is *matched* when one compiled rule on the same tool has its truth table. It is matched *by parts* when the compiled rules it implies, ANDed, have that truth table: the checker ANDs a tool's rules, so a condition split across several compiled rules is the same check.
   - A hand rule that does not validate is *invalid* and unmatched. It never crashes the report.
   - `rate = (matched + by_parts) / hand rules`. `strict_rate` counts single-rule matches only.
   - The report counts *discriminable* hand rules (verdict varies over the probes) and how many of them matched.
5. **`python -m bylaw compile`** prints the rule counts and the full match line, then lists each unmatched hand rule.
6. **`tests/test_compiler.py`:** 32 offline tests and 1 live test. Round 2 had 28 offline tests; round 3 adds 4.

## Before / after

| Check | Before | After |
|---|---|---|
| Unit tests red before the module existed (round 1) | `.scratch/after/cp1-compiler/red-1-validate.txt`, `red-2-match-rate.txt`, `red-3-cli.txt` | `.scratch/after/cp1-compiler/gate.txt` |
| Hand rules discriminable on the probes (airline.json, 28 rules) | 15/26 (reviewer's measurement, round 1) | 28/28, `.scratch/after/cp1-compiler/match-rates.txt` |
| Hand rules discriminable on the probes (retail.json, 24 rules) | crash, `KeyError: 'reservation_id'` (review, round 2) | 24/24, identity 1.0, `.scratch/after/cp1-compiler/retail-identity.txt` |
| All-True compiled set vs airline.json | 0.27 (reviewer, round 1) | 0.000, `match-rates.txt` |
| Identity hand vs hand | 1.0 | 1.000, `match-rates.txt` |
| Live match rate, round-1 prompt (`airline.compiled.json`) | n/a | 0.250, `match-rates.txt` |
| Live match rate, prompt v2 (`airline.compiled.v2.json`) | n/a | 0.643, strict 0.536, `match-rates.txt` |
| Live match rate, prompt v3 (`airline.compiled.v3.json`) | n/a | 0.750 (21/28: 17 single, 4 by parts), strict 0.607, `match-rates.txt` |
| Live match rate, prompt v4 = shipped prompt (v3 + v1.4 reason vocabulary, `airline.compiled.v4.json`) | n/a | **0.643** (18/28: 17 single, 1 by parts), strict 0.607, `live-compile-v4.txt` |
| Mutants killed (21: the review's 4 from round 1, its `flights` mutant from round 2, and the record-key and retail-candidate mutants) | 4 survived (round 1), 1 survived (round 2) | 21/21, `mutations.txt` |
| Compiler acceptance tests (`origin/test/01-wave1`), offline | 6 passed, 1 failed (retail crash, round 2) | 7 passed, `acceptance-offline.txt` |
| Live tests (unit + acceptance REQ-CP1-1, REQ-CP1-3) | n/a | 3 passed, `live-pytest.txt` |

## Tests added

All in `tests/test_compiler.py`.

- **`match_rate` (REQ-CP1-2):**
  - identity is 1.0;
  - an equivalent rewrite matches;
  - 48h vs 24h is told apart on DB probes and in a 1000-record DB;
  - `<` vs `<=` on `amount`;
  - structured args (passenger count);
  - several args changed at once;
  - conversation facts (`reason`);
  - a different tool does not match;
  - an empty or all-True compiled set scores 0;
  - a constant hand rule is matched only by the same constant and is reported as not discriminable;
  - a hand rule that does not parse counts as unmatched without crashing;
  - a compiled rule that raises denies;
  - `user` is resolved through `res`;
  - a split rule matches by parts, but weak parts and rules the hand rule does not imply do not;
  - other bookings' itineraries are probed for `flights` (kills the round-2 mutant);
  - a retail-shaped snapshot is probed through `order_id`;
  - retail `item_ids`, `new_item_ids` and `payment_method_id` vary, including a payment method outside the profile.
- **`compile_policy` (C3 v1.1):**
  - returns Muse's valid RuleSet, with `effort="high"`, `RULESET_SCHEMA`, and the facts in the prompt;
  - sets the domain name;
  - sends one repair round;
  - raises after two invalid replies (dunder, `**kwargs`, `open`, unknown tool, empty `policy_ref`).
- **CLI (REQ-CP1-3):** prints the match line and the unmatched rules, or the rule count when no hand set exists.
- **Real airline data:**
  - every hand rule in `bylaw/rulesets/airline.json` is discriminable and matches itself;
  - an all-True set scores 0.
- **Real retail data:** every hand rule in `bylaw/rulesets/retail.json` is discriminable (24/24) and matches itself.
- **Live:** `test_live_compile_airline_policy`.

`mutations.txt` shows that each of these tests fails when the behaviour it names is removed.

## Out of scope and not measured

- **The M1 target (≥0.90) is not met.** The shipped prompt scored 0.643 (strict 0.607). The previous prompt scored 0.750; the only change between them is the v1.4 reason list, so a single compile moves by about ±0.1. That is one sample per prompt, not a distribution. The 10 unmatched hand rules are listed in `live-compile-v4.txt`. Most of them are interpretation choices where both readings are defensible:
  - EN1 ANDs the airline-cancelled ground with the stated reason;
  - EN1 adds a `changed_or_cancelled` fact that no contract names;
  - payment source vs payment in profile is split differently.

  Others are slips, for example route chaining on booking. I stopped tuning the prompt after four live compiles, to avoid fitting it to one hand set.
- **The probes have a ceiling.**
  - They vary one record's arguments, sampled from 60 stride records plus recent ones, and `now` is fixed.
  - Truth-table equality on probes is evidence of equivalence, not proof.
  - "By parts" only considers compiled rules on the same tool.
- **Retail:** retail is measured offline only, hand rules against themselves (24/24 discriminable, rate 1.0). No retail policy was compiled with Muse, so there is no live retail match rate.
- **Live tests:** the live pytest run was served from the on-disk LLM cache, with the same request as the CLI compile of prompt v4. The four compiles (round 1, v2, v3, v4) were real Muse calls. One v2 attempt returned empty at `max_tokens=32000`.
- **Not scored:** precision. Extra compiled rules and forbidden goals are not scored.
