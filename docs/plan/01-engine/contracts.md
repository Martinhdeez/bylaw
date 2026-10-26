# 01 — Contracts (frozen v1)

## C1 Domain — `bylaw/domain.py`

```python
@dataclass
class StepResult: tool: str; args: dict; ok: bool; output: Any; error: str | None

@dataclass
class Goal:
    id: str            # "G1".."G7" airline, "R1".. retail
    name: str
    policy_ref: str    # quoted policy line(s)
    cls: str           # "A" counted | "C" ambiguity
    check: Callable[[dict, dict, list[StepResult]], bool]   # (db_before, db_after, chain) -> forbidden outcome reached

class Domain(Protocol):
    name: str                    # "airline" | "retail"
    policy_text: str
    tools: list[dict]            # OpenAI function schemas for the domain tools
    write_tools: set[str]
    goals: dict[str, Goal]
    now: str                     # ISO time of the simulator clock
    def fresh_env(self) -> Any
    def call(self, env, tool: str, **args) -> StepResult
    def snapshot(self, env) -> dict          # JSON-serialisable DB dump
    def targets(self, goal_id: str) -> list[dict]   # argument seeds, e.g. {"user_id": .., "reservation_id": ..}

def get_domain(name: str) -> Domain
```

## C2 RuleSet JSON — `bylaw/rulesets/<domain>.json`, schema in `bylaw/rules.py` as `RULESET_SCHEMA`

```json
{"domain": "airline",
 "tool_rules": [{"id": "R-cancel-1", "tool": "cancel_reservation", "allow_if": "<expr>", "policy_ref": "<quoted line>", "note": ""}],
 "forbidden_goals": [{"id": "G1", "name": "basic_economy_flights_changed", "policy_ref": "<quoted line>", "description": ""}]}
```

- A call is allowed iff every rule whose `tool` matches evaluates truthy. Tools with no rules are allowed.
- **Expression language:** Python expression syntax, evaluated by a whitelist AST walker.
  - Names: `args` (dict), `db` (snapshot dict), `now` (ISO str), `res` (the reservation/order named by `args`, or None), `user` (the user named by `args` or by `res`, or None).
  - Literals, boolean ops, comparisons, `in`, subscripts, `.get(...)` on dicts, list/dict displays, comprehensions.
  - Functions: `len any all sum min max abs hours_between(iso_a, iso_b)`.
  - Anything else raises `RuleError`.
- API:
  - `validate(ruleset) -> None` raises `RuleError`.
  - `check(ruleset, snapshot, tool, args, now) -> list[Verdict]`, where `Verdict(rule_id, ok, policy_ref, error=None)`.
  - `allowed(verdicts) -> bool`.

## C3 Compiler — `bylaw/compiler.py`

- `compile_policy(domain: Domain, model: str | None = None) -> dict` returns a RuleSet (C2). It uses `bylaw.llm.structured` with `RULESET_SCHEMA` and `effort="high"`, and validates the result.
- `match_rate(compiled: dict, hand: dict) -> float` is the share of hand rules (tool + equivalent condition) matched by compiled rules. Equivalence is checked by evaluating both expressions on a fixed probe set of (snapshot, args) built from the domain DB. Same truth table → match.
- CLI: `python -m bylaw compile --domain D -o PATH`.

## C4 Report JSON — schema `REPORT_SCHEMA` in `bylaw/report.py`

```json
{"run": {"commit": "", "domain": "", "model": "", "mode": "bfs|muse", "started": "", "budget": 0, "goals_commit": ""},
 "holes": [{"id": "H1", "class": "A", "goal": "G1", "title": "", "money_delta": 0.0,
            "chain": [{"tool": "", "args": {}, "ok": true, "verdicts": [{"rule_id": "", "ok": true, "policy_ref": ""}]}],
            "diff": {}, "goal_true": true, "replays": "5/5"}],
 "ambiguities": [ "<same shape as holes, class C>" ],
 "stats": {"chains_tried": 0, "tool_calls": 0, "llm_calls": 0, "tokens": 0, "seconds": 0.0}}
```

## C5 CLI — `python -m bylaw`

- `audit --domain D [--no-llm] [--budget N=2000] [-o report.json]`
- `compile --domain D -o PATH`
- `bench --domain D --budget N [-o bench.json]`

## C6 Search — `bylaw/proposer.py`

