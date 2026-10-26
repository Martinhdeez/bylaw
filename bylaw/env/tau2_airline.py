"""tau2-bench airline as a C1 Domain: fresh env per chain, direct tool calls (no LLM), dict snapshots."""
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any, Callable

# tau2 reads TAU2_DATA_DIR at import time, so set the default before importing it.
os.environ.setdefault("TAU2_DATA_DIR", str(Path(__file__).resolve().parents[2] / ".context/tau2-bench/data"))

from loguru import logger  # noqa: E402
from tau2.domains.airline.data_model import FlightDB  # noqa: E402
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.domains.airline.utils import AIRLINE_DB_PATH  # noqa: E402

from bylaw.domain import Goal, StepResult  # noqa: E402
from bylaw.goals import GOALS, NOW  # noqa: E402

logger.disable("tau2")


@dataclass
class Tau2Domain:
    """A tau2 domain plug-in: how to load its DB and build an env over a copy of it."""

    name: str
    load_db: Callable[[], Any]
    make_env: Callable[[Any], Any]  # must deep-copy the db it is given

    @cached_property
    def base_db(self):
        return self.load_db()  # loaded once, never mutated

    def fresh_env(self):
        return self.make_env(self.base_db)


airline = Tau2Domain("airline", lambda: FlightDB.load(AIRLINE_DB_PATH), lambda db: get_environment(db=db))

READ_ONLY = {
    "get_user_details", "get_reservation_details", "list_all_airports", "search_direct_flight",
    "search_onestop_flight", "get_flight_status", "calculate", "transfer_to_human_agents",
}

RULESET = Path(__file__).resolve().parents[1] / "rulesets/airline.json"
CLASS_C_GOALS = {"G7"}  # spec v3 §3: pre-registered as Class C


def _wrap(fn):
    """Adapt a frozen G-predicate (FlightDB, FlightDB, step dicts) -> witnesses to the C1 Goal.check signature."""
    def check(before: dict, after: dict, chain: list[StepResult]) -> bool:
        steps = [{"tool": s.tool, "args": s.args, "meta": {"reservation_id": s.args.get("reservation_id")}} for s in chain]
        return bool(fn(FlightDB.model_validate(before), FlightDB.model_validate(after), steps))
    return check


def _target(goal_id: str, r: dict, u: dict) -> bool:
    return {
        "G1": r["cabin"] == "basic_economy",
        "G2": r["cabin"] == "basic_economy" and r["insurance"] == "no"
        and NOW - datetime.fromisoformat(r["created_at"]) > timedelta(hours=24),
        "G3": r["insurance"] == "no",
        "G6": u["membership"] == "regular" and r["insurance"] == "no" and r["cabin"] != "business",
    }.get(goal_id, True)


class AirlineDomain:
    name = "airline"
    now = NOW.isoformat()

    def __init__(self):
        env = airline.fresh_env()
        self.policy_text = env.get_policy()
        self.tools = [t.openai_schema for t in env.get_tools()]
        self._params = {t["function"]["name"]: set(t["function"]["parameters"]["properties"]) for t in self.tools}
        self.write_tools = set(self._params) - READ_ONLY
        refs = {g["id"]: g for g in json.loads(RULESET.read_text())["forbidden_goals"]}
        self.goals = {
            gid: Goal(gid, refs[gid]["name"], refs[gid]["policy_ref"], "C" if gid in CLASS_C_GOALS else "A", _wrap(fn))
            for gid, fn in GOALS.items()
        }

    def fresh_env(self):
        return airline.fresh_env()

    def call(self, env, tool: str, **args) -> StepResult:
        """Runs the tool with the args it accepts; extra conversation facts (C2 v1.1) are kept in StepResult.args."""
        accepted = {k: v for k, v in args.items() if k in self._params.get(tool, args)}
        try:
            out = env.use_tool(tool, **accepted)
            return StepResult(tool, args, True, out.model_dump() if hasattr(out, "model_dump") else out, None)
        except Exception as e:  # tool rejections are data, not crashes
            return StepResult(tool, args, False, None, f"{type(e).__name__}: {e}")

    def snapshot(self, env) -> dict:
        return env.tools.db.model_dump()

    def targets(self, goal_id: str) -> list[dict]:
        db = self.snapshot(self.fresh_env())
        return [
            {"user_id": r["user_id"], "reservation_id": rid}
            for rid, r in sorted(db["reservations"].items())
            if r["status"] != "cancelled" and _target(goal_id, r, db["users"][r["user_id"]])
        ]


@lru_cache(maxsize=1)
def make_domain() -> AirlineDomain:
    return AirlineDomain()


def diff(before: dict, after: dict) -> dict:
    """{collection: {key: {"before": ..., "after": ...}}} for every changed/added/removed record."""
    out = {}
    for coll in sorted(after):
        changed = {
            k: {"before": before[coll].get(k), "after": after[coll].get(k)}
            for k in sorted(before[coll].keys() | after[coll].keys())
            if before[coll].get(k) != after[coll].get(k)
        }
        if changed:
            out[coll] = changed
    return out
