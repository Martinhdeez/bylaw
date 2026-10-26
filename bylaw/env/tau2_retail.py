"""tau2 retail as a Bylaw domain (contract C1): fresh env per chain, direct tool calls, dict snapshots."""
import inspect
import os
from dataclasses import dataclass, field
from pathlib import Path

# tau2 reads TAU2_DATA_DIR at import time, so set the default before importing it.
os.environ.setdefault("TAU2_DATA_DIR", str(Path(__file__).resolve().parents[2] / ".context/tau2-bench/data"))

from loguru import logger  # noqa: E402
from tau2.domains.retail.data_model import RetailDB  # noqa: E402
from tau2.domains.retail.environment import get_environment  # noqa: E402
from tau2.domains.retail.utils import RETAIL_DB_PATH, RETAIL_POLICY_PATH  # noqa: E402
from tau2.environment.toolkit import ToolType  # noqa: E402

from bylaw.domain import Goal, StepResult  # noqa: E402
from bylaw.goals_retail import GOALS  # noqa: E402

logger.disable("tau2")

# Order statuses each goal starts from (argument seeds for the search).
_SEED_STATUS = {
    "R1": {"delivered"}, "R2": {"pending", "processed", "cancelled"}, "R3": {"cancelled", "processed"},
    "R4": {"pending"}, "R5": {"pending"}, "R6": {"pending"}, "R7": {"delivered"}, "R8": {"pending", "delivered"},
}


@dataclass
class RetailDomain:
    base_db: RetailDB  # loaded once, never mutated: get_environment deep-copies it
    name: str = "retail"
    policy_text: str = field(default_factory=lambda: Path(RETAIL_POLICY_PATH).read_text())
    goals: dict[str, Goal] = field(default_factory=lambda: dict(GOALS))
    now: str = "2024-05-15T15:00:00"  # retail tools never read a clock; same fixed time as tau2 airline

    def __post_init__(self):
        kit = self.fresh_env().tools
        self.tools = [t.openai_schema for t in kit.get_tools().values()]
        self.write_tools = {n for n in kit.tools if kit.tool_type(n) == ToolType.WRITE}
        self._params = {n: set(inspect.signature(f).parameters) for n, f in kit.tools.items()}

    def fresh_env(self):
        return get_environment(db=self.base_db)

    def call(self, env, tool: str, **args) -> StepResult:
        accepted = {k: v for k, v in args.items() if k in self._params.get(tool, ())}  # drop conversation facts (C2 v1.1)
        try:
            out = env.use_tool(tool, **accepted)
            return StepResult(tool, args, True, out.model_dump() if hasattr(out, "model_dump") else out, None)
        except Exception as e:  # tool rejections are data, not crashes
            return StepResult(tool, args, False, None, f"{type(e).__name__}: {e}")

    def snapshot(self, env) -> dict:
        return env.tools.db.model_dump(mode="json")

    def targets(self, goal_id: str) -> list[dict]:
        db = self.base_db
        return [
            {"user_id": o.user_id, "order_id": oid, "payment_method_ids": sorted(db.users[o.user_id].payment_methods)}
            for oid, o in sorted(db.orders.items()) if o.status in _SEED_STATUS[goal_id]
        ]


def make_domain() -> RetailDomain:
    return RetailDomain(RetailDB.load(RETAIL_DB_PATH))
