import { AlertTriangle, ChevronRight, RotateCcw } from "lucide-react";
import { useLayoutEffect, useRef, type ReactNode } from "react";
import type { ApiError, Change, Hole, Step } from "./api";

export const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

// The tile takes currentColor, so it follows the theme; the hole keeps its black fill and violet ring.
// `id` names the mask: an SVG inside a hidden parent (the rail in film mode) cannot lend its mask to another one.
export function Logo({ id = "mN3" }: { id?: string }) {
  return (
    <svg viewBox="0 0 120 120" aria-hidden="true">
      <defs>
        <mask id={id} maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">
          <rect width="120" height="120" fill="#fff" />
          <g transform="translate(60 60) scale(0.84) translate(-60 -60)">
            <rect x="26" y="16" width="22" height="88" rx="5" fill="#000" />
            <rect x="38" y="46" width="56" height="58" rx="24" fill="#000" />
          </g>
          <path d="M122.0 6.0 L109.3 12.7 L107.5 25.3 L92.0 33.6 L90.0 47.9 L73.5 57.3 L66.2 73.0 L52.3 76.6 L45.5 94.7 L31.0 101.9 L22.0 118.0" fill="none" stroke="#000" strokeWidth="10" strokeLinejoin="round" />
        </mask>
      </defs>
      <rect x="8" y="8" width="104" height="104" rx="28" fill="currentColor" mask={`url(#${id})`} />
      <circle cx="65.0" cy="72.6" r="7.6" fill="#07090E" stroke="#9152ff" strokeWidth="5" />
    </svg>
  );
}

// `live` passes a sheen over the badge while Muse is working.
export function Muse({ children, live }: { children: ReactNode; live?: boolean }) {
  return <span className={live ? "tag muse is-live" : "tag muse"}>{children}</span>;
}

export function Crumbs({ items }: { items: [string, string?][] }) {
  return (
    <nav className="crumbs" aria-label="Breadcrumb">
      {items.map(([label, href], i) => (
        <span key={label} style={{ display: "contents" }}>
          {i > 0 && <ChevronRight size={12} aria-hidden="true" />}
          {href ? <a href={href}>{label}</a> : <span aria-current="page">{label}</span>}
        </span>
      ))}
    </nav>
  );
}

// Skeletons shaped like the screen they stand in for.
export function Loading({ what, shape = "report" }: { what: string; shape?: "report" | "detail" | "bench" }) {
  return (
    <div role="status" className="loading">
      <span className="sr-only">Loading {what}…</span>
      <div className="skel" style={{ height: 48, width: "56%" }} />
      <div className="skel line" style={{ width: "72%" }} />
      <div className="skel line" style={{ width: "48%" }} />
      {shape === "report" && (
        <>
          <div className="summary">{[0, 1, 2, 3].map((i) => <div key={i} className="skel" style={{ height: 112 }} />)}</div>
          <div className="goal-group"><div className="skel" style={{ height: 280 }} /><div className="skel" style={{ height: 280 }} /></div>
        </>
      )}
      {shape === "detail" && (
        <div className="detail">
          <div className="skel" style={{ height: 420 }} />
          <div className="side"><div className="skel" style={{ height: 160 }} /><div className="skel" style={{ height: 240 }} /></div>
        </div>
      )}
      {shape === "bench" && <div className="bench"><div className="skel" style={{ height: 380 }} /><div className="skel" style={{ height: 200 }} /></div>}
    </div>
  );
}

export function Failure({ error, onRetry }: { error: ApiError; onRetry: () => void }) {
  return (
    <div className="notice" role="alert">
      <AlertTriangle aria-hidden="true" />
      <div>
        <b>{error.status ? `The API answered ${error.status}.` : "The Bylaw API is not reachable."}</b>
        <p>{error.status ? error.message.slice(0, 300) : "Start it from the repository root with uv run uvicorn bylaw.api:app, then retry."}</p>
        <div className="acts">
          <button className="btn sm" onClick={onRetry}><RotateCcw aria-hidden="true" />Retry</button>
        </div>
      </div>
    </div>
  );
}

const nf = new Intl.NumberFormat("en-US");
const cf = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
export const int = (n: number) => nf.format(Math.round(n));
export const usd = (n: number) => cf.format(n);
export const when = (iso: string) =>
  iso ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(iso)) + " UTC" : "";

