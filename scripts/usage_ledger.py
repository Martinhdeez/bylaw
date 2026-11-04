"""TR1: build reports/usage.json, the Muse usage ledger, from committed records only. Stdlib only.

Usage: uv run python scripts/usage_ledger.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUMMARY = "reports/live/dm3-summary.md"


def entry(id, stage, label, source, tokens, calls=None, input_tokens=None, output_tokens=None, seconds=None):
    return {"id": id, "stage": stage, "label": label, "source": source, "calls": calls, "input_tokens": input_tokens,
            "output_tokens": output_tokens, "tokens": tokens, "seconds": seconds}


def split(id, stage, label, source, calls, i, o):
    return entry(id, stage, label, source, i + o, calls, i, o)


def build() -> dict:
    out = []
    for dom, label in (("csdemo", "csdemo audit, Muse-guided search"), ("airline", "airline audit, Muse-guided search")):
        src = f"reports/{dom}.json"
        s = json.loads((ROOT / src).read_text())["stats"]
        if s["tokens"]:
            out.append(entry(f"{dom}-audit", "audit", label, src, s["tokens"], s["llm_calls"], seconds=s["seconds"]))
    bench = json.loads((ROOT / "reports/airline.bench.json").read_text())
    for r in bench["rows"]:
        if r.get("tokens"):  # the committed bench recorded no tokens; an entry appears once it does
            out.append(entry(f"airline-bench-{r['mode']}", "bench", f"airline bench, {r['mode']}",
                             "reports/airline.bench.json", r["tokens"], r["llm_calls"], seconds=r["seconds"]))
    summ = (ROOT / SUMMARY).read_text()
    for id, label in (("dm3-runs", "DM3, 18 runs"), ("dm4-runs", "DM4, 9 guarded runs"), ("dm5-runs", "DM5, 6 guarded runs")):
        c, i, o = map(int, re.search(rf"^\| {label} \| (\d+) \| (\d+) \| (\d+) \|", summ, re.M).groups())
        out.append(split(id, "live", f"{label}, csdemo live sessions", SUMMARY, c, i, o))
    for id, n, label in (("dm4-review-amend", 2, "DM4 review, amend calls (A8, A9)"),
                         ("dm5-amend", 4, "DM5, amend calls (A10, A11, A12)")):
        c, i, o = map(int, re.search(rf"({n}) calls, (\d+) prompt tokens, (\d+) completion tokens", summ).groups())
        out.append(split(id, "amend", label, SUMMARY, c, i, o))
    for p in sorted((ROOT / "reports/live").glob("*.json")):
        d = json.loads(p.read_text())
        if "usage" in d:
            u = d["usage"]
            out.append(split(p.stem, "live", f"{p.stem}, {d.get('framework', 'live')} run", f"reports/live/{p.name}",
                             u["requests"], u["input_tokens"], u["output_tokens"]))
    return {"entries": out}


if __name__ == "__main__":
    (ROOT / "reports/usage.json").write_text(json.dumps(build(), indent=1) + "\n")
