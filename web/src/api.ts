// Client for the Bylaw HTTP API, contract C9 (docs/plan/03-product/contracts.md).
import { useEffect, useState } from "react";

// csdemo: the airline agents of openai-cs-agents-demo (RA1); the API has no bench for it.
export type Domain = "airline" | "retail" | "csdemo";
export const DOMAINS: Domain[] = ["airline", "retail", "csdemo"];
// The name a heading or a crumb uses: "the customer service policy", not the route id "csdemo".
export const DOMAIN_NAME: Record<Domain, string> = { airline: "airline", retail: "retail", csdemo: "customer service" };

// C4 v1.2 report (01 v1.7 classes), with the C7 amendment fields a hole may carry.
export type Verdict = { rule_id: string; ok: boolean; policy_ref: string; error?: string | null };
export type Step = { tool: string; args: Record<string, unknown>; ok: boolean; verdicts: Verdict[] };
export type Change = { before: Record<string, unknown> | null; after: Record<string, unknown> | null };
export type ToolRule = { id: string; tool: string; allow_if: string; policy_ref: string; note?: string };
export type Amendment = { id: string; hole_id: string; policy_text: string; rule_patch: ToolRule[]; rationale: string };
export type Backtest = { tasks: number; blocked: number; baseline_blocked: number; blocked_tasks: string[] };
export type Hole = {
  id: string;
  key: string;
  class: "A" | "B" | "C";
  gold?: { sanctioned: boolean; tasks: string[] }; // 01 v1.7
  goal: string;
  title: string;
  money_delta: number;
  chain: Step[];
  diff: Record<string, Record<string, Change>>;
  goal_true: boolean;
  replays: string;
  amendment?: Amendment;
  closes?: boolean;
  backtest?: Backtest;
};
export type Report = {
  // 01 v1.9: "bfs-fallback" = Muse was requested and every call failed; model is null unless a Muse call succeeded.
  run: { commit: string; domain: string; model: string | null; mode: "bfs" | "muse" | "bfs-fallback"; effort?: string; context_tokens?: number; started: string; budget: number; goals_commit: string };
  holes: Hole[]; // Class A
  contradictions?: Hole[]; // Class B, 01 v1.7
  ambiguities: Hole[];
  stats: { chains_tried: number; tool_calls: number; llm_calls: number; llm_errors?: number; tokens: number; seconds: number };
};
export type Phase = "compile" | "search" | "verify" | "amend" | "backtest" | "done" | "error";
export type ProgressEvent = {
  phase: Phase;
  message: string;
  muse: boolean;
  tokens: number;
  llm_calls: number;
  tool_calls: number;
  holes: number;
  t: number;
};
export type Audit = { id: string; domain: Domain; status: "running" | "done" | "error"; report: Report | null; error: string | null };
export type ForbiddenGoal = { id: string; name: string; policy_ref: string; description: string };
export type Ratified = {
  domain: Domain;
  amendments: (Amendment & { hole_key: string; ratified_at: string })[];
  ruleset: { domain: string; tool_rules: ToolRule[]; forbidden_goals: ForbiddenGoal[] };
};
export type Policy = { domain: Domain; lines: string[] };
export type Bench = {
  domain: Domain;
  budget: number;
  model?: string | null; // 01 v1.9
  rows: {
    mode: "bfs" | "muse"; holes: number; hole_keys: string[]; contradictions?: number; ambiguities?: number; tool_calls: number; llm_calls: number; tokens: number; seconds: number;
    found?: { key: string; tool_calls: number; seconds: number }[]; // C5 v1.6
  }[];
};

// CS-C3 v1.2 live run event file (docs/plan/06-showcase/contracts.md).
export type LiveEntry = { name: string; guard: boolean; file: string };
export type LiveEvent = { t: number } & (
  | { type: "user"; text: string }
  | { type: "agent_message"; agent: string; text: string }
  | { type: "handoff"; from: string; to: string }
  | { type: "tool_call"; agent: string; tool: string; args: Record<string, unknown> }
  | { type: "bylaw_check"; tool: string; allowed: boolean; rule_id: string | null; policy_ref: string | null; enforced: boolean }
  | { type: "tool_output"; tool: string; output: string }
  | { type: "state"; diff: Record<string, Record<string, Change>> }
);
export type LiveRun = { name: string; guard: boolean; model: string | null; started: string; events: LiveEvent[]; final_state: Record<string, unknown> | null };

// TR1 v1.0 usage and cost traceability. Null fields: the source does not record them.
export type UsageEntry = {
  id: string; stage: "compile" | "audit" | "amend" | "bench" | "live"; label: string; source: string;
  calls: number | null; input_tokens: number | null; output_tokens: number | null; tokens: number; seconds: number | null;
  cost_usd: { low: number; high: number };
};
export type Usage = {
  price: { model: string; input_per_1m: number; output_per_1m: number; source: string; read: string };
  recorded: { entries: UsageEntry[]; total: { calls: number; tokens: number; cost_usd: { low: number; high: number } } };
  live: { enabled: boolean; model: string; sessions: number; input_tokens: number; output_tokens: number; tokens_used: number; token_cap: number; cost_usd: number };
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  } catch {
    throw new ApiError(0, "The bylaw API is not reachable.");
  }
  if (!r.ok) throw new ApiError(r.status, (await r.text().catch(() => "")) || r.statusText);
  return r.json();
}

const q = (d: Domain) => `domain=${encodeURIComponent(d)}`;
export const api = {
  report: (d: Domain) => `/api/reports/latest?${q(d)}`,
  policy: (d: Domain) => `/api/policy?${q(d)}`,
  ratified: (d: Domain) => `/api/ratified?${q(d)}`,
  bench: (d: Domain) => `/api/bench?${q(d)}`,
  config: () => "/api/config",
  live: () => "/api/live",
  usage: () => "/api/usage",
  liveFile: (file: string) => `/api/live/${encodeURIComponent(file)}`,
  startAudit: (body: { domain: Domain; use_llm: boolean; budget: number; amend: boolean }) =>
    call<{ id: string }>("/api/audits", { method: "POST", body: JSON.stringify(body) }),
  audit: (id: string) => call<Audit>(`/api/audits/${encodeURIComponent(id)}`),
  events: (id: string) => new EventSource(`/api/audits/${encodeURIComponent(id)}/events`),
  ratify: (d: Domain, key: string) =>
    call<{ ratified: true; amendment_id: string; rule_ids: string[] }>(`/api/holes/${encodeURIComponent(key)}/ratify?${q(d)}`, { method: "POST" }),
};

export type Load<T> = { data?: T; error?: ApiError; loading: boolean; reload: () => void };

// GET a path; refetches when the path changes or reload() is called.
export function useGet<T>(path: string): Load<T> {
  const [n, setN] = useState(0);
  const [s, setS] = useState<{ path: string; data?: T; error?: ApiError }>({ path: "" });
  useEffect(() => {
    let live = true;
    call<T>(path).then(
      (data) => live && setS({ path, data }),
      (error: ApiError) => live && setS({ path, error }),
    );
    return () => {
      live = false;
    };
  }, [path, n]);
  const fresh = s.path === path;
  return { data: fresh ? s.data : undefined, error: fresh ? s.error : undefined, loading: !fresh, reload: () => setN((x) => x + 1) };
}
