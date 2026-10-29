// VZ2: the Live view. Replays a recorded customer conversation with the airline's agents (CS-C3 event files), once
// without Bylaw enforcing and once with it, and shows every action the agents propose next to Bylaw's decision.
// Approved reference: docs/plan/06-showcase/mocks/vz1-live-v4-3.html (on view/vz1-prototype).
// Every figure on this screen comes from an event file; what a file does not carry shows as not recorded.
import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, CircleCheck, CircleDashed, OctagonX, Pause, Play, RotateCcw } from "lucide-react";
import { ApiError, api, call, useGet, type LiveEntry, type LiveEvent, type LiveRun } from "../api";
import { Failure, Logo, usd, when } from "../ui";
import "./live.css";

type Check = Extract<LiveEvent, { type: "bylaw_check" }>;
type Row = { t: number; agent: string; tool: string; args: Record<string, unknown>; check?: Check; out?: { t: number; text: string } };
type Side = "before" | "after";

const ACTION: Record<string, string> = {
  flight_status_tool: "Check the flight status",
  get_trip_details: "Look up the trip",
  faq_lookup_tool: "Read the policy FAQ",
  issue_compensation: "Issue compensation vouchers",
  update_seat: "Change the seat",
  assign_special_service_seat: "Assign a special service seat",
  book_new_flight: "Book a new flight",
  cancel_flight: "Cancel the flight",
  get_matching_flights: "Find matching flights",
  baggage_tool: "Check the baggage",
  display_seat_map: "Show the seat map",
};
const action = (tool: string) => ACTION[tool] ?? tool.replace(/_/g, " ");
const agentName = (a: string) => a.replace(/ Agent$/, "");
const TAIL = 2.5, RESULT = 6;

// Tool calls in event order: each bylaw_check and tool_output belongs to the latest call of its tool still missing one.
function rowsOf(events: LiveEvent[]): Row[] {
  const rows: Row[] = [];
  for (const e of events) {
    if (e.type === "tool_call") rows.push({ t: e.t, agent: e.agent, tool: e.tool, args: e.args });
    if (e.type === "bylaw_check") { const r = rows.findLast((r) => r.tool === e.tool && !r.check); if (r) r.check = e; }
    if (e.type === "tool_output") { const r = rows.findLast((r) => r.tool === e.tool && !r.out); if (r) r.out = { t: e.t, text: e.output }; }
  }
  return rows;
}

// The demo session after the latest write at or before `at` (the state events carry the C4 diff of the session).
function sessionAt(run: LiveRun, at: number): Record<string, unknown> | null {
  let s: Record<string, unknown> | null = null;
  for (const e of run.events) if (e.type === "state" && e.t <= at && e.diff.context?.session?.after) s = e.diff.context.session.after;
  return s;
}
const vouchersOf = (s: Record<string, unknown> | null | undefined) => (Array.isArray(s?.vouchers) ? (s!.vouchers as string[]) : []);
// The face value the vouchers state, only when every voucher states one.
function faceValue(v: string[]) {
  const n = v.map((x) => x.match(/\$(\d+(?:\.\d+)?)/)?.[1]);
  return n.length && n.every(Boolean) ? n.reduce((a, b) => a + Number(b), 0) : null;
}
// The flight on file and its status, from the demo session: the fact a compensation rule turns on.
function flightFact(s: Record<string, unknown> | null | undefined) {
  const f = s?.flight_number;
  const seg = Array.isArray(s?.itinerary) ? (s!.itinerary as Record<string, unknown>[]).find((x) => x.flight_number === f) : undefined;
  return f && seg?.status ? `${f}: ${seg.status}` : null;
}
const paidOf = (r?: LiveRun) => (r?.final_state ? faceValue(vouchersOf(r.final_state)) ?? (vouchersOf(r.final_state).length ? null : 0) : null);
const blockedIn = (r?: LiveRun) => !!r && rowsOf(r.events).some((x) => x.check && !x.check.allowed && x.check.enforced);
const clock = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const argText = (a: Record<string, unknown>) => Object.entries(a).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ");

