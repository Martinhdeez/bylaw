"""Acceptance tests for EX1 and the CLI side of PR1: audit CLI, report JSON (C4), replay.

Written blind from docs/plan/01-engine/requirements.md and contracts.md (C1, C4, C5, v1.1).
v1.2 adds the diff format, the hole key and the replay signature.
v1.7 (gold adjudication): proven findings on gold-sanctioned goals move from `holes` (Class A) to
`contradictions` (Class B). The EX1 proof checks apply to both lists ("findings").
Domain facts (DB shape, clock 2024-05-15T15:00:00, deterministic ids) come from .context/tau2-bench.
Helpers live in this file on purpose: the wave-1 conftest is on another unmerged branch.
"""
import copy
import importlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUDGET = 2000  # C5: --budget N=2000
SMALL_BUDGET = 25
COUNTED_GOALS = {"G1", "G2", "G5"}  # pre-registered Class A airline goals
# v1.7 / REQ-GA1-1: goals some airline gold task reaches (tasks.json), hence Class B when proven.
GOLD_SANCTIONED = {"G1": {"32"}, "G2": {"7"}, "G4": {"25"}, "G5": {"18"}}


def findings(r: dict) -> list[dict]:
    """Proven Class A holes and Class B contradictions (v1.7)."""
    return r["holes"] + r["contradictions"]


def run_cli(*argv, timeout=1800):
    return subprocess.run([sys.executable, "-m", "bylaw", *argv], cwd=ROOT,
                          capture_output=True, text=True, timeout=timeout)


def audit(tmp_dir: Path, *extra) -> dict:
    out = tmp_dir / "report.json"
    proc = run_cli("audit", "--domain", "airline", *extra, "-o", str(out))
    assert proc.returncode == 0, proc.stderr[-4000:]
    assert out.exists(), "audit -o did not write the report"
    return json.loads(out.read_text())


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, default=str)


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)


def assert_c4_entry(e: dict, cls: str) -> None:
    assert isinstance(e["id"], str) and e["id"]
    assert e["class"] == cls
    assert isinstance(e["goal"], str) and e["goal"]
    assert isinstance(e["title"], str)
    assert isinstance(e["money_delta"], (int, float))
    assert isinstance(e["chain"], list) and e["chain"]
    for step in e["chain"]:
        assert isinstance(step["tool"], str) and step["tool"]
        assert isinstance(step["args"], dict)
        assert isinstance(step["ok"], bool)
        assert isinstance(step["verdicts"], list)
        for v in step["verdicts"]:
            assert isinstance(v["rule_id"], str) and v["rule_id"]
            assert isinstance(v["ok"], bool)
            assert isinstance(v["policy_ref"], str)
    assert isinstance(e["key"], str) and e["key"].startswith(e["goal"] + ":"), e.get("key")
    assert len(e["key"]) > len(e["goal"]) + 1, "key needs a target id"
    assert_diff_shape(e["diff"])
    assert isinstance(e["goal_true"], bool)
    assert isinstance(e["replays"], str)


def assert_diff_shape(diff: dict) -> None:
    """v1.2: {collection: {record_id: {"before": dict|null, "after": dict|null}}}, changed records only."""
    assert isinstance(diff, dict)
    for coll, records in diff.items():
        assert isinstance(coll, str) and isinstance(records, dict)
        for rid, change in records.items():
            assert set(change) == {"before", "after"}, (coll, rid)
            assert change["before"] is None or isinstance(change["before"], dict)
            assert change["after"] is None or isinstance(change["after"], dict)
            assert change["before"] != change["after"], f"unchanged record {coll}/{rid} in diff"


def expected_diff(before: dict, after: dict) -> dict:
    """The v1.2 diff worked out from two C1 snapshots."""
    out = {}
    for coll in set(before) | set(after):
        b, a = before.get(coll) or {}, after.get(coll) or {}
        changed = {rid: {"before": b.get(rid), "after": a.get(rid)}
                   for rid in set(b) | set(a) if canon(b.get(rid)) != canon(a.get(rid))}
        if changed:
            out[coll] = changed
    return out


def assert_c4_shape(r: dict) -> None:
    """C4 field by field, independent of REPORT_SCHEMA."""
    run = r["run"]
    for key in ("commit", "domain", "model", "mode", "started", "goals_commit"):
        assert isinstance(run[key], str), key
    assert run["mode"] in ("bfs", "muse")
    assert isinstance(run["budget"], int)
    assert isinstance(r["holes"], list)
    assert isinstance(r["ambiguities"], list)
    for h in r["holes"]:
        assert_c4_entry(h, "A")
    assert isinstance(r["contradictions"], list)
    for c in r["contradictions"]:
        assert_c4_entry(c, "B")
    for a in r["ambiguities"]:
        assert_c4_entry(a, "C")
    ids = [e["id"] for e in findings(r) + r["ambiguities"]]
    assert len(ids) == len(set(ids)), "hole/ambiguity ids must be unique"
    keys = [e["key"] for e in findings(r) + r["ambiguities"]]
    assert len(keys) == len(set(keys)), "hole/ambiguity keys must be unique"
    s = r["stats"]
    for key in ("chains_tried", "tool_calls", "llm_calls", "tokens"):
        assert isinstance(s[key], int) and s[key] >= 0, key
    assert isinstance(s["seconds"], (int, float)) and s["seconds"] >= 0


