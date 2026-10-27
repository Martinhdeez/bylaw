"""EX1: bounded BFS behind the C6 interface: write tools only, depth <= 4, budget = write steps yielded."""
import itertools
import json

import pytest

from bylaw.domain import get_domain
from bylaw.env.tau2_airline import RULESET
from bylaw.proposer import MAX_DEPTH, search

DOMAIN = get_domain("airline")
RULES = json.loads(RULESET.read_text())


@pytest.mark.parametrize("budget", [0, 1, 50])
def test_search_never_yields_more_write_steps_than_the_budget(budget):
    chains = list(itertools.islice(search(DOMAIN, RULES, budget, use_llm=False), budget + 1))
    assert sum(len(c) for c in chains) <= budget
    assert chains or budget == 0


def test_chains_are_write_only_bounded_and_shortest_first():
    chains = list(search(DOMAIN, RULES, 300, use_llm=False))
    assert all(1 <= len(c) <= MAX_DEPTH and all(t in DOMAIN.write_tools for t, _ in c) for c in chains)
    assert [len(c) for c in chains[:5]] == [1] * 5  # BFS: depth 1 comes before deeper chains


def test_search_is_deterministic():
    a = list(search(DOMAIN, RULES, 100, use_llm=False))
    assert a == list(search(DOMAIN, RULES, 100, use_llm=False))


# ---------- PR1: Muse templates first, then BFS on the rest of the budget ----------

def _cert(complaint="delayed"):
    return {"tool": "send_certificate", "args_json": json.dumps({
        "user_id": "=res['user_id']", "reservation_id": "=res['reservation_id']", "complaint": complaint,
        "changed_or_cancelled": True, "amount": "=50 * len(res['passengers'])"})}


DELAYED = ("user['membership'] != 'regular' and any(db['flights'][f['flight_number']]['dates'].get(f['date'], {})"
           ".get('status') == 'delayed' for f in res['flights'])")
G7_TWICE = {"rationale": "two delay certificates for one reservation", "where": DELAYED, "steps": [_cert(), _cert()]}


class ScriptedMuse:
    """Stands in for bylaw.llm.structured: answers `templates` for the goal named in the prompt, nothing otherwise."""

    def __init__(self, templates_by_goal):
        self.templates, self.calls = templates_by_goal, []

    def __call__(self, messages, schema, name, effort=None, **opts):
        goal = json.loads(messages[-1]["content"])["goal"]["id"]
        self.calls.append({"goal": goal, "effort": effort, "messages": messages})
        return {"templates": self.templates.get(goal, [])}


def _delayed_non_regular(rid):
    db = DOMAIN.snapshot(DOMAIN.fresh_env())
    r = db["reservations"][rid]
    return db["users"][r["user_id"]]["membership"] != "regular" and any(
        db["flights"][f["flight_number"]]["dates"].get(f["date"], {}).get("status") == "delayed" for f in r["flights"])


def test_muse_is_asked_once_per_goal_with_high_effort_and_sees_the_goal_rules_and_tools():
    muse = ScriptedMuse({})
    list(search(DOMAIN, RULES, 10, use_llm=True, llm=muse))
    assert sorted(c["goal"] for c in muse.calls) == sorted(DOMAIN.goals)
    assert all(c["effort"] == "high" for c in muse.calls)
    prompt = json.loads(muse.calls[0]["messages"][-1]["content"])
    assert prompt["goal"]["policy_ref"] == DOMAIN.goals[prompt["goal"]["id"]].policy_ref
    assert {r["id"] for r in prompt["rules"]} == {r["id"] for r in RULES["tool_rules"]}
    assert {t["function"]["name"] for t in prompt["write_tools"]} == DOMAIN.write_tools
    assert prompt["targets"]["examples"]


def test_muse_templates_come_first_bound_to_the_targets_they_filter():
    chains = list(search(DOMAIN, RULES, 40, use_llm=True, llm=ScriptedMuse({"G7": [G7_TWICE]})))
    muse = [c for c in chains if [t for t, _ in c] == ["send_certificate"] * 2]
    assert muse and chains[:len(muse)] == muse  # Muse first
    assert len({a["reservation_id"] for c in muse for _, a in c}) == len(muse)  # one binding per target
    for (_, a), (_, b) in muse:
        assert a == b and _delayed_non_regular(a["reservation_id"])
    assert len(chains) > len(muse)  # BFS fills the rest
    assert sum(map(len, chains)) <= 40


