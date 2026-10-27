import { AlertTriangle, ChevronRight, Loader2, RotateCcw, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import type { ApiError, Change, Step } from "./api";

export function Logo() {
  return (
    <svg viewBox="0 0 120 120" aria-hidden="true">
      <defs>
        <mask id="mN3" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">
          <rect width="120" height="120" fill="#fff" />
          <g transform="translate(60 60) scale(0.84) translate(-60 -60)">
            <rect x="26" y="16" width="22" height="88" rx="5" fill="#000" />
            <rect x="38" y="46" width="56" height="58" rx="24" fill="#000" />
          </g>
          <path d="M122.0 6.0 L109.3 12.7 L107.5 25.3 L92.0 33.6 L90.0 47.9 L73.5 57.3 L66.2 73.0 L52.3 76.6 L45.5 94.7 L31.0 101.9 L22.0 118.0" fill="none" stroke="#000" strokeWidth="7" strokeLinejoin="round" />
        </mask>
      </defs>
      <rect x="8" y="8" width="104" height="104" rx="28" fill="currentColor" mask="url(#mN3)" />
      <circle cx="65.0" cy="72.6" r="7.6" fill="#07090E" stroke="#FF4D2E" strokeWidth="5" />
    </svg>
  );
}

export function Muse({ children }: { children: ReactNode }) {
  return (
    <span className="tag muse">
      <Sparkles size={13} aria-hidden="true" />
      {children}
    </span>
  );
}

export function Crumbs({ items }: { items: [string, string?][] }) {
  return (
    <nav className="crumbs" aria-label="Breadcrumb">
      {items.map(([label, href], i) => (
        <span key={label} style={{ display: "contents" }}>
          {i > 0 && <ChevronRight size={13} aria-hidden="true" />}
          {href ? <a href={href}>{label}</a> : <span aria-current="page">{label}</span>}
        </span>
      ))}
    </nav>
  );
}

export function Loading({ what }: { what: string }) {
  return (
    <div className="panel empty-state" role="status">
      <Loader2 size={22} className="spin" aria-hidden="true" />
      <p>Loading {what}…</p>
    </div>
  );
}

export function Failure({ error, onRetry }: { error: ApiError; onRetry: () => void }) {
  return (
    <div className="notice" role="alert">
      <AlertTriangle size={18} aria-hidden="true" />
      <div>
        <b>{error.status ? `The API answered ${error.status}.` : "The Bylaw API is not reachable."}</b>
        <p>{error.status ? error.message.slice(0, 300) : "Start it from the repository root with uv run uvicorn bylaw.api:app, then retry."}</p>
        <button className="btn" style={{ marginTop: 10 }} onClick={onRetry}>
          <RotateCcw size={15} aria-hidden="true" />Retry
        </button>
      </div>
    </div>
  );
}

const nf = new Intl.NumberFormat("en-US");
const cf = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
export const int = (n: number) => nf.format(n);
export const usd = (n: number) => cf.format(n);
export const when = (iso: string) =>
  iso ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(iso)) + " UTC" : "";

// "basic_economy_flights_changed on T1QOBS" -> { name: "Basic economy flights changed", target: "T1QOBS" }
export function humanize(title: string, key = "") {
  const [raw, target = key.split(":")[1] ?? ""] = title.split(" on ");
  const name = raw.replace(/_/g, " ");
  return { name: name.charAt(0).toUpperCase() + name.slice(1), target };
}

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

// The changed fields of one C4 v1.2 diff record, as [path, before, after]; "—" marks a field that did not exist.
export function changedFields(c: Change): [string, string, string][] {
  const b = new Map<string, string>(), a = new Map<string, string>();
  leaves(c.before ?? {}, "", b);
  leaves(c.after ?? {}, "", a);
  return [...new Set([...b.keys(), ...a.keys()])].filter((k) => b.get(k) !== a.get(k)).map((k) => [k, b.get(k) ?? "—", a.get(k) ?? "—"]);
}

// Class B evidence: the gold tasks that reach the goal (01 v1.7).
export function goldLine(tasks: string[], lead = "τ² grades this as correct in") {
  const t = tasks.length > 1 ? `tasks ${tasks.slice(0, -1).join(", ")} and ${tasks.at(-1)}` : `task ${tasks[0]}`;
  return `${lead} ${t}.`;
}

// Policy refs quote list items joined as " - "; show them one per line.
export const quote = (ref: string) => ref.replace(/ - /g, "\n– ");

// 1-based line of the policy that a quoted policy_ref starts on, or 0.
export function lineOf(lines: string[] | undefined, ref: string) {
  const head = ref.split(" - ")[0].trim().slice(0, 60);
  return head && lines ? lines.findIndex((l) => l.includes(head)) + 1 : 0;
}