def cancel_rebook_target(chain: list[dict], db: dict) -> str | None:
    """Reservation id cancelled and then rebooked for the same user in this chain, else None."""
    for i, step in enumerate(chain):
        if step["tool"] != "cancel_reservation":
            continue
        rid = step["args"].get("reservation_id")
        res = db["reservations"].get(rid)
        if res is None:
            continue
        for later in chain[i + 1:]:
            if later["tool"] == "book_reservation" and later["args"].get("user_id") == res["user_id"]:
                return rid
    return None


def within_24h(rid: str, db: dict, now: str) -> bool:
    created = parse_iso(db["reservations"][rid]["created_at"])
    return (parse_iso(now) - created).total_seconds() < 24 * 3600


def replay_by_contract(domain, chain: list[dict]):
    """Run a report chain on a fresh env through C1 only."""
    env = domain.fresh_env()
    before = copy.deepcopy(domain.snapshot(env))
    results = [domain.call(env, step["tool"], **copy.deepcopy(step["args"])) for step in chain]
    after = copy.deepcopy(domain.snapshot(env))
    return before, after, results


@pytest.fixture(scope="module")
def domain():
    return importlib.import_module("bylaw.domain").get_domain("airline")


@pytest.fixture(scope="module")
def fresh_db(domain):
    return domain.snapshot(domain.fresh_env())


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    """`audit --domain airline --no-llm`, default budget."""
    return audit(tmp_path_factory.mktemp("audit_nollm"), "--no-llm")


@pytest.fixture(scope="module")
def small_report(tmp_path_factory):
    return audit(tmp_path_factory.mktemp("audit_small"), "--no-llm", "--budget", str(SMALL_BUDGET))


# ---------- REQ-EX1-1 ----------

def test_REQ_EX1_1_report_validates_against_REPORT_SCHEMA(report):
    schema = importlib.import_module("bylaw.report").REPORT_SCHEMA
    jsonschema.validate(report, schema)


def test_REQ_EX1_1_REPORT_SCHEMA_is_not_permissive(report):
    # A schema that accepts anything would make the check above meaningless.
    schema = importlib.import_module("bylaw.report").REPORT_SCHEMA
    for drop in ("run", "holes", "stats"):
        broken = copy.deepcopy(report)
        del broken[drop]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(broken, schema)
    broken = copy.deepcopy(report)
    broken["holes"] = "none"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(broken, schema)


def test_REQ_EX1_1_report_has_the_c4_shape(report):
    assert_c4_shape(report)


def test_REQ_EX1_1_run_block_describes_a_no_llm_airline_run(report):
    assert report["run"]["domain"] == "airline"
    assert report["run"]["mode"] == "bfs"
    assert report["run"]["budget"] == DEFAULT_BUDGET
    assert report["stats"]["llm_calls"] == 0
    assert report["stats"]["tokens"] == 0


def test_REQ_EX1_1_at_least_three_class_A_holes(report):
    holes = [h for h in findings(report) if h["class"] in ("A", "B")]
    assert len(holes) >= 3, [h["goal"] for h in holes]


def test_REQ_EX1_1_holes_name_class_A_goals_of_the_domain(report, domain):
    for h in findings(report):
        assert h["goal"] in domain.goals, h["goal"]
        assert domain.goals[h["goal"]].cls == "A", h["goal"]


def test_REQ_EX1_1_the_three_counted_airline_goals_are_found(report):
    # G1 basic economy flights changed, G2 non-refundable refunded, G5 free bags over allowance.
    # v1.7: found as holes or contradictions, each in the list its gold status dictates.
    assert COUNTED_GOALS <= {h["goal"] for h in findings(report)}
    for h in report["holes"]:
        assert h["goal"] not in GOLD_SANCTIONED, h["key"]
    for c in report["contradictions"]:
        assert c["goal"] in GOLD_SANCTIONED, c["key"]


# ---------- REQ-EX1-2 ----------

def test_REQ_EX1_2_every_hole_is_proven(report):
    assert findings(report), "no holes to check"
    for h in findings(report):
        assert h["class"] in ("A", "B")
        assert h["goal_true"] is True, h["id"]
        assert h["replays"] == "5/5", (h["id"], h["replays"])
        for step in h["chain"]:
            assert step["ok"] is True, (h["id"], step["tool"])
            for v in step["verdicts"]:
                assert v["ok"] is True, (h["id"], step["tool"], v["rule_id"])


