"""C11 Proxy: one session over one fresh tau2 env; every call is checked by the RuleSet and a goal monitor first."""
import copy
import json
from pathlib import Path

from bylaw import rules

HAND_RULESETS = Path(__file__).resolve().parents[1] / "rulesets"


def default_ruleset(domain_name: str) -> dict:
    """C10 effective RuleSet; the hand RuleSet while bylaw.ratified (AP1) is not merged."""
    try:
        from bylaw.ratified import effective_ruleset
    except ModuleNotFoundError as e:
        if e.name != "bylaw.ratified":
            raise
        return json.loads((HAND_RULESETS / f"{domain_name}.json").read_text())
    return effective_ruleset(domain_name)


class Proxy:
    def __init__(self, domain, ruleset: dict | None = None, monitor: bool = True):
        self.domain = domain
        self.ruleset = default_ruleset(domain.name) if ruleset is None else ruleset
        self.monitor = monitor
        self.env = domain.fresh_env()
        self.start = domain.snapshot(self.env)
        self.history = []  # StepResults executed in this session, the chain the goals read

    def tools(self) -> list[dict]:
        return [{"name": f["name"], "description": f.get("description", ""), "input_schema": f["parameters"]}
                for f in (t["function"] for t in self.domain.tools)]

    def snapshot(self) -> dict:
        return self.domain.snapshot(self.env)

    def call(self, tool: str, args: dict) -> dict:
        out = {"ok": False, "blocked": True, "reason": None, "rule_id": None, "goal": None, "result": None}
        denied = next((v for v in rules.check(self.ruleset, self.snapshot(), tool, args, self.domain.now) if not v.ok), None)
        if denied:
            return out | {"rule_id": denied.rule_id, "reason": f"BLOCKED {denied.rule_id}: {denied.policy_ref}"}
        env = copy.deepcopy(self.env) if self.monitor and tool in self.domain.write_tools else self.env
        res = self.domain.call(env, tool, **copy.deepcopy(args))
        if env is not self.env and res.ok:
            after = self.domain.snapshot(env)
            for gid, goal in self.domain.goals.items():
                if goal.cls == "A" and goal.check(self.start, after, self.history + [res]):
                    return out | {"goal": gid, "reason": f"BLOCKED {gid}: {goal.name}"}
        self.env = env
        self.history.append(res)
        return out | {"ok": res.ok, "blocked": False, "reason": res.error, "result": res.output}
