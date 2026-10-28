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

## v1.5 (2026-10-27, from review of PR #8), binding on all items

- **C2 evaluation limits (replaces the v1.3 wording):** `check` bounds each rule evaluation by work, not wall-clock: at most 10^6 comprehension iterations plus elements or characters built, summed over the evaluation. Over the budget gives `Verdict(ok=False, error=...)`. `check` is safe to call from several threads at once. `bytes` constants are rejected by `validate`.
- **C2 operators (v1.5 addendum):** `*` applies to numbers only (sequence or string repetition is refused). Numeric values a rule computes must stay within `abs(x) <= 10**15`; beyond that the verdict is `ok=False` with an error.

## v1.6 (2026-10-27, from UI2 asks), binding on PR1

- **C5 bench rows** also carry `"found": [{"key", "tool_calls", "seconds"}]`: for each hole key, the cumulative write-step count and seconds at which that mode first proved it. Lets the UI draw holes-found vs budget curves.

## v1.7 (2026-10-27, from PX1 finding), binding on EX1, PR1, AM1, AP1, PX1, UI2

**Finding.** τ²'s own gold trajectories reach pre-registered forbidden goals: task 7 upgrades a basic economy reservation to business and then cancels it (G2), task 32 upgrades basic economy to economy and then changes the flights (G1), task 18 downgrades business to economy keeping free bags (G5), task 25 books a friend on the same itinerary (G4). The benchmark grades these as correct agent behaviour, so for those goals the written policy and the graded practice disagree.

**Gold adjudication (classification rule, applied uniformly; goals stay frozen):**
- Every domain gets `gold_goals(domain) -> {goal_id: [task_id, ...]}`: replay each gold task on a fresh env (C8 rules), evaluate every goal on the diff of the whole task; a goal is *gold-sanctioned* if at least one gold task makes it true. Computed once per domain and cached.
- **Class A:** all steps allowed, goal true, goal **not** gold-sanctioned.
- **Class B (new):** all steps allowed, goal true, goal gold-sanctioned. The finding is a contradiction between policy text and benchmark gold; it is reported, amended (the amendment may clarify the text either way) and backtested, never counted as a hole.
- **Class C:** as before (ambiguous by pre-registration, e.g. 24h cancel+rebook).
- C4: each hole/ambiguity carries `"class": "A"|"B"|"C"` and `"gold": {"sanctioned": bool, "tasks": [task_id]}`. Class B entries go in a new top-level list `"contradictions"` (same shape). `holes` holds Class A only.
- **C11 goal monitor:** enforces only the goals of ratified amendments (the human's decision that this outcome is forbidden). `Proxy(domain, ruleset=None, monitor=True, monitor_goals=None)`; `monitor_goals=None` means "goals of the ratified amendments for this domain". With nothing ratified, the monitor blocks nothing, so the gold replay baseline is the RuleSet's.

## v1.8 (2026-10-27, from review of PR #13), binding on PR1 and GA1

- **C6 search feedback protocol:** `search` is a generator; after yielding a chain the caller sends back `(executed: int, hit: bool)` — the number of write steps actually executed for that chain (stops at the first blocked step, so a chain blocked at step 1 costs 0) and whether it proved a finding. The budget is charged with `executed`, for both the Muse phase and BFS. PR1 owns this change; GA1 adopts it and drops its own budget edit.
- **A failed Muse call** for one goal (error or empty reply after retries) is reported in `stats` (`llm_errors`) and that goal falls back to BFS; it never aborts the audit.
- **REQ-PR1-1 scope:** "at least the holes `--no-llm` finds" is checked at the default budget (2000). Below it, the bench reports both modes honestly per budget; no claim of dominance at small budgets.

## v1.9 (2026-10-27, from FX1), binding on FX1, LC1, BR1, CV1 and the views

- C4 `run.mode` is `"bfs" | "muse" | "bfs-fallback"`. `"bfs-fallback"` means Muse was requested, `stats.llm_calls > 0`, and every call failed, so the whole search ran as BFS.
- C4 `run.model` is a string, or `null` when no Muse call succeeded (modes `bfs` and `bfs-fallback`).
- C4 `run.effort` (optional string): the reasoning effort actually sent, after the `BYLAW_EFFORT` override. It is absent for `bfs`.
- `stats.llm_errors` (int) stays as in v1.8. The CLI prints a warning to stderr when the mode is `bfs-fallback`.
- C5 `bench` JSON has a top-level `model` (string or `null`) and `commit`.
- Views: anything that branches on `run.mode === "muse"` shows `bfs-fallback` as an offline run, with a visible "Muse unavailable" note.

## v1.10 (2026-10-27, from LC1), binding on LC1, BR1, CV1, the API and the views

- C4 `run.context_tokens` (int >= 0, required in reports written from v1.10 on): the largest `prompt_tokens` the API billed for one Muse request in this audit; 0 for `bfs`, or when every reply came from the disk cache. Reports written before v1.10 lack it; consumers treat a missing value as unknown, never as 0.
- C4 `stats.tokens` counts only the requests made by this audit's search (per audit, not per process), so concurrent audits in one API process report their own counts. C9 progress events may still report process-wide usage.
- C5 `audit --domain D [--no-llm] [--long-context] [--budget N=2000] [-o report.json]`: `--long-context` adds every tool schema of the domain and the gold task list (`load_gold`) to each proposer request, as one extra user message before the goal message. It has no effect with `--no-llm`.
- C9 `AuditRequest` does not expose `long_context` (REQ-LC1-1 names only the CLI and the report).

## v1.11 (2026-10-28, from FX2), binding on FX2, DM1 and the views

- C4 hole identity: a finding's key is `<goal>:<primary record>`. For G7 (compensation duplicated) the primary record is the user who receives the certificates, so the key is `G7:<user_id>`. Every other goal keeps the chain's target. Goals whose primary record is not the chain's target are listed in `bylaw/report.py` `KEY_ARG`.
- Reports written before v1.11 may hold several G7 entries for one user; they are not re-keyed on load.

## v1.12 (2026-10-28, from review of PR #26), clarifies v1.9

- C4 `run.model` is `null` only in modes `bfs` and `bfs-fallback`. A `muse` run whose search made zero counted calls (every goal answered from the disk cache) keeps mode `muse` and its model string.