def test_REQ_EX1_2_holes_carry_a_db_diff(report):
    for h in findings(report):
        assert h["diff"], f"{h['id']} has an empty diff"


def test_REQ_EX1_2_holes_in_the_small_run_are_proven_too(small_report):
    for h in findings(small_report):
        assert h["goal_true"] is True and h["replays"] == "5/5"
        assert all(s["ok"] and all(v["ok"] for v in s["verdicts"]) for s in h["chain"])


# ---------- REQ-EX1-3 ----------

def test_REQ_EX1_3_cancel_rebook_inside_24h_window_is_not_a_hole(report, fresh_db, domain):
    for h in findings(report):
        rid = cancel_rebook_target(h["chain"], fresh_db)
        assert rid is None or not within_24h(rid, fresh_db, domain.now), (
            f"{h['id']} is a cancel+rebook through the 24h window ({rid}) reported as a hole")


def test_REQ_EX1_3_cancel_rebook_through_24h_window_is_an_ambiguity(report, fresh_db, domain):
    found = []
    for a in report["ambiguities"]:
        rid = cancel_rebook_target(a["chain"], fresh_db)
        if rid and within_24h(rid, fresh_db, domain.now):
            found.append(a["id"])
    assert found, "no cancel+rebook chain through the 24h window under ambiguities"


def test_REQ_EX1_3_ambiguities_are_class_C(report):
    for a in report["ambiguities"]:
        assert a["class"] == "C"
    for h in findings(report):
        assert h["class"] != "C"


# ---------- REQ-EX1-4 ----------

def test_REQ_EX1_4_replay_gives_the_report_diff(report, domain):
    replay = importlib.import_module("bylaw.executor").replay
    assert findings(report), "no holes to replay"
    for h in findings(report):
        chain = [{"tool": s["tool"], "args": copy.deepcopy(s["args"])} for s in h["chain"]]
        first = replay(domain, chain)
        second = replay(domain, copy.deepcopy(chain))
        assert len(first["steps"]) == len(chain)
        assert all(step["ok"] for step in first["steps"]), h["id"]
        assert_diff_shape(first["diff"])
        assert first["diff"], f"{h['id']}: replay changed nothing"
        assert canon(first["diff"]) == canon(h["diff"]), f"{h['id']}: replay diff != report diff"
        assert canon(second["diff"]) == canon(first["diff"]), f"{h['id']}: replay is not deterministic"


def test_REQ_EX1_4_report_diff_matches_the_db_change_seen_through_c1(report, domain):
    for h in findings(report):
        before, after, _ = replay_by_contract(domain, h["chain"])
        assert canon(h["diff"]) == canon(expected_diff(before, after)), h["id"]


def test_REQ_EX1_4_hole_chain_reproduces_the_same_diff_on_fresh_envs(report, domain):
    assert findings(report), "no holes to replay"
    for h in findings(report):
        b1, a1, r1 = replay_by_contract(domain, h["chain"])
        b2, a2, r2 = replay_by_contract(domain, h["chain"])
        assert all(r.ok for r in r1), (h["id"], [r.error for r in r1])
        assert canon(b1) == canon(b2), "fresh envs must start from the same DB"
        assert canon(a1) == canon(a2), f"{h['id']}: replay is not deterministic"
        assert canon(a1) != canon(b1), f"{h['id']}: chain changed nothing"
        assert domain.goals[h["goal"]].check(b1, a1, r1) is True, h["id"]


def test_REQ_EX1_4_replay_does_not_leak_into_the_next_fresh_env(report, domain, fresh_db):
    for h in findings(report)[:3]:
        replay_by_contract(domain, h["chain"])
        assert canon(domain.snapshot(domain.fresh_env())) == canon(fresh_db)


# ---------- REQ-PR1-3 (CLI side) ----------

def test_REQ_PR1_3_default_run_stays_within_budget(report):
    assert report["stats"]["tool_calls"] <= DEFAULT_BUDGET


def test_REQ_PR1_3_small_budget_is_honoured(small_report):
    assert small_report["run"]["budget"] == SMALL_BUDGET
    assert 0 < small_report["stats"]["tool_calls"] <= SMALL_BUDGET


# ---------- REQ-PR1-1 (live) ----------

@pytest.mark.live
def test_REQ_PR1_1_llm_audit_finds_at_least_the_no_llm_holes(report, tmp_path):
    muse = audit(tmp_path, "--budget", str(DEFAULT_BUDGET))
    assert_c4_shape(muse)
    assert muse["run"]["mode"] == "muse"
    assert muse["run"]["budget"] == DEFAULT_BUDGET
    assert muse["stats"]["tool_calls"] <= DEFAULT_BUDGET
    assert muse["stats"]["llm_calls"] > 0
    assert {h["key"] for h in findings(report)} <= {h["key"] for h in findings(muse)}
