"""AM1: amendment drafter, apply and closure proof (REQ-AM1-1..3), model scripted offline."""
import copy
import json

import pytest

from bylaw import amend
from bylaw.domain import get_domain
from bylaw.env.tau2_airline import RULESET

DOMAIN = get_domain("airline")
HAND = json.loads(RULESET.read_text())

# A G1 hole the hand RuleSet leaves open (also in the acceptance tests): cabin up, change flight, cabin back.
RES, PAY = "Q79V9W", "credit_card_1718968"


def _flights(cabin, flight):
    return {"reservation_id": RES, "cabin": cabin, "flights": [{"flight_number": flight, "date": "2024-05-28"}], "payment_id": PAY}


HOLE = {"id": "H3", "class": "A", "goal": "G1", "key": f"G1:{RES}", "title": "", "money_delta": 0.0, "diff": {},
        "goal_true": True, "replays": "5/5",
        "chain": [{"tool": "update_reservation_flights", "args": a, "ok": True, "verdicts": []}
                  for a in (_flights("economy", "HAT265"), _flights("economy", "HAT073"), _flights("basic_economy", "HAT073"))]}

DOWNGRADE = {"id": "R-am-downgrade", "tool": "update_reservation_flights", "note": "",
             "allow_if": "not (args.get('cabin') == 'basic_economy' and res['cabin'] != 'basic_economy')",
             "policy_ref": "A reservation cannot be moved back to basic economy."}
NOOP = dict(DOWNGRADE, id="R-am-noop", allow_if="True")


def answer(rule, text="A reservation cannot be moved back to basic economy."):
    return {"policy_text": text, "rule_patch": [rule], "rationale": "The downgrade is the step to refuse."}


class Scripted:
    def __init__(self, *payloads):
        self.payloads, self.messages = payloads, []

    def __call__(self, messages, schema, name, effort=None, **opts):
        self.messages.append(messages)
        return copy.deepcopy(self.payloads[min(len(self.messages), len(self.payloads)) - 1])


def test_draft_ids_the_amendment_after_its_hole():
    am = amend.draft(DOMAIN, HAND, HOLE, llm=Scripted(answer(DOWNGRADE)))
    assert (am["id"], am["hole_id"]) == ("A3", "H3")


@pytest.mark.parametrize("bad", [dict(DOWNGRADE, tool="no_such_tool"), dict(DOWNGRADE, id="R-flights-active")],
                         ids=["unknown_tool", "id_taken_by_the_ruleset"])
def test_draft_retries_a_patch_that_cannot_join_the_ruleset(bad):
    llm = Scripted(answer(bad), answer(DOWNGRADE))
    assert amend.draft(DOMAIN, HAND, HOLE, llm=llm)["rule_patch"] == [DOWNGRADE]
    assert len(llm.messages) == 2


def test_the_retry_tells_the_model_what_was_wrong():
    # Same messages twice would also replay the cached bad reply from bylaw.llm's disk cache.
    llm = Scripted(answer(dict(DOWNGRADE, tool="no_such_tool")), answer(DOWNGRADE))
    amend.draft(DOMAIN, HAND, HOLE, llm=llm)
    assert llm.messages[1] != llm.messages[0] and "no_such_tool" in json.dumps(llm.messages[1][len(llm.messages[0]):])


def test_the_prompt_carries_the_policy_and_the_hole_chain():
    llm = Scripted(answer(DOWNGRADE))
    amend.draft(DOMAIN, HAND, HOLE, llm=llm)
    text = json.dumps(llm.messages[0])
    assert DOMAIN.goals["G1"].policy_ref[:40] in text and "HAT073" in text and "R-flights-not-basic" in text


def test_closes_needs_the_chain_blocked_and_no_hole_left_for_the_goal(monkeypatch):
    assert amend.closes(DOMAIN, amend.apply(HAND, {"rule_patch": [NOOP]}), HOLE, budget=40) is False
    # Blocking the downgrade stops this chain; a goal re-audit that still finds a G1 hole keeps it open.
    patched = amend.apply(HAND, {"rule_patch": [DOWNGRADE]})
    monkeypatch.setattr(amend, "audit", lambda d, rs, budget: {"holes": [{"goal": "G1"}]})
    assert amend.closes(DOMAIN, patched, HOLE, budget=40) is False
    monkeypatch.setattr(amend, "audit", lambda d, rs, budget: {"holes": []})
    assert amend.closes(DOMAIN, patched, HOLE, budget=40) is True


def test_the_reaudit_searches_only_the_holes_goal(monkeypatch):
    seen = []
    monkeypatch.setattr(amend, "audit", lambda d, rs, budget: seen.append(set(d.goals)) or {"holes": []})
    amend.closes(DOMAIN, amend.apply(HAND, {"rule_patch": [DOWNGRADE]}), HOLE, budget=40)
    assert seen == [{"G1"}] and len(DOMAIN.goals) == 7


@pytest.mark.live
def test_live_muse_drafts_an_amendment_that_blocks_the_hole():
    am = amend.draft(DOMAIN, HAND, HOLE)
    assert 1 <= len(amend.sentences(am["policy_text"])) <= 2
    assert amend.blocked(DOMAIN, amend.apply(HAND, am), HOLE["chain"])