// Keeps a scroll box at its end when `dep` changes, and again once the web fonts have settled the row heights.
function useStick(dep: unknown) {
  const ref = useRef<HTMLOListElement>(null);
  useEffect(() => {
    const end = () => { const el = ref.current; if (el) el.scrollTop = el.scrollHeight; };
    end();
    document.fonts?.ready.then(end);
  }, [dep]);
  return ref;
}

function useRuns() {
  const list = useGet<LiveEntry[]>(api.live());
  const [runs, setRuns] = useState<{ before?: LiveRun; after?: LiveRun; error?: ApiError; name?: string }>({});
  useEffect(() => {
    const all = list.data;
    if (!all?.length) return;
    // The first script recorded both ways; else the first file there is.
    const name = all.find((e) => all.some((o) => o.name === e.name && o.guard !== e.guard))?.name ?? all[0].name;
    const pick = (g: boolean) => all.find((e) => e.name === name && e.guard === g);
    const get = (e?: LiveEntry) => (e ? call<LiveRun>(api.liveFile(e.file)) : Promise.resolve(undefined));
    let on = true;
    Promise.all([get(pick(false)), get(pick(true))]).then(
      ([before, after]) => on && setRuns({ before, after, name }),
      (error: ApiError) => on && setRuns({ error, name }),
    );
    return () => void (on = false);
  }, [list.data]);
  return { list, runs };
}

export function Live({ film }: { film: boolean }) {
  const { list, runs } = useRuns();
  if (list.error) return <div className="page lvp"><LiveHead /><Failure error={list.error} onRetry={list.reload} /></div>;
  if (list.data && !list.data.length)
    return (
      <div className="page lvp">
        <LiveHead />
        <div className="panel lv-empty">
          <b>No live runs recorded yet.</b>
          <p>Record the script once without Bylaw and once with it, from the repository root:</p>
          <pre>{"uv run python -m bylaw live --domain csdemo --script scripts/live/csdemo-d1.json -o reports/live/csdemo-d1.json\nuv run python -m bylaw live --domain csdemo --script scripts/live/csdemo-d1.json --guard -o reports/live/csdemo-d1-guard.json"}</pre>
        </div>
      </div>
    );
  if (runs.error) return <div className="page lvp"><LiveHead /><Failure error={runs.error} onRetry={list.reload} /></div>;
  if (!runs.before && !runs.after)
    return (
      <div className="page lvp" role="status">
        <span className="sr-only">Loading the live runs…</span>
        <div className="skel" style={{ height: 40, width: "60%" }} />
        <div className="lv-grid"><div className="skel" style={{ height: 520 }} /><div className="skel" style={{ height: 520 }} /><div className="skel" style={{ height: 520 }} /></div>
      </div>
    );
  return <Player before={runs.before} after={runs.after} film={film} />;
}

// The brand bar the user asked for: the 72px mark with its crack, the wordmark and the tagline.
const LiveHead = () => (
  <div className="lv-brand">
    <Logo id="mLive" />
    <b>Bylaw</b>
    <span>The application decides what an AI agent may do</span>
  </div>
);

