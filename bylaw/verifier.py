"""Verifier (EX1): a hole is proven when each of N fresh replays passes every rule, every tool call
succeeds, reproduces the expected diff, and the goal predicate holds on the full before/after DB."""
from bylaw.executor import canon, run


def prove(domain, ruleset: dict, goal_id: str, chain: list[dict], expected_diff: dict, n: int = 5) -> str:
    """Returns "k/n", k = replays that reproduce the hole."""
    goal, want, k = domain.goals[goal_id], canon(expected_diff), 0
    for _ in range(n):
        r = run(domain, chain, ruleset)
        k += (len(r["steps"]) == len(chain) and all(s["ok"] for s in r["steps"])
              and canon(r["diff"]) == want and goal.check(r["before"], r["after"], r["results"]))
    return f"{k}/{n}"
