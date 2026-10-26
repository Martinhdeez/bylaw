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


def cmd_audit(a):
    from bylaw.domain import get_domain
    from bylaw.report import audit

    domain = get_domain(a.domain)
    report = audit(domain, json.loads((HAND_RULESETS / f"{a.domain}.json").read_text()), a.budget, use_llm=not a.no_llm)
    Path(a.output).write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    s = report["stats"]
    print(f"wrote {a.output}: {len(report['holes'])} Class A holes, {len(report['ambiguities'])} ambiguities; "
          f"{s['chains_tried']} chains, {s['tool_calls']} tool calls, {s['seconds']}s")
    for e in report["holes"] + report["ambiguities"]:
        print(f"  {e['id']} {e['class']} {e['key']} replays {e['replays']} money_delta {e['money_delta']} "
              f"{' -> '.join(st['tool'] for st in e['chain'])}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="bylaw")
    sub = p.add_subparsers(required=True)
    b = sub.add_parser("backtest", help="replay tau2 gold tasks through a RuleSet")
    b.add_argument("--domain", required=True)
    b.add_argument("--ruleset", help="RuleSet JSON to test; default: the hand RuleSet (the baseline)")
    b.set_defaults(fn=cmd_backtest)
    au = sub.add_parser("audit", help="search, execute and prove policy holes")
    au.add_argument("--domain", required=True)
    au.add_argument("--no-llm", action="store_true", help="blind BFS search, no Muse calls")
    au.add_argument("--budget", type=int, default=2000, help="write tool calls the search may execute")
    au.add_argument("-o", "--output", default="report.json")
    au.set_defaults(fn=cmd_audit)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