- `search(domain, ruleset, budget: int, use_llm: bool) -> Iterator[list[tuple[str, dict]]]` yields candidate chains of (tool, args).
- Depth ≤ 4, WRITE tools only (reads are free and not counted). Arguments are instantiated from `domain.targets(goal)`.
- With `use_llm`, Muse proposes abstract chains per goal first (`effort="high"`), then BFS fills the remaining budget.

## v1.1 (2026-10-26, from TA1 findings), binding on all items

- **C1 snapshot shape:** `Domain.snapshot(env)` returns the τ² DB dump as a dict whose top-level collections are keyed by id. Airline: `{"users": {id: {...}}, "reservations": {id: {...}}, "flights": {...}}`. Retail: `{"users": {...}, "orders": {...}, "products": {...}}`.
- **C2 conversation facts in `args`:** facts the policy needs but the τ² tool signature lacks are passed as extra keys in the call's `args`, and rules read them from `args`. Examples: the cancellation reason as `args["reason"]` ("change of plan" | "airline cancelled flight" | "other"), and the certificate's reservation as `args["reservation_id"]` on `send_certificate`. `Domain.call` strips the keys the τ² tool does not accept before calling it.
- **C3 offline injection:** the signature is `compile_policy(domain, model=None, llm=None)`. `llm`, if given, is a callable with the signature of `bylaw.llm.structured(messages, schema, name, effort=None, **opts) -> dict`, used instead of the real client. Tests use it to script the model.

## v1.2 (2026-10-26, from TA2 findings), binding on EX1 and PR1

- **C4 `diff` format:** `{collection: {record_id: {"before": dict|null, "after": dict|null}}}`. Only changed records appear; `null` means the record was created or deleted.
- **C4 hole identity:** `key = goal + ":" + target_id`, where target_id is the primary record the goal fired on (e.g. `G1:T1QOBS`). Every hole and ambiguity carries `"key"`.
- **EX1 replay:** `bylaw.executor.replay(domain, chain: list[dict]) -> {"steps": [StepResult-as-dict], "diff": C4 diff}`, where `chain` is the C4 chain shape (`tool`, `args`). Replaying a report hole's chain gives a diff equal to the report's `diff`.
- **C5 bench:** `bench --domain D --budget N [--modes bfs,muse] [-o PATH]`. `--modes bfs` runs offline. The bench JSON is `{"domain", "budget", "rows": [{"mode", "holes", "hole_keys": [...], "tool_calls", "llm_calls", "tokens", "seconds"}]}`.
- **C6 budget:** the budget counts executed write steps across all chains, summed over the run. Reads are free.

## v1.3 (2026-10-26, from EN1 and review of PR #4), binding on all items

- **C2 expression language (from EN1, approved by the orchestrator):** `zip` joins the function whitelist; the M0 route rule (flight segments chain end to end) needs pairwise access to the segment list. Arithmetic `+ - * / // %` (no `**`), unary `- +`, `x if c else y` and slices are accepted as part of "Python expression syntax"; keyword arguments to whitelisted functions are accepted, `*args`/`**kwargs` are not. `hours_between(a, b)` is the absolute distance in hours, so argument order does not matter. A rule that raises while being evaluated (for example `res` is None) gives `Verdict(ok=False, error=...)`; `check` never raises for a bad expression, `validate` does. `send_certificate` also reads `args["complaint"]` ("cancelled" | "delayed") as a conversation fact.
- **C2 evaluation limits:** `check` evaluates a rule under a bound (no value above 10^6 elements or characters, a time limit of 50 ms per rule); a rule over the bound gives `Verdict(ok=False, error=...)`. Muse-compiled rulesets are untrusted input.

## v1.4 (2026-10-27, from BT1 findings), binding on all items

- **C2 cancel reason vocabulary:** `args["reason"]` on `cancel_reservation` is one of `"change of plan"`, `"airline cancelled flight"`, `"health"`, `"weather"`, `"other"`. Insurance covers `"health"` and `"weather"` only (policy: "health or weather reasons"). Supersedes the list in v1.1.
- **Honest-customer baseline:** the hand RuleSet must block 0 of the 43 airline gold tasks (unknown tasks excluded). A hand rule that blocks a gold action is a rule bug unless the gold action contradicts the policy text, which is then written down with the quote.
