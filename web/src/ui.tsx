import { ChevronRight, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import type { Step } from "./fixtures";

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

export const int = (n: number) => n.toLocaleString("en-US");
export const usd = (n: number) => "$" + n.toLocaleString("en-US");

function short(v: unknown): string {
  if (Array.isArray(v)) return "[" + v.map(short).join(", ") + "]";
  if (v && typeof v === "object") {
    const o = v as Record<string, unknown>;
    if ("flight_number" in o) return `${o.flight_number} ${o.date}`;
    return "{…}";
  }
  return JSON.stringify(v);
}

// Renders a tool call; payment_id is left out to keep the line readable.
export function Call({ step }: { step: Pick<Step, "tool" | "args"> }) {
  const args = Object.entries(step.args).filter(([k]) => k !== "payment_id");
  return (
    <code translate="no">
      <span className="fn">{step.tool}</span>
      <span className="a">
        ({args.map(([k, v], i) => `${i ? ", " : ""}${k}=${short(v)}`).join("")})
      </span>
    </code>
  );
}
