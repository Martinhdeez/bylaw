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
