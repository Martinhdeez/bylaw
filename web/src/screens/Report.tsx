import { ArrowRight, Check, ShieldCheck } from "lucide-react";
import { CLASS_C_NOTE, GOALS, type Report } from "../fixtures";
import { Crumbs, Muse, int, usd } from "../ui";

export function ReportView({ report, ratified }: { report: Report; ratified: string[] }) {
  const { run, holes, ambiguities, stats } = report;
  const leaked = holes.reduce((a, h) => a + h.money_delta, 0);
  const when = new Date(run.started).toUTCString().slice(5, 22);

  return (
    <div className="page">
      <Crumbs items={[["Audit", "#/"], [`${run.domain} report`]]} />
      <div className="head">
        <div>
          <h1 className="title">
            {holes.length ? <><span className="r">{holes.length} proven holes</span> in the {run.domain} policy</> : <>No proven holes in the {run.domain} policy</>}
          </h1>
          <p className="lede">
            {holes.length
              ? "Every hole below is a chain of tool calls the policy allows, one by one, that ends in an outcome the policy forbids. Each was replayed five times on a fresh database."
              : "A hole is a chain of tool calls the policy allows, one by one, that ends in an outcome the policy forbids. This run proved none."}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Muse>Rules compiled by Muse Spark</Muse>
          <Muse>Chains proposed by Muse Spark</Muse>
        </div>
      </div>

      <div className="summary">
        <div>
          <span className="label">Run</span>
          <span className="mono" style={{ fontSize: 13 }}>{when} UTC · commit {run.commit}</span>
          <span className="s">mode {run.mode} · model {run.model}</span>
        </div>
        <div><span className="label">Class A holes</span><span className={`v ${holes.length ? "r" : ""}`}>{holes.length}</span><span className="s">counted</span></div>
        <div><span className="label">Money leaked</span><span className="v">{usd(leaked)}</span><span className="s">one booking per hole, {holes.length} holes</span></div>
        <div><span className="label">Search</span><span className="v num">{int(stats.tool_calls)}</span><span className="s">tool calls of {int(run.budget)} · {Math.round(stats.seconds)} s</span></div>
      </div>

      {holes.length ? (
        <div className="holes">
          {holes.map((h) => {
            const fixed = ratified.includes(h.id);
            return (
              <a key={h.id} className="hcard" href={`#/holes/${h.id}`} aria-label={`${h.id}: ${h.title}${fixed ? ", fixed" : ""}`}>
                <div className="top">
                  <span className="id">{h.id} · class {h.class} · {h.chain.length} steps</span>
                  {fixed ? <span className="tag green fixed"><Check size={13} aria-hidden="true" />Fixed</span> : <i className="hole-mark" aria-hidden="true" />}
                </div>
                <h3>{h.title}</h3>
                <span className="goal">{h.goal} {GOALS[h.goal].name}</span>
                <div className="facts">
                  <div><span>money</span><b className="money">{usd(h.money_delta)}</b></div>
                  <div><span>replays</span><b className="rep">{h.replays}</b></div>
                  <div><span>goal</span><b>{h.goal_true ? "true" : "false"}</b></div>
                </div>
                <span className="cta">Replay trace <ArrowRight size={14} aria-hidden="true" /></span>
              </a>
            );
          })}
        </div>
      ) : (
        <section className="panel empty-state">
          <span className="shield"><ShieldCheck size={32} aria-hidden="true" /></span>
          <h2 className="h2">The search spent its budget without reaching a forbidden outcome</h2>
          <p>{int(stats.chains_tried)} chains, depth up to 4, over every write tool. This is not a proof that no hole exists. Raise the budget or add forbidden goals, then run the audit again.</p>
          <a className="btn" href="#/">Run another audit</a>
        </section>
      )}

      {ambiguities.length > 0 && (
        <section className="panel" aria-labelledby="amb-h">
          <div className="panel-h">
            <h2 id="amb-h">Ambiguities · class C, not counted</h2>
            <span className="label">{ambiguities.length} listed for review</span>
          </div>
          <p style={{ padding: "12px 18px 4px", color: "var(--muted)", fontSize: 14 }}>{CLASS_C_NOTE}</p>
          <ul className="amb">
            {ambiguities.map((a) => (
              <li key={a.id}>
                <span className="id">{a.id}</span>
                <span>
                  <span className="t">{a.title}</span>
                  <br />
                  <span className="c">{a.chain.map((s) => s.tool).join(" → ")}</span>
                </span>
                <span className="tag">{a.goal} · {a.replays}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
