"""Gold adjudication (C4 v1.7): which forbidden goals the benchmark's own gold trajectories reach."""
from bylaw.backtest import load_gold

_GOLD_GOALS: dict[tuple, dict[str, list[str]]] = {}


def gold_goals(domain) -> dict[str, list[str]]:
    """C4 v1.7: {goal_id: [task_id, ...]} for every goal some gold task makes true, evaluated on the diff of the
    whole task replayed on a fresh env. Only sanctioned goals are keys. Computed once per domain and goal set:
    amend.closes() audits a goal-restricted copy under the same name (FX2)."""
    key = (domain.name, frozenset(domain.goals))
    if key not in _GOLD_GOALS:
        hits: dict[str, list[str]] = {}
        for task in load_gold(domain):
            env = domain.fresh_env()
            before = domain.snapshot(env)
            results = [domain.call(env, a["tool"], **a["args"]) for a in task["actions"]]
            after = domain.snapshot(env)
            for gid, goal in domain.goals.items():
                if goal.check(before, after, results):
                    hits.setdefault(gid, []).append(task["id"])
        _GOLD_GOALS[key] = dict(sorted(hits.items()))
    return _GOLD_GOALS[key]


def goal_of(hole_key: str) -> str:
    """REQ-GA1-3: the goal of a hole key (`G1:T1QOBS` -> `G1`)."""
    return hole_key.split(":", 1)[0]
