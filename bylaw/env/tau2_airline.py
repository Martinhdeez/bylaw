"""tau2-bench as the simulator: fresh env per chain, direct tool calls (no LLM), DB snapshot + diff."""
import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Callable

# tau2 reads TAU2_DATA_DIR at import time, so set the default before importing it.
os.environ.setdefault("TAU2_DATA_DIR", str(Path(__file__).resolve().parents[2] / ".context/tau2-bench/data"))

from loguru import logger  # noqa: E402
from tau2.domains.airline.data_model import FlightDB  # noqa: E402
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.domains.airline.utils import AIRLINE_DB_PATH  # noqa: E402

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


@dataclass
class StepResult:
    tool: str
    args: dict
    result: Any = None
    error: str | None = None
    meta: dict = field(default_factory=dict)


def call(env, tool: str, **args) -> StepResult:
    try:
        out = env.use_tool(tool, **args)
        return StepResult(tool, args, out.model_dump() if hasattr(out, "model_dump") else out)
    except Exception as e:  # tool rejections are data, not crashes
        return StepResult(tool, args, error=f"{type(e).__name__}: {e}")


def snapshot(env):
    return env.tools.db.model_copy(deep=True)


def diff(before, after) -> dict:
    """{collection: {key: {"before": ..., "after": ...}}} for every changed/added/removed record."""
    b, a = before.model_dump(), after.model_dump()
    out = {}
    for coll in a:
        changed = {
            k: {"before": b[coll].get(k), "after": a[coll].get(k)}
            for k in b[coll].keys() | a[coll].keys()
            if b[coll].get(k) != a[coll].get(k)
        }
        if changed:
            out[coll] = changed
    return out
