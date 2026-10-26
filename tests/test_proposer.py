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
           {"rationale": "", "where": "res['no_such_field']", "steps": [_cert()]}]
    chains = list(search(DOMAIN, RULES, 20, use_llm=True, llm=ScriptedMuse({"G7": bad})))
    assert chains == list(search(DOMAIN, RULES, 20, use_llm=False))


@pytest.mark.live
def test_live_muse_templates_bind_to_targets_and_change_the_search():
    chains = list(search(DOMAIN, RULES, 40, use_llm=True))
    assert sum(map(len, chains)) <= 40
    assert all(1 <= len(c) <= MAX_DEPTH and all(t in DOMAIN.write_tools for t, _ in c) for c in chains)
    blind = list(search(DOMAIN, RULES, 40, use_llm=False))
    assert chains[0] not in blind  # the first proposals are Muse's, not the BFS's
