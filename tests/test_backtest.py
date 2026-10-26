from bylaw.backtest import load_gold


def test_airline_gold_tasks_are_the_43_with_actions_in_order():
    gold = load_gold("airline")
    assert len(gold) == 43
    task1 = next(t for t in gold if t["id"] == "1")
    assert task1["actions"] == [
        {"tool": "get_user_details", "args": {"user_id": "raj_sanchez_7340"}},
        {"tool": "get_reservation_details", "args": {"reservation_id": "Q69X3R"}},
    ]


def test_retail_gold_tasks_are_the_112_with_actions():
    assert len(load_gold("retail")) == 112


def _facts(task_id):
    return next(t for t in load_gold("airline") if t["id"] == task_id)["facts"]


def test_cancel_reason_inferred_from_the_user_scenario():
    assert _facts("19")["reason"] == "other"  # "cancel the trip using the travel insurance as you feel unwell"
    assert _facts("7")["reason"] == "other"  # "You are sick."
    assert _facts("14")["reason"] == "change of plan"  # "cancel the current one and book a new one"


def test_cancel_reason_is_none_when_the_scenario_gives_no_reason():
    assert _facts("39")["reason"] is None  # gives up the seat; no policy reason stated


def test_airline_cancelled_flight_reason():
    from bylaw.backtest import infer_reason

    assert infer_reason("Your flight was cancelled and you want a refund.") == "airline cancelled flight"
    assert infer_reason("You just want to cancel.") is None
