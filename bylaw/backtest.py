"""C8: replay tau2 gold action sequences through rules.check and count the honest tasks a RuleSet blocks."""
import json
import os
import re
from pathlib import Path

DATA_DIR = Path(os.environ.get("TAU2_DATA_DIR", Path(__file__).resolve().parents[1] / ".context/tau2-bench/data"))

# Airline cancel reason (C2 v1.1 args["reason"]), first match wins. Health/weather are "other reasons" in the policy.
# ponytail: keyword rules over the scenario text, read against the 7 airline gold cancels; extend when a task misses.
REASON_RULES = [
    ("airline cancelled flight", r"airline (has )?cancel+ed|cancel+ed by the airline|flight (was|got|has been) cancel+ed"),
    ("other", r"\b(sick|unwell|ill|health|weather)\b"),
    ("change of plan", r"change of plans?|plans? (have |has )?changed|cancel the current one and book|mixup|mix-up"),
]


def infer_reason(text: str) -> str | None:
    return next((reason for reason, pat in REASON_RULES if re.search(pat, text, re.I)), None)


def _scenario_text(task) -> str:
    instr = (task.get("user_scenario") or {}).get("instructions") or {}
    return "\n".join(v for v in instr.values() if isinstance(v, str)) if isinstance(instr, dict) else str(instr)


def load_gold(domain) -> list[dict]:
    name = getattr(domain, "name", domain)
    tasks = json.loads((DATA_DIR / "tau2/domains" / name / "tasks.json").read_text())
    gold = []
    for t in tasks:
        actions = (t.get("evaluation_criteria") or {}).get("actions")
        if actions:
            gold.append({"id": t["id"], "actions": [{"tool": a["name"], "args": a["arguments"]} for a in actions],
                         "facts": {"reason": infer_reason(_scenario_text(t))}})
    return gold
