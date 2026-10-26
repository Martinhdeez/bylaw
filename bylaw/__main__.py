"""python -m bylaw <subcommand>. Each subcommand is one function taking the parsed args."""
import argparse
import json
from pathlib import Path

HAND_RULESETS = Path(__file__).parent / "rulesets"


def cmd_backtest(a):
    from bylaw.backtest import backtest
    from bylaw.domain import get_domain

    domain = get_domain(a.domain)
    hand = json.loads((HAND_RULESETS / f"{a.domain}.json").read_text())
    base = backtest(domain, hand)
    res = backtest(domain, json.loads(Path(a.ruleset).read_text())) if a.ruleset else base
    print(json.dumps({
        "domain": a.domain, "ruleset": a.ruleset or f"bylaw/rulesets/{a.domain}.json",
        "tasks": res["tasks"], "blocked": res["blocked"], "unknown": res["unknown"],
        "baseline_blocked": base["blocked"], "delta": res["blocked"] - base["blocked"],
        "blocked_tasks": [r["id"] for r in res["results"] if r["blocked"]],
        "blocking": [{k: r[k] for k in ("id", "rule_id", "step")} for r in res["results"] if r["blocked"]],
        "unknown_tasks": [r["id"] for r in res["results"] if r["unknown"]],
    }, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(prog="bylaw")
    sub = p.add_subparsers(required=True)
    b = sub.add_parser("backtest", help="replay tau2 gold tasks through a RuleSet")
    b.add_argument("--domain", required=True)
    b.add_argument("--ruleset", help="RuleSet JSON to test; default: the hand RuleSet (the baseline)")
    b.set_defaults(fn=cmd_backtest)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
