import { useState } from "react";
import { AlertTriangle, ArrowRight, Bot, Check, Gavel, Loader2, ShieldCheck, Wrench } from "lucide-react";
import { api, useGet, type ApiError, type Domain, type Hole, type Policy, type Ratified } from "../api";
import { Crumbs, Failure, Loading, Muse, goldLine, holeHref, humanize, int, lineOf, quote, when } from "../ui";

export function AmendmentView({ domain, hkey }: { domain: Domain; hkey: string }) {
  const hole = useGet<Hole>(`/api/holes/${encodeURIComponent(hkey)}?domain=${domain}`);
  const ratified = useGet<Ratified>(api.ratified(domain));
  const policy = useGet<Policy>(api.policy(domain));
  const [busy, setBusy] = useState(false);
  const [fail, setFail] = useState<ApiError>();
  const crumbs = <Crumbs items={[["Report", `#/${domain}/report`], [hkey, holeHref(domain, hkey)], ["Amendment"]]} />;

  if (hole.loading || ratified.loading) return <div className="page">{crumbs}<Loading what="the amendment" /></div>;
  if (!hole.data || !ratified.data) {
    const err = (hole.error ?? ratified.error)!;
    return <div className="page">{crumbs}<Failure error={err} onRetry={() => { hole.reload(); ratified.reload(); }} /></div>;
  }

  const h = hole.data;
  const a = h.amendment;
  const done = ratified.data.amendments.find((x) => x.hole_key === h.key);
  const goal = ratified.data.ruleset.forbidden_goals.find((g) => g.id === h.goal);
  const { name } = humanize(h.title, h.key);

  if (!a)
    return (
      <div className="page">
        {crumbs}
        <section className="panel empty-state">
          <h1 className="h2">No amendment was drafted for {h.key}</h1>
          <p>Run the audit again with “Draft amendments” on. Muse Spark writes one policy sentence and a rule patch for each proven hole.</p>
          <a className="btn" href="#/">Run an audit</a>
        </section>
      </div>
    );

  const bt = h.backtest;
  const newlyBlocked = bt ? Math.max(0, bt.blocked - bt.baseline_blocked) : 0;
  const isB = h.class === "B";
  const goldTasks = h.gold?.tasks ?? [];
  const ln = goal ? lineOf(policy.data?.lines, goal.policy_ref) : 0;

  const ratify = async () => {
    setBusy(true);
    setFail(undefined);
    try {
      await api.ratify(domain, h.key);
      ratified.reload();
    } catch (e) {
      setFail(e as ApiError);
    }
    setBusy(false);
  };

  return (
    <div className="page">
      {crumbs}
      <div className="head">
        <div>
          <h1 className="title">{done ? <>Hole {h.id} <span className="g">closed</span></> : <>Amendment {a.id} for {h.id}</>}</h1>
          <p className="lede">
            {isB
              ? `This finding is a contradiction: the policy text forbids ${name.toLowerCase()}, but ${goldLine(goldTasks, "the benchmark's gold does it in").slice(0, -1)}. Ratifying the rule makes the written policy win over practice; the backtest shows the gold tasks that decision blocks.`
              : `A sentence for the policy and the rule that enforces it, so that the trace for ${name.toLowerCase()} no longer passes. Past gold tasks were replayed to count the honest customers it would also stop.`}
          </p>
        </div>
        <Muse>Drafted by Muse Spark · max reasoning</Muse>
      </div>

      <div className="amend">
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <section className="diffdoc" aria-label="Policy diff">
            <div className="src"><span>policy.md{ln > 0 && `:${ln}`}</span><span>amendment {a.id}</span></div>
            {goal && <p className="ctx"><span className="m"> </span><span style={{ whiteSpace: "pre-line" }}>{quote(goal.policy_ref)}</span></p>}
            <p className="plus"><span className="m">+</span><span>{a.policy_text}</span></p>
          </section>

          <section className="panel">
            <div className="panel-h"><h2>Rule patch</h2><span className="label">{a.rule_patch.length} {a.rule_patch.length === 1 ? "rule" : "rules"} added</span></div>
            <div className="panel-b" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {a.rule_patch.map((r) => (
                <pre className="code" key={r.id} translate="no">
                  <span className="k">+ </span>{`{ "id": "${r.id}",\n    "tool": "${r.tool}",\n    "allow_if": `}<span className="k">{r.allow_if}</span>{`,\n    "policy_ref": "${r.policy_ref}" }`}
                </pre>
              ))}
              {a.rationale && <p className="rationale"><b>Why:</b> {a.rationale}</p>}
            </div>
          </section>
        </div>

        <aside className="side">
          <div className="metrics">
            <div className="metric"><span>gold tasks replayed</span><b>{bt ? int(bt.tasks) : "—"}</b></div>
            <div className="metric"><span>{isB ? "gold tasks blocked" : "honest customers blocked"}</span><b className={newlyBlocked ? "w" : "g"}>{bt ? int(newlyBlocked) : "—"}</b>{bt && bt.baseline_blocked > 0 && <span>{bt.baseline_blocked} already blocked before</span>}</div>
            <div className="metric"><span>{isB ? "stops the chain" : "closes the hole"}</span><b className={h.closes ? "g" : "w"}>{h.closes === undefined ? "—" : h.closes ? "yes" : "no"}</b></div>
            <div className="metric"><span>rules added</span><b>{a.rule_patch.length}</b></div>
          </div>

          {done ? (
            <section className="enforced" role="status" data-testid="ratified">
              <span className="t"><ShieldCheck size={24} aria-hidden="true" />Enforced by MCP proxy</span>
              <div className="flow" aria-label="Your agent calls tools through the Bylaw proxy">
                <span><Bot size={14} aria-hidden="true" />your agent</span>
                <ArrowRight size={14} aria-hidden="true" />
                <span className="px"><Gavel size={14} aria-hidden="true" />bylaw proxy</span>
                <ArrowRight size={14} aria-hidden="true" />
                <span><Wrench size={14} aria-hidden="true" />τ² tools</span>
              </div>
              <p style={{ color: "var(--muted)", fontSize: 14 }}>
                Ratified {when(done.ratified_at)}. The proxy now refuses calls that fail {done.rule_patch.map((r) => r.id).join(", ")}.
              </p>
              <a className="btn" href={`#/${domain}/report`}>Back to report</a>
            </section>
          ) : (
            <section className="panel ratify-box">
              <h2 className="h2">Ratify this amendment</h2>
              {isB && (
                <p className="tradeoff">
                  <b>Trade-off.</b> {goldLine(goldTasks)} Ratifying forbids it from now on{bt && bt.blocked_tasks.length ? `, and the proxy will refuse gold task${bt.blocked_tasks.length > 1 ? "s" : ""} ${bt.blocked_tasks.join(", ")}` : ""}. Ratify only if the written policy should win.
                </p>
              )}
              {!isB && <p>
                {!bt
                  ? "This amendment was not backtested. Ratify only after reading the rule."
                  : newlyBlocked === 0
                    ? `None of the ${bt.tasks} gold tasks is newly blocked. Ratifying adds the rule to the proxy, which refuses matching tool calls from now on.`
                    : `${newlyBlocked} of ${bt.tasks} gold tasks would be newly blocked. Read them before you ratify.`}
              </p>}
              {!isB && bt && newlyBlocked > 0 && <p className="blocked">Blocked tasks: {bt.blocked_tasks.join(", ")}</p>}
              {h.closes === false && <p className="blocked"><b>The trace still passes with this rule.</b> Ratifying will not close the hole.</p>}
              {fail && (
                <p className="blocked" role="alert">
                  <AlertTriangle size={13} aria-hidden="true" /> {fail.status === 409 ? "The API says this hole has no amendment to ratify. Reload the report." : fail.status ? `The API answered ${fail.status}. Try again.` : fail.message}
                </p>
              )}
              <button className="btn ratify" onClick={ratify} disabled={busy}>
                {busy ? <Loader2 size={18} className="spin" aria-hidden="true" /> : <Check size={18} aria-hidden="true" />}
                {busy ? "Ratifying…" : "Ratify"}
              </button>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
