import { useEffect, useRef, useState, type CSSProperties } from "react";
import { AlertTriangle, ArrowRight, Check, Loader2, Minus, Play, RotateCcw } from "lucide-react";
import { DOMAINS, api, type ApiError, type Domain, type Phase, type ProgressEvent } from "../api";
import { Muse, Ticker, int, toolName } from "../ui";

const ABOUT: Record<Domain, { label: string; docket: string; desc: string; tools: string[] }> = {
  airline: {
    label: "τ² Airline",
    docket: "01",
    desc: "Flight bookings, cabin changes, bags, cancellations and refunds.",
    tools: ["book_reservation", "update_reservation_flights", "update_reservation_baggages", "cancel_reservation", "send_certificate"],
  },
  retail: {
    label: "τ² Retail",
    docket: "02",
    desc: "Orders, exchanges, returns and address changes for an online store.",
    tools: ["cancel_pending_order", "exchange_delivered_order_items", "return_delivered_order_items", "modify_pending_order_items"],
  },
  csdemo: {
    label: "Airline customer service (OpenAI demo)",
    docket: "03",
    desc: "The agents of OpenAI's customer service demo: seats, rebooking, cancellations and compensation.",
    tools: ["update_seat", "book_new_flight", "cancel_flight", "issue_compensation", "assign_special_service_seat"],
  },
};

// The phases are the articles of the run, Art. I to Art. V.
const PHASES: { key: Phase; art: string; label: string; detail: string }[] = [
  { key: "compile", art: "I", label: "Compiling policy", detail: "policy text → tool rules and forbidden goals" },
  { key: "search", art: "II", label: "Searching", detail: "chains of allowed write calls, depth ≤ 4" },
  { key: "verify", art: "III", label: "Verifying", detail: "every hit replayed 5 times on a fresh DB" },
  { key: "amend", art: "IV", label: "Amending", detail: "one policy sentence and a rule patch per hole" },
  { key: "backtest", art: "V", label: "Backtesting", detail: "gold tasks replayed through the patched rules" },
];

type Run = { id?: string; events: ProgressEvent[]; status: "idle" | "starting" | "running" | "done" | "error"; error?: string; useLlm: boolean };

function Status({ run }: { run: Run }) {
  const last = run.events.at(-1);
  if (run.status === "idle") return <span className="status"><i />Idle</span>;
  if (run.status === "starting" || !last) return <span className="status running"><i />Starting</span>;
  if (run.status === "running") return <span className="status running"><i />Running <b>{last.phase}</b> {last.t.toFixed(1)} s</span>;
  if (run.status === "done") return <span className="status done"><i />Finished in {Math.round(last.t)} s</span>;
  return <span className="status error"><i />Stopped</span>;
}

