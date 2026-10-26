"""CLI (contract C5): python -m bylaw <subcommand>. Each subcommand is one function taking the parsed args."""
import argparse
import json
import os
import sys
from pathlib import Path

from bylaw import compiler
from bylaw.domain import get_domain

HAND_RULESETS = Path(__file__).parent / "rulesets"


def cmd_backtest(a):
    from bylaw.backtest import backtest

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
          f"{s['chains_tried']} chains, {s['tool_calls']} tool calls, {s['llm_calls']} LLM calls, "
          f"{s['tokens']} tokens, {s['seconds']}s")
    for e in report["holes"] + report["ambiguities"]:
        print(f"  {e['id']} {e['class']} {e['key']} replays {e['replays']} money_delta {e['money_delta']} "
              f"{' -> '.join(st['tool'] for st in e['chain'])}")


def cmd_compile(a):
    domain = get_domain(a.domain)
    ruleset = compiler.compile_policy(domain)
    Path(a.output).write_text(json.dumps(ruleset, indent=2) + "\n")
    print(f"wrote {a.output}: {len(ruleset['tool_rules'])} tool rules, {len(ruleset['forbidden_goals'])} forbidden goals")
    hand_path = HAND_RULESETS / f"{a.domain}.json"
    if not hand_path.exists():
        print(f"no hand RuleSet at {hand_path}; match rate not computed")
        return 0
    hand = json.loads(hand_path.read_text())
    m = compiler.match_report(ruleset, hand, domain)
    print(f"match rate: {m['rate']:.2f} ({m['matched'] + m['by_parts']}/{m['hand_rules']} hand rules: "
          f"{m['matched']} by one compiled rule, {m['by_parts']} by several; strict {m['strict_rate']:.2f}; "
          f"{m['discriminable']}/{m['hand_rules']} discriminable on the probes, {m['matched_discriminable']} of them "
          f"matched; {m['invalid']} invalid)")
    for r in m["rules"]:
        if r["status"] not in ("matched", "by_parts"):
            print(f"  {r['status']:9} {r['id']}")
    return 0


def cmd_amend(a):
    from bylaw.amend import apply, closes, draft
    from bylaw.backtest import backtest

    report = json.loads(Path(a.report).read_text())
    name = report["run"]["domain"]
    domain = get_domain(name)
    hand = json.loads((HAND_RULESETS / f"{name}.json").read_text())
    base = None if a.no_backtest else backtest(domain, hand)
    entries = report["holes"] + report.get("contradictions", [])  # Class A and Class B (01 v1.7)
    for h in entries:
        try:
            am = draft(domain, hand, h)
        except ValueError as e:  # the model failed twice: record it, never pass an invalid amendment through
            h.update(amendment=None, closes=False, error=str(e))
            print(f"  {h['id']} {h['key']} no amendment: {e}")
            continue
        patched = apply(hand, am)
        h["amendment"], h["closes"] = am, closes(domain, patched, h, report["run"].get("budget", 2000))
        line = f"  {h['id']} {h['class']} {h['key']} closes {h['closes']}"
        if base is not None:
            res = backtest(domain, patched)
            h["backtest"] = {"tasks": res["tasks"], "blocked": res["blocked"], "baseline_blocked": base["blocked"],
                             "blocked_tasks": [r["id"] for r in res["results"] if r["blocked"]]}
            line += f" blocked {res['blocked']}/{res['tasks']} (baseline {base['blocked']})"
        print(f"{line}: {am['policy_text']}", flush=True)
    Path(a.output).write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(f"wrote {a.output}: {sum(bool(h.get('closes')) for h in entries)}/{len(entries)} closed")


def cmd_proxy(a):
    from bylaw.proxy.core import Proxy
    from bylaw.proxy.mcp_server import serve

    serve(Proxy(get_domain(a.domain)))


def latest_report(domain: str) -> Path:
    """C9 report store (03 v1.1): the newest by mtime of <reports>/<domain>.json and <cache>/<domain>-*.json."""
    root = Path(__file__).resolve().parents[1]
    reports = root / os.environ.get("BYLAW_REPORTS_DIR", "reports")
    cache = root / os.environ.get("BYLAW_CACHE_DIR", ".cache/reports")
    found = [p for p in [reports / f"{domain}.json", *cache.glob(f"{domain}-*.json")] if p.exists()]
    if not found:
        raise SystemExit(f"no report for {domain}; run `python -m bylaw audit --domain {domain}` and pass --report")
    return max(found, key=lambda p: p.stat().st_mtime)


