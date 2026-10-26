import { useEffect, useState } from "react";
import { ArrowRight, Check, Play, ShieldCheck, X } from "lucide-react";
import { GOALS, type Hole } from "../fixtures";
import { Call, Crumbs, Muse, usd } from "../ui";

const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export function HoleView({ hole, ratified }: { hole: Hole; ratified: boolean }) {
  const n = hole.chain.length;
  const [at, setAt] = useState(reduced() ? n : -1);
  const [run, setRun] = useState(0);
  const [open, setOpen] = useState(n - 1);
  const goal = GOALS[hole.goal];

  useEffect(() => {
    if (reduced()) return setAt(n);
    setAt(-1);
    const id = setInterval(() => setAt((a) => (a >= n ? (clearInterval(id), a) : a + 1)), 900);
    return () => clearInterval(id);
  }, [hole.id, run, n]);
  useEffect(() => setOpen(Math.min(Math.max(at, 0), n - 1)), [at, n]);

  return (
    <div className="page">
      <Crumbs items={[["Report", "#/report"], [`${hole.id} · ${hole.title}`]]} />
      <div className="head">
        <div>
          <h1 className="title">{hole.title}</h1>
          <p className="lede">{goal.description} Each step below passes every rule compiled from the policy. Together they reach goal {goal.id}.</p>
        </div>
        <div className="replay-ctl">
          {ratified ? (
            <span className="tag green"><ShieldCheck size={13} aria-hidden="true" />Fixed and enforced</span>
          ) : (
            <a className="btn primary" href={`#/holes/${hole.id}/amendment`}>Review amendment <ArrowRight size={16} aria-hidden="true" /></a>
          )}
        </div>
      </div>

      <div className="detail">
        <section className="panel" aria-labelledby="trace-h">
          <div className="panel-h">
            <h2 id="trace-h">Trace replay</h2>
            <div className="replay-ctl">
              <Muse>Rules compiled by Muse Spark</Muse>
              <button className="btn" style={{ height: 32, padding: "0 12px" }} onClick={() => setRun((r) => r + 1)}>
                <Play size={14} aria-hidden="true" />Replay
              </button>
            </div>
          </div>
          <ol className="trace" aria-live="polite">
            {hole.chain.map((s, i) => {
              const state = i < at ? "" : i === at ? "current" : "pending";
              return (
                <li key={i} className={`step ${state}`} style={{ listStyle: "none" }}>
                  <button className="step-h" aria-expanded={state !== "pending" && open === i} disabled={state === "pending"} onClick={() => setOpen(i)}>
                    <span className="i">{String(i + 1).padStart(2, "0")}</span>
                    <Call step={s} />
                    {state !== "pending" && (
                      <span className={`verdict ${s.ok ? "ok" : "no"}`}>
                        {s.ok ? <Check size={15} aria-hidden="true" /> : <X size={15} aria-hidden="true" />}
                        {s.ok ? "allowed" : "blocked"}
                      </span>
                    )}
                  </button>
                  {state !== "pending" && open !== i && (
                    <div className="chips">
                      {s.verdicts.map((v) => <span key={v.rule_id}><Check size={11} aria-hidden="true" />{v.rule_id}</span>)}
                    </div>
                  )}
                  {state !== "pending" && open === i && (
                    <div className="rules">
                      {s.verdicts.map((v) => (
                        <div className="rule" key={v.rule_id}>
                          <Check size={13} aria-label="rule passed" />
                          <span className="rid">{v.rule_id}</span>
                          <q>{v.policy_ref}</q>
                        </div>
                      ))}
                    </div>
                  )}
                </li>
              );
            })}
            <li className={`outcome ${at >= n ? "" : "pending"}`} style={{ listStyle: "none" }}>
              <span className="eq">=</span>
              <code>{goal.id} {goal.name}</code>
              {at >= n && <span className="verdict"><X size={15} aria-hidden="true" />forbidden</span>}
            </li>
          </ol>
        </section>

        <aside className="side">
          <section className="panel">
            <div className="panel-h"><h2>Proof</h2><span className="tag green">replays {hole.replays}</span></div>
            <div className="panel-b" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div className="replays" aria-label={`${hole.replays} replays reproduced the outcome`}>
                {Array.from({ length: 5 }, (_, i) => <i key={i}><Check size={13} aria-hidden="true" /></i>)}
                <span className="label" style={{ marginLeft: 6 }}>same DB diff on a fresh env</span>
              </div>
              <div className="money">
                <b>{usd(hole.money_delta)}</b>
                <span>{hole.money_delta ? "paid back that the policy says the airline keeps, per booking" : "no money moves; the forbidden change itself is the harm"}</span>
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="panel-h"><h2>Forbidden goal</h2><span className="label">{goal.id}</span></div>
            <div className="panel-b" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div className="paper">
                <div className="src">policy.md</div>
                <p className="quote">{goal.policy_ref}</p>
              </div>
              <pre className="pred" aria-label="Goal predicate">{goal.predicate}</pre>
            </div>
          </section>

          <section className="panel">
            <div className="panel-h"><h2>Database diff</h2><span className="label">before → after</span></div>
            <div className="panel-b">
              {Object.entries(hole.diff).map(([obj, fields]) => (
                <table className="difft" key={obj}>
                  <thead><tr><th colSpan={2}>{obj}</th></tr></thead>
                  <tbody>
                    {Object.entries(fields).map(([k, [b, a]]) => (
                      <tr key={k} className={JSON.stringify(a) !== JSON.stringify(b) ? "chg" : ""}>
                        <td>{k}</td>
                        <td>
                          {JSON.stringify(a) !== JSON.stringify(b) && <><span className="was">{String(b)}</span> → </>}
                          <span className="now">{String(a)}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
