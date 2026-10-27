import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { ArrowRight, Check, ChevronLeft, ChevronRight, Pause, Play, ShieldCheck, X } from "lucide-react";
import { api, useGet, type Domain, type ForbiddenGoal, type Hole, type Policy, type Ratified } from "../api";
import { Call, Crumbs, Failure, Loading, Muse, Ticker, changedFields, goldLine, holeHref, humanize, lineOf, quote, reduced, usd } from "../ui";

export function HoleView({ domain, hkey, muse }: { domain: Domain; hkey: string; muse: boolean }) {
  const hole = useGet<Hole>(`/api/holes/${encodeURIComponent(hkey)}?domain=${domain}`);
  const ratified = useGet<Ratified>(api.ratified(domain));
  const policy = useGet<Policy>(api.policy(domain));
  const crumbs = <Crumbs items={[["Report", `#/${domain}/report`], [hkey]]} />;

  if (hole.loading) return <div className="page">{crumbs}<Loading what={`hole ${hkey}`} shape="detail" /></div>;
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

// The trace is shown as an evidence exhibit: a rail with one node per call, a cursor on the current one,
// and the forbidden outcome punched like the logo's hole once the last call lands.
function Trace({ domain, h, goal, isFixed, lines, crumbs, muse }: {
  domain: Domain; h: Hole; goal?: ForbiddenGoal; isFixed: boolean; lines?: string[]; crumbs: ReactNode; muse: boolean;
}) {
  const n = h.chain.length;
  const [at, setAt] = useState(reduced() ? n : -1);
  const [playing, setPlaying] = useState(!reduced());
  const [open, setOpen] = useState(n - 1);
  const list = useRef<HTMLOListElement>(null);
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
  const replay = () => {
    if (reduced()) return setAt(n);
    setAt(-1);
    setPlaying(true);
  };
  // ←/→ step the trace, unless the keys belong to a field or the ⌘K dialog.
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || (e.target as Element).closest?.("input, textarea, select, dialog")) return;
      if (e.key === "ArrowRight") step(1);
      if (e.key === "ArrowLeft") step(-1);
    };
    addEventListener("keydown", on);
    return () => removeEventListener("keydown", on);
  }, [n]);
  // Cursor on the current node, fill from the first node to it: one layout read per step or resize.
  useLayoutEffect(() => {
    const ol = list.current!;
    const measure = () => {
      const nodes = ol.querySelectorAll(".node");
      const track = ol.querySelector(".track");
      const node = nodes[Math.min(Math.max(at, 0), n)];
      if (!node || !track) return;
      const o = ol.getBoundingClientRect(), t = track.getBoundingClientRect(), r = node.getBoundingClientRect();
      const mid = r.top + r.height / 2;
      ol.style.setProperty("--y", `${mid - o.top}px`);
      ol.style.setProperty("--p", String(at < 0 ? 0 : Math.max(0, Math.min(1, (mid - t.top) / t.height))));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(ol);
    return () => ro.disconnect();
  }, [at, open, n]);

  return (
    <div className="page">
      {crumbs}
      <div className="head">
        <div>
          <h1 className="title">{name} <span className="mono-t">{target}</span></h1>
          <p className="lede">
            {h.class === "B"
              ? `Policy vs practice, not counted as a hole: each step passes every rule and together they reach goal ${h.goal}, which the policy text forbids. ${goldLine(h.gold?.tasks ?? [])}`
              : h.class === "C"
              ? `Class C ambiguity, not counted: each step passes every rule and together they reach goal ${h.goal}, but cancel and rebook inside a permitted cancel ground is the method the policy allows.`
              : `Each step below passes every rule of the policy. Together they reach goal ${h.goal}, an outcome the policy forbids.`}
          </p>
        </div>
        <div className="ctl">
          {h.class === "B" && <span className="tag amber">Class B, contradiction</span>}
          {isFixed ? (
            <span className="tag green"><ShieldCheck aria-hidden="true" />Fixed and enforced</span>
          ) : h.amendment ? (
            <a className="btn primary" href={holeHref(domain, h.key, "/amendment")}>Review amendment<span className="ic"><ArrowRight aria-hidden="true" /></span></a>
          ) : (
            <span className="tag">{h.class === "C" ? "Class C, listed for review" : "No amendment drafted"}</span>
          )}
        </div>
      </div>

      <div className="detail">
        <section className="panel" aria-labelledby="trace-h">
          <div className="panel-h">
            <h2 id="trace-h">
              <span className="exhibit">Exhibit {h.id}</span>Trace replay
              <span className="segs" role="img" aria-label={`step ${Math.max(0, Math.min(at, n))} of ${n}`}>
                {Array.from({ length: n + 1 }, (_, i) => <i key={i} className={i < at ? "on" : i === at ? "cur" : ""} />)}
              </span>
            </h2>
            <div className="ctl">
              {muse ? <Muse>Rules compiled by Muse Spark</Muse> : <span className="tag">Hand RuleSet</span>}
              <span className="keys" aria-hidden="true"><kbd>←</kbd><kbd>→</kbd></span>
              <button className="btn sm icon" onClick={() => step(-1)} disabled={at <= 0} aria-label="Previous step" aria-keyshortcuts="ArrowLeft" data-tip="Previous step" data-tip-pos="bottom"><ChevronLeft aria-hidden="true" /></button>
              <button className="btn sm" onClick={() => step(1)} disabled={at >= n} aria-keyshortcuts="ArrowRight">Next step<ChevronRight aria-hidden="true" /></button>
              {playing
                ? <button className="btn sm" onClick={() => setPlaying(false)}><Pause aria-hidden="true" />Pause</button>
                : <button className="btn sm" onClick={replay}><Play aria-hidden="true" />Replay</button>}
            </div>
          </div>
          <ol className={at < 0 ? "trace idle" : "trace"} ref={list} aria-live="polite">
            <li className="track" aria-hidden="true"><span className="fill" /></li>
            <li className="cursor" aria-hidden="true" />
            {h.chain.map((s, i) => {
              const state = i < at ? "" : i === at ? "current" : "pending";
              return (
                <li key={i} className={`step ${state || "past"}`} data-testid="step" data-state={state || "past"}>
                  <button className="step-h" aria-expanded={state !== "pending" && open === i} disabled={state === "pending"} onClick={() => setOpen(i)}>
                    <span className="node">{state === "" ? <Check aria-hidden="true" /> : String(i + 1).padStart(2, "0")}</span>
                    <Call step={s} />
                    {state !== "pending" && (
                      <span className={`verdict ${s.ok ? "ok" : "no"}`}>
                        {s.ok ? <Check aria-hidden="true" /> : <X aria-hidden="true" />}
                        {s.ok ? "allowed" : "blocked"}
                      </span>
                    )}
                  </button>
                  {state !== "pending" && open !== i && (
                    <div className="chips">
                      {s.verdicts.map((v, j) => <span key={v.rule_id} className={v.ok ? "" : "no"} style={{ "--i": j } as CSSProperties}>{v.ok ? <Check aria-hidden="true" /> : <X aria-hidden="true" />}{v.rule_id}</span>)}
                    </div>
                  )}
                  {state !== "pending" && open === i && (
                    <div className="rules">
                      {s.verdicts.map((v, j) => {
                        const ln = lineOf(lines, v.policy_ref);
                        return (
                          <div className="rule" key={v.rule_id} style={{ "--i": j } as CSSProperties}>
                            {v.ok ? <Check aria-label="rule passed" /> : <X aria-label="rule failed" className="no" />}
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
            <li className={`outcome ${h.class === "B" ? "b" : ""} ${at >= n ? "" : "pending"}`} data-testid="outcome">
              <span className="node" aria-hidden="true" />
              <code translate="no">{h.goal} {goal?.name ?? name}</code>
              {at >= n && <span className="verdict"><X aria-hidden="true" />{h.class === "B" ? "forbidden by the text, done by gold" : "forbidden"}</span>}
            </li>
          </ol>
        </section>

        <aside className="side">
          <section className="panel">
            <div className="panel-h"><h2>Proof</h2><span className="tag green">replays {h.replays}</span></div>
            <div className="panel-b stack">
              <div className="replays" aria-label={`${h.replays} replays reproduced the outcome`}>
                {Array.from({ length: total || 0 }, (_, i) => <i key={i} className={i < ok ? "" : "miss"} style={{ "--i": i } as CSSProperties}>{i < ok ? <Check aria-hidden="true" /> : <X aria-hidden="true" />}</i>)}
                <span className="label">same DB diff on a fresh env</span>
              </div>
              <div className={`money ${h.class === "A" ? "" : "neutral"}`}>
                <Ticker className="b-num" value={h.money_delta} format={usd} ms={1100} />
                <span>{h.money_delta > 0 ? "net paid out to the customer by this chain" : h.money_delta < 0 ? "net charged to the customer; the forbidden change itself is the harm" : "no money moves; the forbidden change itself is the harm"}</span>
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="panel-h"><h2>Forbidden goal</h2><span className="label">{h.goal}</span></div>
            <div className="panel-b stack">
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
                        <tr key={k}>
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
