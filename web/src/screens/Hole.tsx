import { useEffect, useState, type ReactNode } from "react";
import { ArrowRight, Check, ChevronLeft, ChevronRight, Play, ShieldCheck, X } from "lucide-react";
import { api, useGet, type Domain, type Hole, type Policy, type Ratified } from "../api";
import { Call, Crumbs, Failure, Loading, Muse, changedFields, holeHref, humanize, lineOf, quote, usd } from "../ui";

const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export function HoleView({ domain, hkey, muse }: { domain: Domain; hkey: string; muse: boolean }) {
  const hole = useGet<Hole>(`/api/holes/${encodeURIComponent(hkey)}?domain=${domain}`);
  const ratified = useGet<Ratified>(api.ratified(domain));
  const policy = useGet<Policy>(api.policy(domain));
  const crumbs = <Crumbs items={[["Report", `#/${domain}/report`], [hkey]]} />;

  if (hole.loading) return <div className="page">{crumbs}<Loading what={`hole ${hkey}`} /></div>;
  if (!hole.data)
    return (
      <div className="page">
        {crumbs}
        {hole.error?.status === 404 ? (
          <section className="panel empty-state">
            <h1 className="h2">Hole {hkey} is not in the latest {domain} report</h1>
            <p>A newer audit may have replaced the report it came from.</p>
            <a className="btn" href={`#/${domain}/report`}>Open the latest report</a>
          </section>
        ) : <Failure error={hole.error!} onRetry={hole.reload} />}
      </div>
    );

  const h = hole.data;
  const goal = ratified.data?.ruleset.forbidden_goals.find((g) => g.id === h.goal);
  const isFixed = !!ratified.data?.amendments.some((a) => a.hole_key === h.key);
  return <Trace domain={domain} h={h} goal={goal} isFixed={isFixed} lines={policy.data?.lines} crumbs={crumbs} muse={muse} />;
}

