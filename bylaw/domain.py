"""Domain interface (contract C1) and the registry of domain plug-ins."""
import importlib
from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass
class StepResult:
    tool: str
    args: dict
    ok: bool
    output: Any
    error: str | None


@dataclass
class Goal:
    id: str
    name: str
    policy_ref: str
    cls: str  # "A" counted | "C" ambiguity
    check: Callable[[dict, dict, list[StepResult]], bool]  # (db_before, db_after, chain) -> forbidden outcome reached


class Domain(Protocol):
    name: str
    policy_text: str
    tools: list[dict]
    write_tools: set[str]
    goals: dict[str, Goal]
    now: str

    def fresh_env(self) -> Any: ...
    def call(self, env, tool: str, **args) -> StepResult: ...
    def snapshot(self, env) -> dict: ...
    def targets(self, goal_id: str) -> list[dict]: ...


MODULES = {"airline": "bylaw.env.tau2_airline", "retail": "bylaw.env.tau2_retail"}


def get_domain(name: str) -> Domain:
    if name not in MODULES:
        raise ValueError(f"unknown domain {name!r}; known: {sorted(MODULES)}")
    try:
        module = importlib.import_module(MODULES[name])
    except ModuleNotFoundError as e:
        if e.name != MODULES[name]:
            raise
        raise RuntimeError(f"domain {name!r} is not available: {MODULES[name]} is missing") from e
    return module.make_domain()
