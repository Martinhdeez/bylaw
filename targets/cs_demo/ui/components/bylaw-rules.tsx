"use client";

// bylaw: the rules the guard enforces, from GET /api/ratified?domain=csdemo (forbidden goals, ratified amendments, base rules).
import { useEffect, useRef } from "react";

interface Rule {
  id: string;
  tool: string;
  note?: string;
}

interface Amendment {
  id: string;
  hole_key: string;
  policy_text: string;
  rule_patch: Rule[];
  ratified_at: string;
  ratified_by?: string;
}

export interface Rules {
  amendments: Amendment[];
  ruleset: { tool_rules: Rule[]; forbidden_goals: { id: string; description: string }[] };
}

/** null on any failure: the rail then shows only the checks. */
export async function fetchRules(): Promise<Rules | null> {
  try {
    const res = await fetch("/api/ratified?domain=csdemo");
    if (!res.ok) return null;
    const data = await res.json();
    return Array.isArray(data?.amendments) && data?.ruleset?.tool_rules ? data : null;
  } catch {
    return null;
  }
}

/** The list entry a check's rule id points at. Matched by hole key, since a recording can predate a re-ratified rule. */
export function ruleKey(rules: Rules | null, ruleId: string | null): string | null {
  if (!rules || !ruleId) return null;
  const a = rules.amendments.find((x) => ruleId.startsWith(`${x.hole_key}/`));
  if (a) return `a-${a.id}`;
  return rules.ruleset.tool_rules.some((r) => r.id === ruleId) ? `r-${ruleId}` : null;
}

const day = (iso: string) =>
  new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

const firstSentence = (s = "") => s.split(/(?<=\.)\s/)[0];

export function RulesList({ rules, focus }: { rules: Rules; focus: string | null }) {
  const root = useRef<HTMLDivElement>(null);
  const patched = new Set(rules.amendments.flatMap((a) => a.rule_patch.map((r) => r.id)));
  const base = rules.ruleset.tool_rules.filter((r) => !patched.has(r.id));
  const goals = rules.ruleset.forbidden_goals;

  useEffect(() => {
    const el = focus ? root.current?.querySelector<HTMLElement>(`[data-key="${CSS.escape(focus)}"]`) : null;
    el?.scrollIntoView({ block: "nearest" });
    // keyboard users land on the rule they asked for, not back at the top of the rail
    el?.focus({ preventScroll: true });
  }, [focus]);

  return (
    <div className="brr" ref={root}>
      <h3 className="br-label">Outcomes the policy forbids · checked on every tool call</h3>
      <ul className="brr-goals">
        {goals.map((g) => (
          <li key={g.id}>
            <span className="brr-id" data-tone="red">{g.id}</span>
            <span>{g.description}</span>
          </li>
        ))}
      </ul>

      <h3 className="br-label">Amendments in force · {rules.amendments.length}</h3>
      {rules.amendments.length === 0 ? (
        <p className="brr-none">None ratified yet. Only the base rules apply.</p>
      ) : (
        <ul className="brr-amends">
          {rules.amendments.map((a) => (
            <li key={a.id} tabIndex={-1} data-key={`a-${a.id}`} data-focus={focus === `a-${a.id}`} className="brr-amend">
              <div className="brr-meta">
                <span className="brr-id">{a.id}</span>
                <span>
                  guards <code>{a.rule_patch.map((r) => r.tool).join(", ")}</code>
                </span>
                <span className="brr-closes">blocks {a.hole_key.split(":")[0]}</span>
              </div>
              <p className="brr-text">{a.policy_text}</p>
              <div className="brr-foot">
                Ratified {a.ratified_by ? `by ${a.ratified_by}` : "by a person"}, {day(a.ratified_at)}
                {a.rule_patch.map((r) => (
                  <code key={r.id} className="br-rule">{r.id}</code>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}

      <details className="brr-base" open={focus?.startsWith("r-") || undefined}>
        <summary>
          {base.length} base rules, written from the agents' instructions
        </summary>
        <ul>
          {base.map((r) => (
            <li key={r.id} tabIndex={-1} data-key={`r-${r.id}`} data-focus={focus === `r-${r.id}`}>
              <code>{r.tool}</code>
              <span>{firstSentence(r.note)}</span>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