function Trace({ domain, h, goal, isFixed, lines, crumbs, muse }: {
  domain: Domain; h: Hole; goal?: { id: string; name: string; policy_ref: string; description: string }; isFixed: boolean; lines?: string[]; crumbs: ReactNode; muse: boolean;
}) {
  const n = h.chain.length;
  const [at, setAt] = useState(reduced() ? n : -1);
  const [playing, setPlaying] = useState(!reduced());
  const [open, setOpen] = useState(n - 1);
  const { name, target } = humanize(h.title, h.key);
  const [ok, total] = h.replays.split("/").map(Number);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => setAt((a) => (a >= n ? (setPlaying(false), a) : a + 1)), 900);
    return () => clearInterval(id);
  }, [playing, n]);
  useEffect(() => setOpen(Math.min(Math.max(at, 0), n - 1)), [at, n]);
  const step = (d: number) => {
    setPlaying(false);
    setAt((a) => Math.min(n, Math.max(0, a + d)));
  };

  return (
    <div className="page">
      {crumbs}
      <div className="head">
        <div>
          <h1 className="title">{name} <span className="mono-t">{target}</span></h1>
          <p className="lede">
            {h.class === "C"
              ? `Class C ambiguity, not counted: each step passes every rule and together they reach goal ${h.goal}, but cancel and rebook inside a permitted cancel ground is the method the policy allows.`
              : `Each step below passes every rule of the policy. Together they reach goal ${h.goal}, an outcome the policy forbids.`}
          </p>
        </div>
        <div className="replay-ctl">
          {isFixed ? (
            <span className="tag green"><ShieldCheck size={13} aria-hidden="true" />Fixed and enforced</span>
          ) : h.amendment ? (
            <a className="btn primary" href={holeHref(domain, h.key, "/amendment")}>Review amendment <ArrowRight size={16} aria-hidden="true" /></a>
          ) : (
            <span className="tag">{h.class === "C" ? "Class C · listed for review" : "No amendment drafted"}</span>
          )}
        </div>
      </div>

      <div className="detail">
        <section className="panel" aria-labelledby="trace-h">
          <div className="panel-h">
            <h2 id="trace-h">Trace replay <span className="label">step {Math.max(0, Math.min(at, n))} of {n}</span></h2>
            <div className="replay-ctl">
              {muse ? <Muse>Rules compiled by Muse Spark</Muse> : <span className="tag">Hand RuleSet</span>}
              <button className="btn sm" onClick={() => step(-1)} disabled={at <= 0} aria-label="Previous step"><ChevronLeft size={15} aria-hidden="true" /></button>
              <button className="btn sm" onClick={() => step(1)} disabled={at >= n}>Next step<ChevronRight size={15} aria-hidden="true" /></button>
              <button className="btn sm" onClick={() => { setAt(-1); setPlaying(!reduced()); if (reduced()) setAt(n); }}>
                <Play size={14} aria-hidden="true" />Replay
              </button>
            </div>
          </div>
          <ol className="trace" aria-live="polite">
            {h.chain.map((s, i) => {
              const state = i < at ? "" : i === at ? "current" : "pending";
              return (
                <li key={i} className={`step ${state}`} data-testid="step" data-state={state || "past"}>
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
                      {s.verdicts.map((v) => <span key={v.rule_id} className={v.ok ? "" : "no"}>{v.ok ? <Check size={11} aria-hidden="true" /> : <X size={11} aria-hidden="true" />}{v.rule_id}</span>)}
                    </div>
                  )}
                  {state !== "pending" && open === i && (
                    <div className="rules">
                      {s.verdicts.map((v) => {
                        const ln = lineOf(lines, v.policy_ref);
                        return (
                          <div className="rule" key={v.rule_id}>
                            {v.ok ? <Check size={13} aria-label="rule passed" /> : <X size={13} aria-label="rule failed" className="no" />}
                            <span className="rid" translate="no">{v.rule_id}{ln > 0 && <small>policy.md:{ln}</small>}</span>
                            <q>{v.policy_ref}</q>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </li>
              );
            })}
            <li className={`outcome ${at >= n ? "" : "pending"}`} data-testid="outcome">
              <span className="eq">=</span>
              <code translate="no">{h.goal} {goal?.name ?? name}</code>
              {at >= n && <span className="verdict"><X size={15} aria-hidden="true" />forbidden</span>}
            </li>
          </ol>
        </section>

        <aside className="side">
          <section className="panel">
            <div className="panel-h"><h2>Proof</h2><span className="tag green">replays {h.replays}</span></div>
            <div className="panel-b" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div className="replays" aria-label={`${h.replays} replays reproduced the outcome`}>
                {Array.from({ length: total || 0 }, (_, i) => <i key={i} className={i < ok ? "" : "miss"}>{i < ok ? <Check size={13} aria-hidden="true" /> : <X size={13} aria-hidden="true" />}</i>)}
                <span className="label" style={{ marginLeft: 6 }}>same DB diff on a fresh env</span>
              </div>
              <div className="money">
                <b>{usd(h.money_delta)}</b>
                <span>{h.money_delta > 0 ? "net paid out to the customer by this chain" : h.money_delta < 0 ? "net charged to the customer; the forbidden change itself is the harm" : "no money moves; the forbidden change itself is the harm"}</span>
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="panel-h"><h2>Forbidden goal</h2><span className="label">{h.goal}</span></div>
            <div className="panel-b" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {goal ? (
                <>
                  <div className="paper">
                    <div className="src">policy.md{lineOf(lines, goal.policy_ref) > 0 && `:${lineOf(lines, goal.policy_ref)}`}</div>
                    <p className="quote">{quote(goal.policy_ref)}</p>
                  </div>
                  <code className="pred" translate="no">{goal.name}</code>
                </>
              ) : <p className="label">Loading goal…</p>}
            </div>
          </section>

          <section className="panel">
            <div className="panel-h"><h2>Database diff</h2><span className="label">before → after</span></div>
            <div className="panel-b">
              {Object.entries(h.diff).flatMap(([coll, recs]) =>
                Object.entries(recs).map(([rid, c]) => (
                  <table className="difft" key={coll + rid}>
                    <thead><tr><th colSpan={2}>{coll}.{rid}{!c.before ? " (created)" : !c.after ? " (deleted)" : ""}</th></tr></thead>
                    <tbody>
                      {changedFields(c).map(([k, b, a]) => (
                        <tr key={k} className="chg">
                          <td>{k}</td>
                          <td><span className="was">{b}</span> → <span className="now">{a}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )),
              )}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
