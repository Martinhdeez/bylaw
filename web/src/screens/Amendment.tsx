import { useState } from "react";
import { AlertTriangle, ArrowRight, Bot, Check, FileSearch, Gavel, Loader2, Wrench } from "lucide-react";
import { api, useGet, type ApiError, type Domain, type Hole, type Policy, type Ratified } from "../api";
import { Crumbs, Failure, Loading, Muse, goldLine, holeHref, humanize, int, lineOf, quote, when } from "../ui";

export function AmendmentView({ domain, hkey, effort }: { domain: Domain; hkey: string; effort?: string }) {
  const hole = useGet<Hole>(`/api/holes/${encodeURIComponent(hkey)}?domain=${domain}`);
  const ratified = useGet<Ratified>(api.ratified(domain));
  const policy = useGet<Policy>(api.policy(domain));
  const readonly = !!useGet<{ readonly: boolean }>(api.config()).data?.readonly;
  const [busy, setBusy] = useState(false);
  const [fail, setFail] = useState<ApiError>();
  // Set by this page's own ratify, so the stamp lands only then and not on a later visit.
  const [justNow, setJustNow] = useState(false);
  const crumbs = <Crumbs items={[["Report", `#/${domain}/report`], [hkey, holeHref(domain, hkey)], ["Amendment"]]} />;

  if ((hole.loading || ratified.loading) && !hole.data) return <div className="page">{crumbs}<Loading what="the amendment" shape="detail" /></div>;
  if (!hole.data || !ratified.data) {
    const err = hole.error ?? ratified.error;
    if (!err) return <div className="page">{crumbs}<Loading what="the amendment" shape="detail" /></div>;
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
          <span className="shield"><FileSearch aria-hidden="true" /></span>
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
      setJustNow(true);
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
          <h1 className="title">{done ? <>Hole {h.id} <span className="g">closed</span></> : <>Amendment <span className="v">{a.id}</span> for {h.id}</>}</h1>
          <p className="lede">
            {isB
              ? `This finding is policy vs practice: ${goldLine(goldTasks, "the benchmark's gold reaches it in").slice(0, -1)}, so the policy and the benchmark's practice disagree. Ratifying the rule settles it against practice${bt ? "; the backtest shows the gold tasks that decision blocks" : ""}.`
              : `A sentence for the policy and the rule that enforces it, so that the trace for ${name.toLowerCase()} no longer passes. Past gold tasks were replayed to count the honest customers it would also stop.`}
          </p>
        </div>
        <Muse>{effort ? `Drafted by Muse Spark, ${effort} effort` : "Drafted by Muse Spark"}</Muse>
      </div>

      <div className="amend">
        <div className="stack wide">
          {/* A redline on the policy page: the clause in force, then the inserted sentence, underlined. */}
          <section className="diffdoc" aria-label="Policy diff">
            <div className="src"><span>policy.md{ln > 0 && `:${ln}`}</span><span>amendment {a.id}</span></div>
            {goal && <p className="ctx"><span className="m">§{ln > 0 ? ln : ""}</span><span style={{ whiteSpace: "pre-line" }}>{quote(goal.policy_ref)}</span></p>}
            <p className="plus"><span className="m">+</span><ins>{a.policy_text}</ins></p>
            <span className="note">inserted by amendment {a.id}</span>
          </section>

          <section className="panel">
            <div className="panel-h"><h2>Rule patch</h2><span className="label">{a.rule_patch.length} {a.rule_patch.length === 1 ? "rule" : "rules"} added</span></div>
            <div className="panel-b stack">
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
            <Metric label="gold tasks replayed" v={bt ? int(bt.tasks) : null} />
            <Metric label={isB ? "gold tasks blocked" : "honest customers blocked"} v={bt ? int(newlyBlocked) : null} tone={!bt ? "" : newlyBlocked ? "w" : "g"} note={bt && bt.baseline_blocked > 0 ? `${bt.baseline_blocked} already blocked before` : undefined} />
            <Metric label={isB ? "stops the chain" : "closes the hole"} v={h.closes === undefined ? null : h.closes ? "yes" : "no"} tone={h.closes === undefined ? "" : h.closes ? "g" : "w"} />
            <Metric label="rules added" v={String(a.rule_patch.length)} />
          </div>

          {done ? (
            <section className={justNow ? "enforced fresh" : "enforced"} role="status" data-testid="ratified">
              <span className="stamp" data-testid="stamp">Ratified<small>{when(done.ratified_at)}</small></span>
              <span className="t"><i className="closing" aria-hidden="true" />Enforced by MCP proxy</span>
              <div className="flow" aria-label="Your agent calls tools through the bylaw proxy">
                <span><Bot aria-hidden="true" />your agent</span>
                <ArrowRight size={14} aria-hidden="true" />
                <span className="px"><Gavel aria-hidden="true" />bylaw proxy</span>
                <ArrowRight size={14} aria-hidden="true" />
                <span><Wrench aria-hidden="true" />τ² tools</span>
              </div>
              <p className="label">
                The proxy now refuses calls that fail {done.rule_patch.map((r) => r.id.replace(`${h.key}/`, "")).join(", ")}.
              </p>
              <a className="btn" href={`#/${domain}/report`}>Back to report</a>
            </section>
          ) : (
            <section className="panel ratify-box">
              <h2 className="h2">Ratify this amendment</h2>
              {isB && (
                <p className="tradeoff">
                  <b>Trade-off.</b> {goldLine(goldTasks)} Ratifying forbids it from now on{bt && bt.blocked_tasks.length ? `, and the proxy will refuse gold task${bt.blocked_tasks.length > 1 ? "s" : ""} ${bt.blocked_tasks.join(", ")}` : ""}. Ratify only if the policy should forbid what practice allows.
                </p>
              )}
              {!bt && <p>This amendment was not backtested. Ratify only after reading the rule.</p>}
              {!isB && bt && (
                <p>
                  {newlyBlocked === 0
                    ? `None of the ${bt.tasks} gold tasks is newly blocked. Ratifying adds the rule to the proxy, which refuses matching tool calls from now on.`
                    : `${newlyBlocked} of ${bt.tasks} gold tasks would be newly blocked. Read them before you ratify.`}
                </p>
              )}
              {!isB && bt && newlyBlocked > 0 && <p className="blocked">Blocked tasks: {bt.blocked_tasks.join(", ")}</p>}
              {h.closes === false && <p className="blocked"><b>The trace still passes with this rule.</b> Ratifying will not close the hole.</p>}
              {fail && (
                <p className="blocked" role="alert">
                  <AlertTriangle size={13} aria-hidden="true" /> {fail.status === 409 ? "The API says this hole has no amendment to ratify. Reload the report." : fail.status ? `The API answered ${fail.status}. Try again.` : fail.message}
                </p>
              )}
              <button className="btn ratify" onClick={ratify} disabled={busy || readonly}>
                {busy ? <Loader2 className="spin" aria-hidden="true" /> : <Check aria-hidden="true" />}
                {busy ? "Ratifying…" : readonly ? "Ratify is off on the public demo" : "Ratify"}
              </button>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}

function Metric({ label, v, tone = "", note }: { label: string; v: string | null; tone?: string; note?: string }) {
  return (
    <div className="panel metric">
      <span>{label}</span>
      {v === null ? <b className="na">not backtested</b> : <b className={tone}>{v}</b>}
      {note && <span>{note}</span>}
    </div>
  );
}