function Player({ before, after, film }: { before?: LiveRun; after?: LiveRun; film: boolean }) {
  // One timeline: the run without Bylaw, then the run with it, then the result side by side.
  const parts = useMemo(() => {
    const out: { side: Side; run: LiveRun; start: number; dur: number }[] = [];
    let at = 0;
    for (const [side, run] of [["before", before], ["after", after]] as const) {
      if (!run) continue;
      const dur = (run.events.at(-1)?.t ?? 0) + TAIL;
      out.push({ side, run, start: at, dur });
      at += dur;
    }
    return { list: out, result: at, total: at + RESULT };
  }, [before, after]);

  const start = Number(new URLSearchParams(location.search).get("at"));
  const [t, setT] = useState(Number.isFinite(start) ? Math.min(Math.max(start, 0), parts.total) : 0);
  const [playing, setPlaying] = useState(film);
  const [speed, setSpeed] = useState(1);
  const [calls, setCalls] = useState(false);
  useEffect(() => {
    if (!playing) return;
    let raf = 0, last = performance.now();
    const f = (now: number) => {
      setT((x) => Math.min(parts.total, x + ((now - last) / 1000) * speed));
      last = now;
      raf = requestAnimationFrame(f);
    };
    raf = requestAnimationFrame(f);
    return () => cancelAnimationFrame(raf);
  }, [playing, speed, parts.total]);
  useEffect(() => void (t >= parts.total && setPlaying(false)), [t, parts.total]);

  const inResult = t >= parts.result;
  const part = parts.list.findLast((p) => t >= p.start) ?? parts.list[0];
  const at = Math.min(t - part.start, part.dur);
  const toggle = () => {
    if (!playing && t >= parts.total) setT(0);
    setPlaying(!playing);
  };
  // Before / After: jump to the same moment of the other run.
  const jump = (side: Side) => {
    const p = parts.list.find((x) => x.side === side);
    if (p) setT(p.start + Math.min(inResult ? 0 : at, p.dur - 0.001));
  };

  return (
    <div className={film ? "page lvp film" : "page lvp"}>
      <LiveHead />
      <Headline part={part} at={at} inResult={inResult} before={before} after={after} />
      {inResult ? <Result before={before} after={after} /> : <Stage run={part.run} at={at} calls={calls} key={part.side} />}
      <footer className="lv-transport" aria-label="Playback">
        <button className="lv-btn icon" onClick={toggle} aria-label={playing ? "Pause" : t >= parts.total ? "Replay" : "Play"}>
          {playing ? <Pause aria-hidden="true" /> : t >= parts.total ? <RotateCcw aria-hidden="true" /> : <Play aria-hidden="true" />}
        </button>
        <button className="lv-btn" onClick={() => setSpeed(speed === 1 ? 2 : 1)} aria-label={`Playback speed ${speed}×`}>{speed}×</button>
        <div className="lv-seg" role="group" aria-label="Without or with Bylaw">
          {parts.list.map((p) => (
            <button key={p.side} aria-pressed={!inResult && part.side === p.side} onClick={() => jump(p.side)}>{p.side === "before" ? "Without Bylaw" : "With Bylaw"}</button>
          ))}
          <button aria-pressed={inResult} onClick={() => setT(parts.result)}>Result</button>
        </div>
        <button className="lv-btn" aria-pressed={calls} onClick={() => setCalls(!calls)}>Show tool calls</button>
        <div className="lv-scrub">
          <input type="range" min={0} max={parts.total} step={0.05} value={t} aria-label="Timeline" aria-valuetext={clock(t)}
            onChange={(e) => { setPlaying(false); setT(Number(e.target.value)); }} />
          <div className="lv-chaps" aria-hidden="true">
            {[...parts.list.map((p) => ({ k: p.side, at: p.start })), { k: "result", at: parts.result }].map((c) => (
              <span key={c.k} style={{ left: `${(c.at / parts.total) * 100}%` }} />
            ))}
          </div>
        </div>
        <span className="lv-clock">{clock(t)} / {clock(parts.total)}</span>
      </footer>
    </div>
  );
}