@pytest.mark.parametrize("budget", [0, 1, 7, 40])
def test_llm_search_never_exceeds_the_budget(budget):
    chains = list(search(DOMAIN, RULES, budget, use_llm=True, llm=ScriptedMuse({"G7": [G7_TWICE]})))
    assert sum(map(len, chains)) <= budget


def test_a_template_the_rules_forbid_at_step_one_spends_no_budget():
    chains = list(search(DOMAIN, RULES, 20, use_llm=True,
                         llm=ScriptedMuse({"G7": [{**G7_TWICE, "steps": [_cert("lost luggage")]}]})))
    assert chains == list(search(DOMAIN, RULES, 20, use_llm=False))


def test_malformed_templates_are_ignored():
    bad = [{"rationale": "", "where": "True", "steps": [{"tool": "send_certificate", "args_json": "{not json"}]},
           {"rationale": "", "where": "True", "steps": [{"tool": "get_user_details", "args_json": "{}"}]},
           {"rationale": "", "where": "True", "steps": [_cert()] * 5},
           {"rationale": "", "where": "__import__('os')", "steps": [_cert()]},
           {"rationale": "", "where": "res['no_such_field']", "steps": [_cert()]},
           # plain eval would accept these; the bounded rules evaluator must reject them (untrusted Muse output)
           {"rationale": "", "where": "9 ** 2 > 0 and " + DELAYED, "steps": [_cert()]},
           {"rationale": "", "where": "res.keys() is not None and " + DELAYED, "steps": [_cert()]}]
    chains = list(search(DOMAIN, RULES, 20, use_llm=True, llm=ScriptedMuse({"G7": bad})))
    assert chains == list(search(DOMAIN, RULES, 20, use_llm=False))


def _is_cert(chain):
    return [t for t, _ in chain] == ["send_certificate"] * 2


def test_a_template_that_keeps_missing_loses_its_turns_and_one_that_hits_keeps_them():
    """v1.8: the caller sends back (executed, hit); a template that misses is dropped early."""
    gen = search(DOMAIN, RULES, 40, use_llm=True, llm=ScriptedMuse({"G7": [G7_TWICE]}))
    missed = [next(gen)] + [gen.send((2, False)) for _ in range(3)]
    assert [_is_cert(c) for c in missed] == [True, True, False, False]
    gen = search(DOMAIN, RULES, 40, use_llm=True, llm=ScriptedMuse({"G7": [G7_TWICE]}))
    hit = [next(gen)] + [gen.send((2, True)) for _ in range(3)]
    assert all(map(_is_cert, hit))


@pytest.mark.parametrize("use_llm", [False, True])
def test_the_budget_is_charged_with_executed_steps_when_the_caller_reports_them(use_llm):
    """C6 v1.8: a chain blocked at step 1 costs 0; without feedback each chain costs its length."""
    muse = ScriptedMuse({"G7": [G7_TWICE]})
    gen = search(DOMAIN, RULES, 2, use_llm=use_llm, llm=muse)
    blocked = [next(gen)] + [gen.send((0, False)) for _ in range(5)]  # never charged: the search keeps going
    assert len(blocked) == 6
    gen = search(DOMAIN, RULES, 2, use_llm=use_llm, llm=muse)
    first = next(gen)
    rest = []
    try:
        while True:
            rest.append(gen.send((len(first if not rest else rest[-1]), False)))
    except StopIteration:
        pass
    assert len(first) + sum(map(len, rest)) <= 2


def test_a_failed_muse_call_for_one_goal_leaves_the_others_and_the_bfs():
    """C6 v1.8: an error for one goal never aborts the search."""
    ok = ScriptedMuse({"G7": [G7_TWICE]})

    def flaky(messages, schema, name, **kw):
        if json.loads(messages[-1]["content"])["goal"]["id"] == "G1":
            raise RuntimeError("empty reply from muse-spark-1.3 (finish_reason=length)")
        return ok(messages, schema, name, **kw)

    chains = list(search(DOMAIN, RULES, 40, use_llm=True, llm=flaky))
    assert _is_cert(chains[0]) and not all(map(_is_cert, chains))


@pytest.mark.live
def test_live_muse_templates_bind_to_targets_and_change_the_search():
    chains = list(search(DOMAIN, RULES, 40, use_llm=True))
    assert sum(map(len, chains)) <= 40
    assert all(1 <= len(c) <= MAX_DEPTH and all(t in DOMAIN.write_tools for t, _ in c) for c in chains)
    blind = list(search(DOMAIN, RULES, 40, use_llm=False))
    assert chains[0] not in blind  # the first proposals are Muse's, not the BFS's
