// Bylaw: client of the live chat (docs/plan/06-showcase/vz3-contract.md v1.0, C2, C5, C6).
import type { Agent } from "./types";
import type { LiveEvent } from "./replay";

export interface LiveStatus {
  enabled: boolean;
  model: string;
  tokens_used: number;
  token_cap: number;
  sessions: number;
}

export interface LiveSession {
  session: string;
  guard: boolean;
  model: string;
  current_agent: string;
  context: Record<string, any>;
}

/** An HTTP refusal of the live API, with the contract's `detail` ("turn limit", "token cap", "live disabled"). */
export class LiveError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

async function refusal(res: Response) {
  let detail = `HTTP ${res.status}`;
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") detail = body.detail;
  } catch {}
  return new LiveError(res.status, detail);
}

/** C6. null when the backend has no live endpoints at all (an older Bylaw API). */
export async function fetchStatus(): Promise<LiveStatus | null> {
  try {
    const res = await fetch("/api/live/status");
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/** C5, with null on any failure so the caller keeps its static copy. */
export async function fetchAgents(): Promise<Agent[] | null> {
  try {
    const res = await fetch("/api/csdemo/agents");
    if (!res.ok) return null;
    const data = await res.json();
    return Array.isArray(data) && data.length ? data : null;
  } catch {
    return null;
  }
}

export async function createSession(guard: boolean): Promise<LiveSession> {
  const res = await fetch("/api/live/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ guard }),
  });
  if (!res.ok) throw await refusal(res);
  return res.json();
}

export interface TurnHandlers {
  onEvent: (e: LiveEvent) => void;
  onDone: (d: { current_agent: string; context: Record<string, any> }) => void;
  onError: (message: string) => void;
}

/** C2: one customer turn as a server-sent event stream (POST, so read with fetch, not EventSource). */
export async function sendTurn(session: string, text: string, h: TurnHandlers): Promise<void> {
  const res = await fetch(`/api/live/session/${encodeURIComponent(session)}/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok || !res.body) throw await refusal(res);
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buf = "";
  let finished = false;
  for (;;) {
    const { value, done } = await reader.read();
    if (value) buf += value.replace(/\r\n/g, "\n");
    let cut;
    while ((cut = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, cut);
      buf = buf.slice(cut + 2);
      const msg = parseBlock(block);
      if (!msg) continue;
      if (msg.event === "done") {
        finished = true;
        h.onDone(msg.data);
      } else if (msg.event === "error") {
        finished = true;
        h.onError(msg.data?.message ?? "The live run failed.");
      } else h.onEvent(msg.data);
    }
    if (done) break;
  }
  if (!finished) h.onError("The connection closed before the agents finished.");
}

export function parseBlock(block: string): { event: string; data: any } | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith(":")) continue; // keepalive comment
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
  }
  if (!data.length) return null;
  try {
    return { event, data: JSON.parse(data.join("\n")) };
  } catch {
    return null;
  }
}

/** Plain words for a refusal, and whether live chat is unusable until the page reloads. */
export function explain(err: unknown): { text: string; liveOff: boolean; newSession: boolean } {
  if (err instanceof LiveError) {
    if (err.status === 503) return { text: "Live chat is switched off on this server. Watch a recorded conversation instead.", liveOff: true, newSession: false };
    if (err.status === 429 && err.detail === "token cap")
      return { text: "The live demo has used its Muse budget for now. Watch a recorded conversation instead.", liveOff: true, newSession: false };
    if (err.status === 429)
      return { text: "This conversation reached its 12-message limit. Send again to start a new one.", liveOff: false, newSession: true };
    if (err.status === 409) return { text: "The agents are still answering your last message.", liveOff: false, newSession: false };
    if (err.status === 404) return { text: "This conversation expired. Send again to start a new one.", liveOff: false, newSession: true };
    return { text: `The live server refused the message (${err.detail}).`, liveOff: false, newSession: false };
  }
  return { text: "Could not reach the live server. Watch a recorded conversation instead.", liveOff: false, newSession: true };
}