function Headline({ part, at, inResult, before, after }: { part: { side: Side; run: LiveRun }; at: number; inResult: boolean; before?: LiveRun; after?: LiveRun }) {
  const b = paidOf(before), a = paidOf(after);
  let lead: string, claim: string, sub: string;
  if (inResult && b !== null && a !== null) [lead, claim, sub] = [`${usd(b)} without Bylaw.`, `${usd(a)} with it.`, "The model proposes. The application decides."];
  // One run recorded (e.g. only the guarded one): say what it paid and that the other side is missing.
  else if (inResult && (a !== null || b !== null)) [lead, claim, sub] = a !== null
    ? [`${usd(a)} with Bylaw.`, "The run without it is not recorded.", "The model proposes. The application decides."]
    : [`${usd(b!)} without Bylaw.`, "The run with it is not recorded.", "The model proposes. The application decides."];
  else if (inResult) [lead, claim, sub] = ["Without Bylaw and with it,", "side by side.", "The model proposes. The application decides."];
  else if (part.run.guard) [lead, claim, sub] = ["With Bylaw.", blockedIn(part.run) ? "The same action is stopped before it runs." : "Every action is checked before it runs.", narrate(part.run, at)];
  else [lead, claim, sub] = ["Without Bylaw.", b ? `The agents pay ${usd(b)} in vouchers.` : "The agents run every action they propose.", narrate(part.run, at)];
  const r = inResult ? after ?? before : part.run;
  return (
    <header className="lv-head">
      <h1 data-slot="headline"><span>{lead}</span> {claim}</h1>
      <p className="lv-cap" data-slot="narration" aria-live="polite">{sub}</p>
      {r && (
        <dl className="lv-meta">
          <div><dt>Script</dt><dd>{r.name}</dd></div>
          <div><dt>Model</dt><dd>{r.model ?? "not recorded"}</dd></div>
          <div><dt>Recorded</dt><dd>{r.started ? when(r.started) : "not recorded"}</dd></div>
        </dl>
      )}
    </header>
  );
}

// One sentence for the latest event at the playhead.
function narrate(run: LiveRun, at: number) {
  const e = run.events.findLast((x) => x.t <= at && x.type !== "tool_output" && x.type !== "state");
  if (!e) return "The customer opens the airline's support chat.";
  switch (e.type) {
    case "user": return "The customer writes to the airline's support chat.";
    case "handoff": return `${agentName(e.from)} hands the conversation to ${agentName(e.to)}.`;
    case "agent_message": return `${agentName(e.agent)} answers the customer.`;
    case "tool_call": return `${agentName(e.agent)} proposes an action: ${action(e.tool).toLowerCase()}.`;
    case "bylaw_check":
      if (e.enforced) return e.allowed ? "Bylaw checks it against the rules and allows it." : "Bylaw blocks it before it runs.";
      return e.allowed ? "Nothing enforces a rule here. The action runs." : "A Bylaw rule would block this, but nothing enforces it. The action runs.";
  }
  return "";
}

function Stage({ run, at, calls }: { run: LiveRun; at: number; calls: boolean }) {
  const seen = run.events.filter((e) => e.t <= at);
  const rows = rowsOf(run.events).filter((r) => r.t <= at);
  const session = sessionAt(run, at);
  const done = rows.filter((r) => r.check && r.check.t <= at);
  const allowed = done.filter((r) => r.check!.allowed).length;
  const okWord = run.guard ? "allowed" : "ran, logged only";
  const blocked = done.filter((r) => !r.check!.allowed && r.check!.enforced).length;
  const unenforced = done.filter((r) => !r.check!.allowed && !r.check!.enforced).length;
  // The handoff trail: who held the conversation, in order.
  const first = run.events.find((e) => e.type === "handoff" || e.type === "agent_message" || e.type === "tool_call");
  const trail: string[] = first ? [first.type === "handoff" ? first.from : first.agent] : [];
  for (const e of seen) if (e.type === "handoff" && trail.at(-1) !== e.to) trail.push(e.to);

  return (
    <div className="lv-grid">
      <Chat events={seen} />
      <section className="panel lv-lane" aria-label="Bylaw: every action the agents propose, and the decision">
        <div className="lv-ph">
          <h2>Actions</h2>
          <span className={run.guard ? "lv-mode on" : "lv-mode"} data-slot="status">{run.guard ? "Bylaw enforcing" : "Bylaw not enforcing"}</span>
          <span className="lv-counts">
            <span><b>{allowed}</b> {okWord}</span>
            {run.guard ? <span className={blocked ? "r" : ""}><b>{blocked}</b> blocked</span> : <span><b>{unenforced}</b> would be blocked</span>}
          </span>
        </div>
        {trail.length > 0 && (
          <ol className="lv-trail" aria-label="Agents that held the conversation">
            {trail.map((a, i) => <li key={i} aria-current={i === trail.length - 1 ? "step" : undefined}>{agentName(a)}</li>)}
          </ol>
        )}
        <div className="lv-cols" aria-hidden="true"><span /><span>Proposed by the agent</span><span>Decided by Bylaw</span></div>
        <Rows rows={rows} at={at} calls={calls} run={run} />
      </section>
      <Ledger session={session} />
    </div>
  );
}

