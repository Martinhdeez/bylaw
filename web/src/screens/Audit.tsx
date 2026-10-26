import { useEffect, useRef, useState } from "react";
import { AlertTriangle, ArrowRight, Check, Loader2, Play, RotateCcw } from "lucide-react";
import { AIRLINE, PHASES, RETAIL, type Report } from "../fixtures";
import { Muse, int } from "../ui";

const DOMAINS = {
  airline: {
    label: "τ² Airline",
    desc: "Flight bookings, cabin changes, bags, cancellations and refunds. 50 tasks, 2,000 reservations.",
    tools: ["book_reservation", "update_reservation_flights", "update_reservation_baggages", "cancel_reservation", "send_certificate"],
    report: AIRLINE,
  },
  retail: {
    label: "τ² Retail",
    desc: "Orders, exchanges, returns and address changes for an online store. 114 tasks, 1,000 orders.",
    tools: ["cancel_pending_order", "exchange_delivered_order_items", "return_delivered_order_items", "modify_pending_order_items"],
    report: RETAIL,
  },
} as const;
type DomainKey = keyof typeof DOMAINS;

// Ticks of 100 ms each; the real run takes minutes, the prototype compresses it.
const LENGTH = [22, 34, 26, 16];
const LOG: [number, string, string][] = [
  [2, "mu", "muse.compile  policy.md  effort=high"],
  [12, "", "rules  23 tool rules · 7 forbidden goals"],
  [20, "ok", "validate  RuleSet ok  match 0.91 vs hand"],
  [25, "mu", "muse.propose  G1 basic_economy_flights_changed"],
  [32, "mu", "muse.propose  G2 non_refundable_fare_refunded"],
  [40, "mu", "muse.propose  G5 free_bags_exceed_allowance"],
  [48, "", "bfs  depth ≤ 4 · write tools only · budget 2,000"],
  [60, "", "exec  T1QOBS  update_reservation_flights ×3"],
  [64, "bad", "hit  G1  H1 basic economy flights changed"],
  [70, "bad", "hit  G2  H2 non-refundable fare refunded"],
  [76, "bad", "hit  G5  H3 free bags kept after downgrade"],
  [80, "", "class C  H4 H5 H6  cancel+rebook ambiguities"],
  [86, "ok", "replay  H1 5/5 · H2 5/5 · H3 5/5"],
  [96, "ok", "report  3 class A · 3 class C"],
];

const RETAIL_LOG: [number, string, string][] = [
  [2, "mu", "muse.compile  policy.md  effort=high"],
  [12, "", "rules  19 tool rules · 5 forbidden goals"],
  [20, "ok", "validate  RuleSet ok"],
  [26, "mu", "muse.propose  R1 refund_exceeds_paid"],
  [34, "mu", "muse.propose  R2 exchange_after_return"],
  [48, "", "bfs  depth ≤ 4 · write tools only · budget 2,000"],
  [70, "", "exec  2,000 chains · no forbidden goal reached"],
  [96, "ok", "report  0 class A · 0 class C · budget spent"],
];

