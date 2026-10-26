import { ArrowRight, Bot, Check, Gavel, ShieldCheck, Wrench } from "lucide-react";
import { AMENDMENTS, type Hole } from "../fixtures";
import { Crumbs, Muse, int } from "../ui";

export function AmendmentView({ hole, ratified, onRatify }: { hole: Hole; ratified: boolean; onRatify: () => void }) {
  const a = AMENDMENTS[hole.id];
  const clean = a.backtest.blocked === 0;

  return (
    <div className="page">
      <Crumbs items={[["Report", "#/report"], [hole.id, `#/holes/${hole.id}`], ["Amendment"]]} />
      <div className="head">
        <div>
          <h1 className="title">{ratified ? <>Hole {hole.id} <span className="g">closed</span></> : <>Amendment for {hole.id}</>}</h1>
          <p className="lede">A change to the policy text and the rule that enforces it. With the rule in place the {hole.id} trace no longer passes. Past cases were replayed to count the honest customers it would also stop.</p>
        </div>
        <Muse>Drafted by Muse Spark · max reasoning</Muse>
      </div>

      <div className="amend">
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <section className="diffdoc" aria-label="Policy diff">
            <div className="src"><span>{a.section}</span><span>amendment 1</span></div>
            {a.context.map((l) => <p key={l} className="ctx"><span className="m"> </span><span>{l}</span></p>)}
            {a.removed.map((l) => <p key={l} className="minus"><span className="m">−</span><span>{l}</span></p>)}
            {a.added.map((l) => <p key={l} className="plus"><span className="m">+</span><span>{l}</span></p>)}
          </section>

          <section className="panel">
            <div className="panel-h"><h2>Rule patch</h2><span className="label">bylaw/rulesets/airline.json</span></div>
            <div className="panel-b">
              <pre className="code">
                <span className="k">+ </span>{`{ "id": "${a.rule.id}",\n    "tool": "${a.rule.tool}",\n    "allow_if": `}<span className="k">{a.rule.allow_if}</span>{`,\n    "policy_ref": "${a.rule.policy_ref}" }`}
              </pre>
            </div>
          </section>
        </div>

        <aside className="side">
          <div className="metrics">
            <div className="metric"><span>past cases replayed</span><b>{a.backtest.cases}</b></div>
            <div className="metric"><span>honest customers blocked</span><b className={clean ? "g" : "w"}>{a.backtest.blocked}</b></div>
            <div className="metric"><span>hole replays still passing</span><b className="g">{a.backtest.hole_closed}</b></div>
            <div className="metric"><span>Muse Spark tokens</span><b>{int(a.backtest.tokens)}</b></div>
          </div>

          {ratified ? (
            <section className="enforced" role="status">
              <span className="t"><ShieldCheck size={24} aria-hidden="true" />Enforced by MCP proxy</span>
              <div className="flow" aria-label="Your agent calls tools through the Bylaw proxy">
                <span><Bot size={14} aria-hidden="true" />your agent</span>
                <ArrowRight size={14} aria-hidden="true" />
                <span className="px"><Gavel size={14} aria-hidden="true" />bylaw proxy</span>
                <ArrowRight size={14} aria-hidden="true" />
                <span><Wrench size={14} aria-hidden="true" />τ² tools</span>
              </div>
              <div className="blocked"><b>✗ blocked</b> {a.proxy_blocked_example}<br />{a.rule.id}: “{a.rule.policy_ref}”</div>
              <a className="btn" href="#/report">Back to report</a>
            </section>
          ) : (
            <section className="panel ratify-box">
              <h2 className="h2">Ratify this amendment</h2>
              <p>
                {clean
                  ? `None of the ${a.backtest.cases} past cases is blocked. Ratifying adds ${a.rule.id} to the proxy, which refuses matching tool calls from now on.`
                  : `${a.backtest.blocked} of ${a.backtest.cases} past cases would be blocked. Read it before you ratify.`}
              </p>
              {a.backtest.blocked_cases.map((c) => <p key={c} className="blocked" style={{ fontSize: 13 }}>{c}</p>)}
              <button className="btn ratify" onClick={onRatify}><Check size={18} aria-hidden="true" />Ratify</button>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