export function Audit({ domain, onDomain, onDone }: { domain: Domain; onDomain: (d: Domain) => void; onDone: () => void }) {
  const [useLlm, setUseLlm] = useState(true);
  const [amend, setAmend] = useState(true);
  const [budget, setBudget] = useState(2000);
  const [run, setRun] = useState<Run>({ events: [], status: "idle", useLlm: true });
  const es = useRef<EventSource>();
  useEffect(() => () => es.current?.close(), []);

  const start = async (llm = useLlm) => {
    es.current?.close();
    setUseLlm(llm);
    setRun({ events: [], status: "starting", useLlm: llm });
    let id: string;
    try {
      ({ id } = await api.startAudit({ domain, use_llm: llm, budget, amend }));
    } catch (e) {
      const err = e as ApiError;
      return setRun({ events: [], status: "error", useLlm: llm, error: err.status ? `The API refused the audit (${err.status}): ${err.message.slice(0, 200)}` : err.message });
    }
    setRun({ id, events: [], status: "running", useLlm: llm });
    const src = api.events(id);
    es.current = src;
    src.onmessage = (m) => {
      const ev = JSON.parse(m.data) as ProgressEvent;
      const end = ev.phase === "done" || ev.phase === "error";
      if (end) src.close();
      setRun((r) => ({ ...r, events: [...r.events, ev], status: ev.phase === "done" ? "done" : ev.phase === "error" ? "error" : r.status, error: ev.phase === "error" ? ev.message : r.error }));
      if (ev.phase === "done") onDone();
    };
    src.onerror = () => {
      if (src.readyState === EventSource.CLOSED) setRun((r) => (r.status === "running" ? { ...r, status: "error", error: "The progress stream closed before the audit finished." } : r));
    };
  };

  const busy = run.status === "starting" || run.status === "running";
  const last = run.events.at(-1);
  const seen = new Set(run.events.map((e) => e.phase));
  const order = PHASES.map((p) => p.key);
  const current = [...run.events].reverse().find((e) => order.includes(e.phase))?.phase;
  const phases = PHASES.map((p) => {
    const i = order.indexOf(p.key);
    const reached = seen.has(p.key);
    const passed = run.status === "done" || (current !== undefined && order.indexOf(current) > i);
    const state = reached && passed ? "done" : reached ? (run.status === "error" ? "stopped" : "active") : run.status === "done" || passed ? "skipped" : "idle";
    return { ...p, state, muse: run.events.some((e) => e.phase === p.key && e.muse) };
  });
  // The run bar's bottom rule: the share of phases settled, plus half a phase while one is running.
  const settled = phases.filter((p) => p.state === "done" || p.state === "skipped").length;
  const tape = run.status === "done" ? 1 : run.status === "idle" ? 0 : (settled + (busy ? 0.5 : 0)) / PHASES.length;

  return (
    <div className="page">
      <div className="head">
        <div>
          <h1 className="title">Audit a <span className="v">policy</span></h1>
          <p className="lede">Bylaw compiles the agent's policy into rules, searches for chains of allowed tool calls that reach a forbidden outcome, and proves each one in the τ²-bench simulator.</p>
        </div>
        <Status run={run} />
      </div>

      {run.status === "idle" && (
        <div className="domains" role="radiogroup" aria-label="Domain">
          {DOMAINS.map((k) => (
            <button key={k} className="domain" role="radio" aria-checked={domain === k} onClick={() => onDomain(k)}>
              <span className="dk">Docket {ABOUT[k].docket}</span>
              <span className="n">{ABOUT[k].label}{domain === k && <span className="ck"><Check aria-hidden="true" /></span>}</span>
              <span className="d">{ABOUT[k].desc}</span>
              <span className="tools">{ABOUT[k].tools.map((t) => <span key={t} className="chip">{toolName(t)}</span>)}</span>
            </button>
          ))}
        </div>
      )}

      <div className="panel runbar">
        <span className={run.status === "done" ? "tape done" : "tape"} style={{ "--f": tape } as CSSProperties} aria-hidden="true" />
        <div className="opts">
          {run.status !== "idle" && (
            <span>Domain <b>{ABOUT[domain].label}</b>{!busy && <> · <button className="link" onClick={() => setRun({ events: [], status: "idle", useLlm })}>change</button></>}</span>
          )}
          <label className="opt"><input type="checkbox" checked={useLlm} disabled={busy} onChange={(e) => setUseLlm(e.target.checked)} />Use Muse Spark</label>
          <label className="opt"><input type="checkbox" checked={amend} disabled={busy} onChange={(e) => setAmend(e.target.checked)} />Draft amendments</label>
          <label className="opt">Budget
            <input className="num-in" type="number" name="budget" autoComplete="off" inputMode="numeric" min={10} max={20000} step={100} value={budget} disabled={busy} onChange={(e) => setBudget(Math.max(10, Number(e.target.value) || 0))} />
            tool calls
          </label>
        </div>
        {run.status === "done" ? (
          <a className="btn primary" href={`#/${domain}/report`}>Open report<span className="ic"><ArrowRight aria-hidden="true" /></span></a>
        ) : (
          <button className="btn primary" onClick={() => start()} disabled={busy}>
            {busy ? "Auditing…" : "Run audit"}
            <span className="ic">{busy ? <Loader2 className="spin" aria-hidden="true" /> : <Play aria-hidden="true" />}</span>
          </button>
        )}
      </div>

      {run.status === "error" && (
        <div className="notice" role="alert">
          <AlertTriangle aria-hidden="true" />
          <div>
            <b>The audit stopped.</b>
            <p>{run.error}</p>
            <div className="acts">
              <button className="btn sm" onClick={() => start(run.useLlm)}><RotateCcw aria-hidden="true" />Retry</button>
              {run.useLlm && <button className="btn sm" onClick={() => start(false)}>Run without Muse</button>}
            </div>
          </div>
        </div>
      )}

      <section className="panel" aria-label="Audit progress">
        <div className="phases">
          {phases.map((p) => (
            <div key={p.key} className={`phase ${p.state}`} aria-current={p.state === "active" ? "step" : undefined}>
              <span className="st">
                <span className="art">Art. {p.art}</span>
                {p.state === "done" ? <Check aria-hidden="true" /> : p.state === "active" ? <Loader2 className="spin" aria-hidden="true" /> : p.state === "skipped" ? <Minus aria-hidden="true" /> : null}
                {p.state === "idle" ? "waiting" : p.state === "active" ? "running" : p.state}
              </span>
              <span className="nm">{p.label}</span>
              <span className="dt">{p.detail}</span>
              {p.muse && <span><Muse live={p.state === "active"}>Muse Spark</Muse></span>}
              <span className="bar"><i /></span>
            </div>
          ))}
        </div>
      </section>

      <div className="live">
        <section className="panel" aria-label="Run log">
          <div className="panel-h"><h2>Run log</h2><Status run={run} /></div>
          <div className="log" aria-live="polite">
            {run.status === "idle" && <span>Pick a domain and run the audit. Progress shows here.</span>}
            {run.status === "starting" && <span>Starting the audit…</span>}
            {run.events.slice(-9).map((e, i) => (
              <span key={run.events.length - i} className={e.phase === "error" ? "bad" : e.phase === "done" ? "ok" : e.muse ? "mu" : ""}>
                <span className="ts">{e.t.toFixed(1).padStart(6)}s</span>  {e.phase.padEnd(8)} {e.message}
              </span>
            ))}
            {busy && <span><span className="caret" /></span>}
          </div>
        </section>
        <section className="panel tokens" aria-label="Counters">
          <Muse live={busy && run.useLlm}>Muse Spark tokens</Muse>
          <Ticker className="big" testId="tokens" value={last?.tokens ?? 0} />
          <div className="rows">
            <span className="row">Tool calls <b><Ticker value={last?.tool_calls ?? 0} /> / {int(budget)}</b></span>
            <span className="row">LLM calls <b><Ticker value={last?.llm_calls ?? 0} /></b></span>
            <span className="row">Holes proven <b style={{ color: last?.holes ? "var(--red)" : undefined }}><Ticker value={last?.holes ?? 0} /></b></span>
          </div>
        </section>
      </div>
    </div>
  );
}