def cmd_replay(a):
    from bylaw.backtest import load_gold
    from bylaw.proxy.core import Proxy

    domain = get_domain(a.domain)

    def line(n, tool, out):  # C11 v1.1: "<n> ALLOWED|BLOCKED <tool>[ <reason>]"
        return f"{n} {'BLOCKED' if out['blocked'] else 'ALLOWED'} {tool}" + (f" {out['reason']}" if out["reason"] else "")

    if a.gold:
        gold, blocked, unknown = load_gold(domain), 0, 0
        for task in gold:
            steps = []
            for s in task["actions"]:
                args = dict(s["args"])
                if s["tool"] == "cancel_reservation" and "reason" not in args:  # C2 v1.1 fact, as in backtest
                    args["reason"] = task["facts"].get("reason")
                steps.append((s["tool"], args))
            if any(t == "cancel_reservation" and args["reason"] is None for t, args in steps):
                unknown += 1  # C8 unknown: no cancel reason to infer; not replayed, counts as not blocked
                continue
            proxy = Proxy(domain)
            for n, (tool, args) in enumerate(steps):
                out = proxy.call(tool, args)
                if out["blocked"]:
                    blocked += 1
                    print(f"task {task['id']}: {line(n, tool, out)}")
                    break
        print(f"unknown: {unknown}")
        print(f"blocked: {blocked}/{len(gold)}")
        return
    report = json.loads(Path(a.report or latest_report(a.domain)).read_text())
    hole = next((h for h in [*report["holes"], *report["ambiguities"], *report.get("contradictions", [])] if h["key"] == a.hole), None)
    if hole is None:
        raise SystemExit(f"hole {a.hole} not in the report")
    proxy = Proxy(domain)
    for n, s in enumerate(hole["chain"]):
        print(line(n, s["tool"], proxy.call(s["tool"], s["args"])))


def cmd_bench(a):
    from bylaw.report import audit

    domain = get_domain(a.domain)
    ruleset = json.loads((HAND_RULESETS / f"{a.domain}.json").read_text())
    modes, rows = a.modes.split(","), []
    if set(modes) - {"bfs", "muse"}:
        raise SystemExit(f"unknown mode in --modes {a.modes!r}; known: bfs, muse")
    for mode in modes:
        r = audit(domain, ruleset, a.budget, use_llm=mode == "muse")
        rows.append({"mode": mode, "holes": len(r["holes"]), "hole_keys": [h["key"] for h in r["holes"]],
                     "ambiguities": len(r["ambiguities"]), "ambiguity_keys": [h["key"] for h in r["ambiguities"]],
                     **{k: r["stats"][k] for k in ("tool_calls", "llm_calls", "tokens", "seconds")}, "commit": r["run"]["commit"]})
    Path(a.output).write_text(json.dumps({"domain": a.domain, "budget": a.budget, "rows": rows}, indent=2) + "\n")
    cols = ("mode", "holes", "ambiguities", "tool_calls", "llm_calls", "tokens", "seconds")
    print(f"bench {a.domain} budget {a.budget} -> {a.output}")
    print(" | ".join(f"{c:>11}" for c in cols))
    for row in rows:
        print(" | ".join(f"{row[c]!s:>11}" for c in cols))


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
    c = sub.add_parser("compile", help="compile a domain policy into a RuleSet with Muse")
    c.add_argument("--domain", required=True)
    c.add_argument("-o", "--output", required=True)
    c.set_defaults(fn=cmd_compile)
    am = sub.add_parser("amend", help="draft, prove and backtest one amendment per hole of a report")
    am.add_argument("report")
    am.add_argument("-o", "--output", default="amended.json")
    am.add_argument("--no-backtest", action="store_true", help="skip the gold-task backtest")
    am.set_defaults(fn=cmd_amend)
    px = sub.add_parser("proxy", help="MCP stdio server enforcing the effective RuleSet and the goal monitor")
    px.add_argument("--domain", required=True)
    px.set_defaults(fn=cmd_proxy)
    rp = sub.add_parser("replay", help="replay a report hole or the gold tasks through the proxy")
    rp.add_argument("--domain", required=True)
    what = rp.add_mutually_exclusive_group(required=True)
    what.add_argument("--hole", help="hole key, e.g. G1:T1QOBS")
    what.add_argument("--gold", action="store_true", help="replay the tau2 gold tasks; prints blocked: N/total")
    rp.add_argument("--report", help="C4 report; default: the latest in the report store")
    rp.set_defaults(fn=cmd_replay)
    be = sub.add_parser("bench", help="holes per tool-call budget, Muse-guided vs blind BFS")
    be.add_argument("--domain", required=True)
    be.add_argument("--budget", type=int, required=True, help="write tool calls each mode may execute")
    be.add_argument("--modes", default="bfs,muse", help="comma-separated: bfs, muse")
    be.add_argument("-o", "--output", default="bench.json")
    be.set_defaults(fn=cmd_bench)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
