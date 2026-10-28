"""Amendments (contract C7): Muse drafts a policy sentence plus a C2 rule patch per hole; Bylaw proves it closes."""
import copy
import json
import re

from bylaw import llm as llm_mod
from bylaw import rules
from bylaw.executor import run
from bylaw.report import audit

ANSWER_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["policy_text", "rule_patch", "rationale"],
    "properties": {"policy_text": {"type": "string"}, "rule_patch": rules.RULESET_SCHEMA["properties"]["tool_rules"],
                   "rationale": {"type": "string"}},
}

AIRLINE_NAMES = """- args: the call's arguments (dict); res: the reservation named by args['reservation_id'] (or None); \
user: the user named by args['user_id'] or by res (or None); db: the whole database snapshot \
({"users": {id: ...}, "reservations": {id: ...}, "flights": {number: {"dates": {date: ...}}}}); now: ISO time string."""

SYSTEM = """You amend the RuleSet that guards an AI customer-service agent. A RuleSet holds tool_rules; a tool call is \
allowed iff every rule for that tool evaluates truthy on the database as it is just before the call.

A Bylaw audit found a hole: a chain of tool calls, each allowed by the current rules, that reaches an outcome the \
policy forbids. Draft the amendment that closes it:
- policy_text: one or two sentences, in the voice of the policy, stating the rule the policy is missing.
- rule_patch: new tool_rules (fields id, tool, allow_if, policy_ref, note) that block at least one step of the chain. \
Ids must be new. policy_ref quotes the policy line (or your policy_text) the rule enforces.
- rationale: why this closes the hole and why honest requests the policy allows still pass.
Keep the patch narrow: every request the policy permits must stay allowed (the patch is backtested on real \
customer tasks and each one it blocks counts against it).

allow_if is a Python expression over these names only:
- args: the call's arguments (dict); res: the reservation named by args['reservation_id'] (or None); \
user: the user named by args['user_id'] or by res (or None); db: the whole database snapshot \
({"users": {id: ...}, "reservations": {id: ...}, "flights": {number: {"dates": {date: ...}}}}); now: ISO time string.
- literals, and/or/not, comparisons, in, arithmetic (+ - * / // %, no **; * on numbers only), x if c else y, subscripts, slices, \
list/set/dict displays and comprehensions, dict .get(...).
- functions: len any all sum min max abs zip hours_between(iso_a, iso_b) (absolute hours).
Nothing else: no other names, methods, attributes, imports or lambdas. A rule that raises denies the call."""


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def apply(ruleset: dict, amendment: dict) -> dict:
    out = copy.deepcopy(ruleset)
    ids = {r["id"] for r in out["tool_rules"]}
    for r in amendment["rule_patch"]:
        if r["id"] in ids:
            raise ValueError(f"rule id {r['id']!r} already exists in the ruleset")
        ids.add(r["id"])
        out["tool_rules"].append(copy.deepcopy(r))
    return out


def _problem(domain, ruleset: dict, ans) -> str | None:
    """Why the model's answer is not a usable amendment, or None."""
    try:
        if not (isinstance(ans.get("rationale"), str) and ans["rationale"].strip()):
            return "rationale must be a non-empty string"
        if not isinstance(ans.get("policy_text"), str) or not 1 <= len(sentences(ans["policy_text"])) <= 2:
            return "policy_text must be one or two sentences"
        patch = ans.get("rule_patch")
        if not isinstance(patch, list) or not patch:
            return "rule_patch must be a non-empty list of tool_rules"
        tools = {t["function"]["name"] for t in domain.tools}
        unknown = sorted({str(r.get("tool")) for r in patch if not isinstance(r, dict) or r.get("tool") not in tools})
        if unknown:
            return f"unknown tool(s) {unknown}; tools are {sorted(tools)}"
        rules.validate(apply(ruleset, ans))
    except (ValueError, AttributeError, TypeError, KeyError) as e:
        return f"{type(e).__name__}: {e}"
    return None


def _hole_text(domain, hole: dict) -> str:
    goal = domain.goals[hole["goal"]]
    return json.dumps({"hole_id": hole["id"], "goal": {"id": goal.id, "name": goal.name, "policy_ref": goal.policy_ref},
                       "chain": [{"tool": s["tool"], "args": s["args"]} for s in hole["chain"]],
                       "diff": hole.get("diff", {}),
                       # Class B (01 v1.7): benchmark gold tasks also reach this goal; blocking them is the trade-off
                       **{k: hole[k] for k in ("class", "gold") if k in hole}}, indent=1, default=str)


def draft(domain, ruleset: dict, hole: dict, model=None, llm=None) -> dict:
    ask = llm or llm_mod.structured  # module attribute, read at call time: tests replace it (C7 v1.1)
    # a domain whose snapshot is not the tau2 airline DB describes its own rule names (csdemo)
    system = SYSTEM.replace(AIRLINE_NAMES, domain.rule_names) if hasattr(domain, "rule_names") else SYSTEM
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": f"POLICY:\n{domain.policy_text}\n\nCURRENT RULESET:\n"
                                            f"{json.dumps(ruleset, indent=1)}\n\nHOLE:\n{_hole_text(domain, hole)}"}]
    # high effort spends its reasoning inside max_tokens: the 4000 default came back empty (finish_reason=length)
    opts = {"max_tokens": 32000, **({"model": model} if model else {})}
    for attempt in range(2):
        ans = ask(messages, ANSWER_SCHEMA, "amendment", effort="high", **opts)
        problem = _problem(domain, ruleset, ans) if isinstance(ans, dict) else "the answer must be a JSON object"
        if problem is None:
            return {"id": "A" + hole["id"].removeprefix("H"), "hole_id": hole["id"], "policy_text": ans["policy_text"],
                    "rule_patch": ans["rule_patch"], "rationale": ans["rationale"]}
        messages = [*messages, {"role": "assistant", "content": json.dumps(ans, default=str)},
                    {"role": "user", "content": f"That amendment was rejected: {problem}. Reply with a corrected one."}]
    raise ValueError(f"no valid amendment for {hole['id']} after 2 answers: {problem}")


def blocked(domain, ruleset: dict, chain: list[dict]) -> bool:
    """The rules forbid some step of the chain when it is re-run on a fresh env."""
    return any(not all(v["ok"] for v in s["verdicts"]) for s in run(domain, chain, ruleset)["steps"])


def closes(domain, ruleset: dict, hole: dict, budget: int) -> bool:
    """REQ-AM1-3: the hole's own chain is blocked and a re-audit of its goal finds nothing left: no Class A hole and
    no Class B contradiction (01 v1.7)."""
    if not blocked(domain, ruleset, hole["chain"]):
        return False
    one_goal = copy.copy(domain)
    one_goal.goals = {hole["goal"]: domain.goals[hole["goal"]]}
    found = audit(one_goal, ruleset, budget)
    return not found["holes"] + found.get("contradictions", [])