function Chat({ events }: { events: LiveEvent[] }) {
  const ref = useStick(events.length);
  return (
    <section className="panel lv-chat" aria-label="The customer's chat">
      <div className="lv-ph"><h2>Customer chat</h2></div>
      <ol ref={ref} data-slot="chat">
        {events.map((e, i) =>
          e.type === "user" ? <li key={i} className="me">{e.text}</li>
          : e.type === "agent_message" ? <li key={i} className="ag"><small>{agentName(e.agent)}</small>{e.text}</li>
          : e.type === "handoff" ? <li key={i} className="note">{agentName(e.to)} took over</li>
          : null,
        )}
      </ol>
    </section>
  );
}

function Rows({ rows, at, calls, run }: { rows: Row[]; at: number; calls: boolean; run: LiveRun }) {
  // Scroll whenever the latest row grows (its verdict, its output), so it stays whole in view.
  const ref = useStick(rows.map((r) => `${r.check && r.check.t <= at ? 1 : 0}${r.out && r.out.t <= at ? 1 : 0}`).join("") + calls);
  if (!rows.length) return <p className="lv-none">No action proposed yet.</p>;
  return (
    <ol className="lv-rows" ref={ref}>
      {rows.map((r, i) => {
        const c = r.check && r.check.t <= at ? r.check : undefined;
        const ran = r.out && r.out.t <= at;
        const state = !c ? "pending" : c.allowed ? "ok" : c.enforced ? "blk" : "free";
        return (
          <li key={i} className={`lv-row ${state}${i === rows.length - 1 ? " now" : ""}`} data-testid="live-row">
            <span className="lv-t">{clock(r.t)}</span>
            <div className="lv-prop">
              <b>{action(r.tool)}</b>
              {r.agent !== rows[i - 1]?.agent && <small>{agentName(r.agent)}</small>}
              {calls && <code>{r.tool}({argText(r.args)})</code>}
            </div>
            <div className="lv-dec">
              {state === "pending" && <span className="lv-vd">Checking</span>}
              {state === "ok" && (c!.enforced
                ? <span className="lv-vd ok"><CircleCheck aria-hidden="true" />{ran ? "Allowed, ran" : "Allowed"}</span>
                : <span className="lv-vd free"><CircleDashed aria-hidden="true" />{ran ? "Ran, logged only" : "Logged only"}</span>)}
              {state === "free" && <span className="lv-vd free"><CircleDashed aria-hidden="true" />{ran ? "Ran, not enforced" : "Not enforced"}</span>}
              {state === "blk" && <span className="lv-vd blk"><OctagonX aria-hidden="true" />Blocked before it ran</span>}
              {c && !c.allowed && (
                <p className="lv-rule">
                  {c.enforced ? "Rule" : "Would be blocked by"} <span className="id">{c.rule_id ?? "rule not recorded"}</span>
                  {flightFact(sessionAt(run, c.t)) && <span className="fact">Flight data: {flightFact(sessionAt(run, c.t))}</span>}
                </p>
              )}
              {c && !c.allowed && c.policy_ref && (
                <details className="lv-out">
                  <summary><ChevronDown aria-hidden="true" />Policy source</summary>
                  <q>{c.policy_ref}</q>
                </details>
              )}
              {ran && (state === "blk" || calls) && (
                <details className="lv-out">
                  <summary><ChevronDown aria-hidden="true" />{state === "blk" ? "What the agent was told" : "Tool output"}</summary>
                  <code>{r.out!.text}</code>
                </details>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function Ledger({ session }: { session: Record<string, unknown> | null }) {
  const v = vouchersOf(session);
  const total = faceValue(v);
  return (
    <section className={v.length ? "lv-ledger issued" : "lv-ledger"} aria-label="What the airline paid out">
      <h2>Paid out</h2>
      <dl>
        <div><dt>Passenger</dt><dd>{String(session?.passenger_name ?? "not on file")}</dd></div>
        <div><dt>Confirmation</dt><dd>{String(session?.confirmation_number ?? "not on file")}</dd></div>
        <div><dt>Flight</dt><dd>{String(session?.flight_number ?? "not on file")}</dd></div>
        <div><dt>Compensation case</dt><dd>{String(session?.compensation_case_id ?? "none")}</dd></div>
      </dl>
      {v.length ? <ul>{v.map((x) => <li key={x}><span>{x}</span><b>{x.match(/\$\d+(?:\.\d+)?/)?.[0] ?? "not stated"}</b></li>)}</ul> : <p className="lv-nil">No vouchers issued.</p>}
      <div className="lv-total">
        <span>Face value</span>
        <b data-testid="paid">{v.length ? (total === null ? "not stated" : usd(total)) : usd(0)}</b>
      </div>
    </section>
  );
}

function Result({ before, after }: { before?: LiveRun; after?: LiveRun }) {
  return (
    <div className="lv-result">
      {([["before", before], ["after", after]] as const).map(([side, run]) => {
        const rows = run ? rowsOf(run.events) : [];
        const key = rows.find((r) => r.check && !r.check.allowed) ?? rows.at(-1);
        const c = key?.check;
        const asked = run?.events.findLast((e) => e.type === "user");
        const v = vouchersOf(run?.final_state);
        const total = faceValue(v);
        const stopped = !!c && !c.allowed && c.enforced;
        const answered = stopped && run!.events.some((e) => e.type === "agent_message" && e.t > c!.t);
        const caseId = run?.final_state?.compensation_case_id;
        return (
          <section key={side} className={`panel lv-side ${side}`} aria-label={side === "before" ? "Without Bylaw" : "With Bylaw"}>
            <h2>{side === "before" ? "Without Bylaw" : "With Bylaw"}</h2>
            {!run ? <p className="lv-nil">This run is not recorded.</p> : (
              <>
                <dl>
                  <div><dt>Customer</dt><dd>{asked?.type === "user" ? <q>{asked.text}</q> : "not recorded"}</dd></div>
                  <div><dt>Proposal</dt><dd>{key ? `${action(key.tool)}, by ${agentName(key.agent)}` : "No action proposed"}</dd></div>
                  <div><dt>Flight data</dt><dd>{flightFact(run.final_state) ?? "not recorded"}</dd></div>
                  <div><dt>Decision</dt><dd className={stopped ? "blk" : undefined}>{!c ? "Not recorded" : c.allowed ? "Allowed" : stopped ? `Blocked before it ran by ${c.rule_id ?? "a rule"}` : "Not enforced. The tool ran."}</dd></div>
                </dl>
                <p className="lv-big"><b data-testid={`result-${side}`}>{!run.final_state ? "not recorded" : v.length ? (total === null ? "not stated" : usd(total)) : usd(0)}</b>
                  <span>{v.length ? `issued in ${v.length} voucher${v.length > 1 ? "s" : ""}${caseId ? `. Case ${caseId}.` : "."}` : answered ? "issued. The agent still answered the customer." : "issued."}</span></p>
              </>
            )}
          </section>
        );
      })}
    </div>
  );
}
