"""RuleSet checker (contract C2): per-tool `allow_if` expressions over the DB snapshot before a call.

Expressions are Python expression syntax, accepted only if every AST node is on a whitelist, then
evaluated with no builtins. Names: args db now res user, plus comprehension variables.
Functions: len any all sum min max abs hours_between zip (zip: C2 v1.3). Methods: `.get` only.
Evaluation is bounded by work (C2 v1.5): comprehension iterations, elements built by `+` and elements reached
by comparisons and min/max count against BUDGET per evaluation. `*` is numeric only, numbers stay within
MAX_NUMBER, `%` is numeric only, `sum` takes a numeric start only, bytes are rejected.
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


BUDGET = 10**6  # comprehension iterations plus elements built or compared, per rule evaluation (C2 v1.5)
MAX_NUMBER = 10**15  # money/hours scale; any number a rule computes stays within +-MAX_NUMBER (C2 v1.5 addendum)
_NUM = (int, float)
_SEQ = (str, list, tuple)
_CONTAINERS = (list, tuple, dict, set, frozenset)


class _OverBudget(Exception):
    pass


def _num(x):
    if isinstance(x, _NUM) and abs(x) > MAX_NUMBER:
        raise _OverBudget(f"number over {MAX_NUMBER}")
    return x


class _Budget:
    """Work counter for one rule evaluation; _Guard routes comprehension iterables, arithmetic and comparison
    operands here. One instance per evaluation, so concurrent checks never share it."""

    def __init__(self):
        self.left = BUDGET

    def charge(self, n):
        self.left -= n
        if self.left < 0:
            raise _OverBudget(f"rule over the evaluation budget of {BUDGET} iterations and elements")

    def it(self, iterable):
        for x in iterable:
            self.charge(1)
            yield x

    def deep(self, x):
        """Charge every element reachable from x, counting shared sub-lists each time they are reached,
        which is what a deep ==, `in` or min/max over x can cost."""
        stack = [x]
        while stack:
            y = stack.pop()
            if isinstance(y, dict):
                self.charge(len(y))
                stack.extend(y.values())
            elif isinstance(y, _CONTAINERS):
                self.charge(len(y))
                stack.extend(y)
        return x

    def cmp(self, x):
        return self.deep(x) if isinstance(x, _CONTAINERS) else x

    def key(self, x):
        """Right side of `in`: dict and set lookups hash the left side only."""
        return x if isinstance(x, (dict, set, frozenset)) else self.cmp(x)

    @staticmethod
    def mul(a, b):
        if not (isinstance(a, _NUM) and isinstance(b, _NUM)):
            raise _OverBudget("* applies to numbers only")
        return _num(a * b)

    def add(self, a, b):
        if isinstance(a, _SEQ) and isinstance(b, _SEQ):
            self.charge(len(a) + len(b))
        return _num(a + b)

    @staticmethod
    def mod(a, b):
        if isinstance(a, str):  # '%0999999999d' % 1 builds the string in C
            raise _OverBudget("string formatting is not allowed")
        return _num(a % b)

    @staticmethod
    def arith(x):
        return _num(x)

    def min(self, *args, **kw):
        return min(*(self.deep(a) for a in args), **kw)

    def max(self, *args, **kw):
        return max(*(self.deep(a) for a in args), **kw)


def _sum(items, start=0):
    if not isinstance(start, _NUM):  # sum(lists, []) concatenates in C, out of reach of the budget
        raise _OverBudget("sum start must be a number")
    return _num(sum(items, start))


def _static_repeat(node):
    """`*` with a sequence or string display on either side (the runtime check catches the rest)."""
    seq = (ast.List, ast.Tuple, ast.Set, ast.Dict, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
    return isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult) and any(
        isinstance(x, seq) or (isinstance(x, ast.Constant) and isinstance(x.value, (str, bytes))) for x in (node.left, node.right))


def _call(name, *args):
    return ast.Call(ast.Name(name, ast.Load()), list(args), [])


class _Guard(ast.NodeTransformer):
    """Routes comprehension iterables, arithmetic and comparison operands through the budget. Runs after
    validation, so rules cannot name the helpers."""

    def visit_comprehension(self, node):
        self.generic_visit(node)
        node.iter = _call("_it", node.iter)
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        fn = {ast.Mult: "_mul", ast.Add: "_add", ast.Mod: "_mod"}.get(type(node.op))
        return _call(fn, node.left, node.right) if fn else _call("_arith", node)

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        return _call("_arith", node) if isinstance(node.op, (ast.USub, ast.UAdd)) else node

    def visit_Compare(self, node):
        self.generic_visit(node)
        if all(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops):
            return node  # identity, no element is compared
        node.left = _call("_cmp", node.left)
        node.comparators = [_call("_key" if isinstance(op, (ast.In, ast.NotIn)) else "_cmp", c)
                            for op, c in zip(node.ops, node.comparators)]
        return node


def _run(code, scope):
    b = _Budget()
    return eval(code, {**scope, "_it": b.it, "_mul": b.mul, "_add": b.add, "_mod": b.mod, "_arith": b.arith,
                       "_cmp": b.cmp, "_key": b.key, "min": b.min, "max": b.max})


FUNCS = {f.__name__: f for f in (len, any, all, min, max, abs, zip, hours_between)} | {"sum": _sum}
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
        if isinstance(n, ast.Constant) and isinstance(n.value, bytes):
            raise RuleError(f"bytes constant not allowed in {expr!r}")
        if isinstance(n, ast.Constant) and isinstance(n.value, _NUM) and abs(n.value) > MAX_NUMBER:
            raise RuleError(f"number over {MAX_NUMBER} in {expr!r}")
        if _static_repeat(n):
            raise RuleError(f"* applies to numbers only, in {expr!r}")
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
    return compile(ast.fix_missing_locations(_Guard().visit(tree)), "<rule>", "eval")


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
            out.append(Verdict(r["id"], bool(_run(_compile(r["allow_if"]), scope)), r["policy_ref"]))
        except Exception as e:  # a rule that cannot be evaluated does not allow the call
            out.append(Verdict(r["id"], False, r["policy_ref"], f"{type(e).__name__}: {e}"))
    return out


def allowed(verdicts: list[Verdict]) -> bool:
    return all(v.ok for v in verdicts)