// Tweens a number to its new value in a rAF loop, writing the text outside React's render.
export function Ticker({ value, format = int, ms = 900, className, testId }: { value: number; format?: (n: number) => string; ms?: number; className?: string; testId?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const cur = useRef(0);
  useLayoutEffect(() => {
    const el = ref.current!;
    const a = cur.current, b = value;
    if (reduced() || a === b) {
      el.textContent = format(b);
      cur.current = b;
      return;
    }
    let raf = 0, t0: number | undefined;
    const tick = (t: number) => {
      t0 ??= t;
      const p = Math.min(1, (t - t0) / ms);
      cur.current = a + (b - a) * (1 - Math.pow(1 - p, 4));
      el.textContent = format(p < 1 ? cur.current : b);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      cur.current = b;
      el.textContent = format(b);
    };
  }, [value]);
  return <span ref={ref} className={className} data-testid={testId} />;
}

// "basic_economy_flights_changed on T1QOBS" -> { name: "Basic economy flights changed", target: "T1QOBS" }
export function humanize(title: string, key = "") {
  const [raw, target = key.split(":")[1] ?? ""] = title.split(" on ");
  const name = raw.replace(/_/g, " ");
  return { name: name.charAt(0).toUpperCase() + name.slice(1), target };
}

// "update_reservation_flights" -> "Update reservation flights": tool names read as words outside the code view.
export const toolName = (t: string) => { const s = t.replace(/_/g, " "); return s.charAt(0).toUpperCase() + s.slice(1); };
export const chainText = (steps: { tool: string }[]) => steps.map((s, i) => (i ? toolName(s.tool).toLowerCase() : toolName(s.tool))).join(", then ");

// Hole routes carry the domain and the C4 v1.2 key.
export const holeHref = (domain: string, key: string, sub = "") => `#/${domain}/holes/${encodeURIComponent(key)}${sub}`;

function short(v: unknown): string {
  if (Array.isArray(v)) return "[" + v.map(short).join(", ") + "]";
  if (v && typeof v === "object") {
    const o = v as Record<string, unknown>;
    if ("flight_number" in o) return `${o.flight_number} ${o.date}`;
    return "{…}";
  }
  return JSON.stringify(v);
}

// Renders a tool call; payment_id and passengers are left out to keep the line readable.
export function Call({ step }: { step: Pick<Step, "tool" | "args"> }) {
  const args = Object.entries(step.args).filter(([k]) => k !== "payment_id" && k !== "passengers");
  return (
    <code translate="no">
      <span className="fn">{step.tool}</span>
      <span className="a">
        ({args.map(([k, v], i) => `${i ? ", " : ""}${k}=${short(v)}`).join("")})
      </span>
    </code>
  );
}

function leaves(v: unknown, path: string, out: Map<string, string>) {
  if (v && typeof v === "object") {
    for (const [k, x] of Object.entries(v)) leaves(x, Array.isArray(v) ? `${path}[${k}]` : path ? `${path}.${k}` : k, out);
  } else out.set(path, v === null || v === undefined ? "null" : String(v));
}

// The changed fields of one C4 v1.2 diff record, as [path, before, after]; "none" marks a field that did not exist.
export function changedFields(c: Change): [string, string, string][] {
  const b = new Map<string, string>(), a = new Map<string, string>();
  leaves(c.before ?? {}, "", b);
  leaves(c.after ?? {}, "", a);
  return [...new Set([...b.keys(), ...a.keys()])].filter((k) => b.get(k) !== a.get(k)).map((k) => [k, b.get(k) ?? "none", a.get(k) ?? "none"]);
}

// Class B evidence: the gold tasks that reach the goal (01 v1.7).
export function goldLine(tasks: string[], lead = "τ² grades this as correct in") {
  const t = tasks.length > 1 ? `tasks ${tasks.slice(0, -1).join(", ")} and ${tasks.at(-1)}` : `task ${tasks[0]}`;
  return `${lead} ${t}.`;
}

// Goals pre-registered as Class C, with the ambiguity each one was registered for.
// ponytail: copied from bylaw/env/tau2_airline.py CLASS_C_GOALS and the cls="C" goals of bylaw/goals_retail.py;
// the report does not carry a goal's registered class, so a new Class C goal needs a line here.
const PRE_C: Record<string, string> = {
  G7: "the policy is silent on a second certificate for the same incident, so it was pre-registered as an ambiguity",
  R5: "the once-only line may cover only item changes, not every modify or exchange, so it was pre-registered as an ambiguity",
  R8: "the refund-target line sits under returns, while modify and exchange only ask for a payment method, so it was pre-registered as an ambiguity",
};

// Why a Class C entry is not counted, in the order report.classify decides it: a goal pre-registered as Class C first;
// then a cancel followed by a rebook for the same user, the method the policy allows.
export function classCWhy(h: Hole) {
  if (PRE_C[h.goal]) return PRE_C[h.goal];
  const owner = (rid: unknown) => {
    const c = h.diff.reservations?.[String(rid)];
    return (c?.before ?? c?.after)?.user_id;
  };
  const rebooked = h.chain.some((s, i) =>
    s.tool === "cancel_reservation" && owner(s.args.reservation_id) !== undefined &&
    h.chain.slice(i + 1).some((t) => t.tool === "book_reservation" && t.args.user_id === owner(s.args.reservation_id)));
  return rebooked
    ? "cancel and rebook for the same user inside a permitted cancel ground is the method the policy allows"
    : "it was listed as an ambiguity for review";
}

// Class B: a gold task reaches the goal. Holds for a policy gap and for an ambiguity that practice resolves.
export const PRACTICE = "A gold task reaches this outcome: the policy and the benchmark's practice disagree.";

// Policy refs quote list items joined as " - "; show them one per line.
export const quote = (ref: string) => ref.replace(/ - /g, "\n– ");

// 1-based line of the policy that a quoted policy_ref starts on, or 0.
export function lineOf(lines: string[] | undefined, ref: string) {
  const head = ref.split(" - ")[0].trim().slice(0, 60);
  return head && lines ? lines.findIndex((l) => l.includes(head)) + 1 : 0;
}