export function Audit({ onDone }: { onDone: (r: Report) => void }) {
  const [domain, setDomain] = useState<DomainKey>("airline");
  const [tick, setTick] = useState(-1);
  const [failed, setFailed] = useState(false);
  const timer = useRef<number>();
  const total = LENGTH.reduce((a, b) => a + b, 0);
  const report = DOMAINS[domain].report;
  const fail = location.hash.includes("fail");

  useEffect(() => () => clearInterval(timer.current), []);
  useEffect(() => {
    if (tick === total) onDone(report);
    if (fail && tick === 12) {
      clearInterval(timer.current);
      setFailed(true);
    }
  }, [tick]); // eslint-disable-line react-hooks/exhaustive-deps

  const run = () => {
    setFailed(false);
    setTick(0);
    clearInterval(timer.current);
    timer.current = window.setInterval(() => setTick((t) => (t >= total ? (clearInterval(timer.current), t) : t + 1)), 100);
  };

  const running = tick >= 0 && tick < total && !failed;
  const done = tick === total;
  let start = 0;
  const phases = PHASES.map((p, i) => {
    const s = start;
    start += LENGTH[i];
    const progress = tick < 0 ? 0 : Math.min(1, Math.max(0, (tick - s) / LENGTH[i]));
    return { ...p, progress, state: progress >= 1 ? "done" : tick >= s ? "active" : "idle" };
  });
  const share = Math.max(0, tick) / total;
  const tokens = Math.round(report.stats.tokens * Math.min(1, share * 1.6));
  const calls = Math.round(report.stats.tool_calls * Math.max(0, (share - 0.25) / 0.75));
  const found = domain === "airline" ? LOG.filter(([t, k]) => k === "bad" && t <= tick).length : 0;
  const log = (domain === "airline" ? LOG : RETAIL_LOG).filter(([t]) => t <= tick).slice(-9);

  return (
    <div className="page">
      <div className="head">
        <div>
          <h1 className="title">Audit a policy</h1>
          <p className="lede">Bylaw compiles the agent's policy into rules, searches for chains of allowed tool calls that reach a forbidden outcome, and proves each one in the τ²-bench simulator.</p>
        </div>
      </div>

      {tick < 0 && <div className="domains" role="radiogroup" aria-label="Domain">
        {(Object.keys(DOMAINS) as DomainKey[]).map((k) => (
          <button key={k} className="domain" role="radio" aria-checked={domain === k} disabled={running} onClick={() => { setDomain(k); setTick(-1); setFailed(false); }}>
            <span className="n">{DOMAINS[k].label}{domain === k && <Check size={22} aria-hidden="true" />}</span>
            <span className="d">{DOMAINS[k].desc}</span>
            <span className="tools">{DOMAINS[k].tools.map((t) => <code key={t}>{t}</code>)}</span>
          </button>
        ))}
      </div>}

      <div className="panel runbar">
        <div className="opts">
          {tick >= 0 && <span>Domain <b>{DOMAINS[domain].label}</b>{!running && <> · <button className="link" onClick={() => { setTick(-1); setFailed(false); }}>change</button></>}</span>}
          <span>Budget <b>2,000</b> tool calls</span>
          <span>Depth <b>≤ 4</b></span>
          <span>Replays <b>5</b> per hole</span>
          <Muse>Muse Spark · high reasoning</Muse>
        </div>
        {done ? (
          <a className="btn primary" href="#/report">Open report <ArrowRight size={16} aria-hidden="true" /></a>
        ) : (
          <button className="btn primary" onClick={run} disabled={running}>
            {running ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
            {running ? "Auditing…" : "Run audit"}
          </button>
        )}
      </div>

      {failed && (
        <div className="notice" role="alert">
          <AlertTriangle size={18} aria-hidden="true" />
          <div>
            <b>Muse Spark did not answer (HTTP 429, rate limited).</b>
            <p>The policy was not compiled. Retry in a minute, or run without Muse: the hand-written RuleSet and blind BFS still find and prove holes.</p>
            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              <button className="btn" onClick={run}><RotateCcw size={15} aria-hidden="true" />Retry</button>
              <button className="btn" onClick={() => { location.hash = "/"; run(); }}>Run without Muse</button>
            </div>
          </div>
        </div>
      )}

      <section className="panel" aria-label="Audit progress">
        <div className="phases">
          {phases.map((p, i) => (
            <div key={p.key} className={`phase ${p.state}`} aria-current={p.state === "active" ? "step" : undefined}>
              <span className="st">
                {p.state === "done" ? <Check size={14} aria-hidden="true" /> : p.state === "active" && !failed ? <Loader2 size={14} className="spin" aria-hidden="true" /> : <span>{i + 1}</span>}
                {p.state === "done" ? "done" : p.state === "active" ? (failed ? "stopped" : "running") : "waiting"}
              </span>
              <span className="nm">{p.label}</span>
              <span className="dt">{p.detail}</span>
              {p.muse && <span><Muse>{p.muse}</Muse></span>}
              <span className="bar"><i style={{ transform: `scaleX(${p.progress})` }} /></span>
            </div>
          ))}
        </div>
      </section>

      <div className="live">
        <section className="panel" aria-label="Run log">
          <div className="panel-h"><h2>Run log</h2><span className="label">{tick < 0 ? "idle" : done ? "finished" : failed ? "stopped" : "live"}</span></div>
          <div className="log" aria-live="polite">
            {tick < 0 && <span>Pick a domain and run the audit. Progress shows here.</span>}
            {log.map(([t, k, line]) => <span key={t} className={k}>{line}</span>)}
          </div>
        </section>
        <section className="panel tokens" aria-label="Counters">
          <Muse>Muse Spark tokens</Muse>
          <span className="big">{int(tokens)}</span>
          <span className="row">Tool calls <b className="num">{int(calls)} / 2,000</b></span>
          <span className="row">LLM calls <b className="num">{Math.round(report.stats.llm_calls * Math.min(1, share * 1.6))}</b></span>
          <span className="row">Holes proven
            <span className="found" aria-label={`${found} holes`}>
              {[0, 1, 2].map((i) => (i < found ? <i key={i} className="hole-mark" /> : <i key={i} className="empty" />))}
            </span>
          </span>
        </section>
      </div>
    </div>
  );
}
