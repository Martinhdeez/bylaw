"""RuleSet checker (contract C2): per-tool `allow_if` expressions over the DB snapshot before a call.

Expressions are Python expression syntax, accepted only if every AST node is on a whitelist, then
evaluated with no builtins. Names: args db now res user, plus comprehension variables.
Functions: len any all sum min max abs hours_between zip (zip: C2 v1.1 note). Methods: `.get` only.
"""
import ast
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

_STR = {"type": "string"}
RULESET_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["domain", "tool_rules", "forbidden_goals"],
    "properties": {
        "domain": _STR,
        "tool_rules": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["id", "tool", "allow_if", "policy_ref", "note"],
            "properties": {k: _STR for k in ("id", "tool", "allow_if", "policy_ref", "note")},
        }},
        "forbidden_goals": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["id", "name", "policy_ref", "description"],
            "properties": {k: _STR for k in ("id", "name", "policy_ref", "description")},
        }},
    },
}


class RuleError(ValueError):
    pass


@dataclass
class Verdict:
    rule_id: str
    ok: bool
    policy_ref: str
    error: str | None = None


def hours_between(a: str, b: str) -> float:
    """Absolute distance between two ISO timestamps, in hours."""
    return abs((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds()) / 3600


FUNCS = {f.__name__: f for f in (len, any, all, sum, min, max, abs, zip, hours_between)}
NAMES = {"args", "db", "now", "res", "user"}

_NODES = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,  # no Pow: 9**9**9 hangs
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.IfExp, ast.Constant, ast.Name, ast.Load, ast.Store, ast.Subscript, ast.Slice,
    ast.List, ast.Tuple, ast.Set, ast.Dict,
    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.comprehension,
    ast.Call, ast.Attribute, ast.keyword,
)


@lru_cache(maxsize=4096)
def _compile(expr: str):
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise RuleError(f"syntax error in {expr!r}: {e.msg}") from None
    nodes = list(ast.walk(tree))
    bound = {n.id for c in nodes if isinstance(c, ast.comprehension) for n in ast.walk(c.target) if isinstance(n, ast.Name)}
    for n in nodes:
        if not isinstance(n, _NODES):
            raise RuleError(f"{type(n).__name__} not allowed in {expr!r}")
        if isinstance(n, ast.Name) and (n.id.startswith("_") or n.id not in NAMES | FUNCS.keys() | bound):
            raise RuleError(f"name {n.id!r} not allowed in {expr!r}")
        if isinstance(n, ast.Attribute) and n.attr != "get":
            raise RuleError(f"attribute .{n.attr} not allowed in {expr!r}")
        if isinstance(n, ast.keyword) and n.arg is None:
            raise RuleError(f"**kwargs not allowed in {expr!r}")
        if isinstance(n, ast.Call):
            f = n.func
            if not ((isinstance(f, ast.Name) and f.id in FUNCS) or isinstance(f, ast.Attribute)):
                raise RuleError(f"call not allowed in {expr!r}")
        if isinstance(n, ast.Attribute) and not any(isinstance(c, ast.Call) and c.func is n for c in nodes):
            raise RuleError(f".get must be called in {expr!r}")
    return compile(tree, "<rule>", "eval")


def validate(ruleset: dict) -> None:
    if not isinstance(ruleset, dict) or not isinstance(ruleset.get("domain"), str):
        raise RuleError("ruleset must be an object with a string 'domain'")
    for key, fields in (("tool_rules", ("id", "tool", "allow_if", "policy_ref")), ("forbidden_goals", ("id", "name", "policy_ref"))):
        items = ruleset.get(key)
        if not isinstance(items, list):
            raise RuleError(f"'{key}' must be a list")
        for item in items:
            if not isinstance(item, dict) or not all(isinstance(item.get(f), str) and item[f] for f in fields):
                raise RuleError(f"{key} entry needs non-empty strings {fields}: {item!r}")
    ids = [r["id"] for r in ruleset["tool_rules"]]
    if len(ids) != len(set(ids)):
        raise RuleError("rule ids must be unique")
    for r in ruleset["tool_rules"]:
        _compile(r["allow_if"])


def _scope(snapshot: dict, args: dict, now: str) -> dict:
    res = None
    for key, coll in (("reservation_id", "reservations"), ("order_id", "orders")):
        if key in args:
            res = snapshot.get(coll, {}).get(args[key])
            break
    users = snapshot.get("users", {})
    user = users.get(args.get("user_id") or (res or {}).get("user_id"))
    return {"__builtins__": {}, **FUNCS, "args": args, "db": snapshot, "now": now, "res": res, "user": user}


def check(ruleset: dict, snapshot: dict, tool: str, args: dict, now: str) -> list[Verdict]:
    scope = _scope(snapshot, args, now)
    out = []
    for r in ruleset["tool_rules"]:
        if r["tool"] != tool:
            continue
        try:
            out.append(Verdict(r["id"], bool(eval(_compile(r["allow_if"]), dict(scope))), r["policy_ref"]))
        except Exception as e:  # a rule that cannot be evaluated does not allow the call
            out.append(Verdict(r["id"], False, r["policy_ref"], f"{type(e).__name__}: {e}"))
    return out


def allowed(verdicts: list[Verdict]) -> bool:
    return all(v.ok for v in verdicts)
