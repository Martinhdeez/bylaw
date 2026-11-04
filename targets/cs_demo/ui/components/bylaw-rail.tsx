"use client";

// Bylaw: the rail beside the demo. Picks a recorded run, switches the guard, and narrates every check.
import { useEffect, useRef, useState } from "react";
import { Check, X, Pause, Play, RotateCcw, ShieldCheck, ShieldOff, Clapperboard } from "lucide-react";
import type { BylawCheck } from "@/lib/types";
import type { LiveFile, Scenario } from "@/lib/replay";
import type { LiveStatus } from "@/lib/live";
import { BylawMark } from "./bylaw-mark";
import { RulesList, fetchRules, ruleKey, type Rules } from "./bylaw-rules";
import { scrollMode } from "@/lib/utils";

interface BylawRailProps {
  scenarios: Scenario[];
  scenarioId: string;
  onScenario: (id: string) => void;
  guard: boolean;
  onGuard: (on: boolean) => void;
  mode: "replay" | "live";
  live: { on: boolean; status: LiveStatus | null; busy: boolean };
  onWatch: () => void;
  playing: boolean;
  onPlay: () => void;
  onRestart: () => void;
  speed: number;
  onSpeed: (s: number) => void;
  file: LiveFile | null;
  step: number;
  checks: BylawCheck[];
  moneyOut: number;
  moneyStopped: number;
  stoppedUnpriced: boolean;
  error: string | null;
}

const usd = (n: number) => `$${n.toLocaleString("en-US")}`;

function verdict(c: BylawCheck) {
  if (c.allowed) return { tone: "green", label: "Allowed" };
  if (c.enforced) return { tone: "red", label: "Blocked" };
  return { tone: "amber", label: "Would block" };
}

function CheckEntry({ c, latest, onRule }: { c: BylawCheck; latest: boolean; onRule?: () => void }) {
  const v = verdict(c);
  if (c.readOnly && c.allowed) {
    return (
      <li className="br-step br-step-read" data-latest={latest}>
        <span className="br-dot" data-tone="green" aria-hidden="true" />
        <span className="br-read-text">{c.wants}</span>
        <span className="br-read-tag">read only · allowed</span>
      </li>
    );
  }
  return (
    <li className="br-step" data-latest={latest} data-tone={v.tone}>
      <span className="br-dot" data-tone={v.tone} aria-hidden="true" />
      <div className="br-body">
        <div className="br-label">The agent wants to</div>
        <p className="br-wants">{c.wants}</p>
        {c.reads.length > 0 && (
          <>
            <div className="br-label">bylaw reads</div>
            <ul className="br-facts">
              {c.reads.map((f) => (
                <li key={f.label} data-ok={f.ok}>
                  {f.ok ? <Check className="h-3.5 w-3.5" aria-label="passes" /> : <X className="h-3.5 w-3.5" aria-label="fails" />}
                  <span>
                    <b>{f.label}:</b> {f.value}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
        <div className="br-verdict" data-tone={v.tone}>
          <span className="br-stamp">{v.label}</span>
          {c.rule_id &&
            (onRule ? (
              <button type="button" className="br-rule-link" onClick={onRule}>
                <code className="br-rule">{c.rule_id}</code>
                <span>See rule</span>
              </button>
            ) : (
              <code className="br-rule">{c.rule_id}</code>
            ))}
        </div>
        {c.reason && <p className="br-reason">{c.reason}</p>}
        {!c.allowed && !c.enforced && <p className="br-reason br-off">The guard is off, so the call ran anyway.</p>}
        {c.money !== 0 && (
          <p className="br-money" data-tone={c.money > 0 ? "out" : "kept"}>
            {c.money > 0
              ? `${usd(c.money)} left the airline`
              : `${usd(-c.money)} stayed with the airline: what this agent paid without bylaw in the recorded run`}
          </p>
        )}
      </div>
    </li>
  );
}

export function BylawRail(p: BylawRailProps) {
  const feed = useRef<HTMLDivElement>(null);
  const total = p.file?.events.length ?? 0;
  const isLive = p.mode === "live";
  const done = !isLive && total > 0 && p.step >= total;
  const blocked = p.checks.filter((c) => !c.allowed).length;
  const scenario = p.scenarios.find((s) => s.id === p.scenarioId);
  const [rules, setRules] = useState<Rules | null>(null);
  const [tab, setTab] = useState<"checks" | "rules">("rules");
  const [focus, setFocus] = useState<string | null>(null);
  const started = p.checks.length > 0;
  const showRules = !!rules && tab === "rules";

  useEffect(() => {
    void fetchRules().then(setRules);
  }, []);

  // idle: the rules (collapsed on phones); from the first check of a conversation: the checks
  useEffect(() => {
    setTab(started || window.matchMedia("(max-width: 480px)").matches ? "checks" : "rules");
    setFocus(null);
  }, [started]);

  useEffect(() => {
    if (!showRules) feed.current?.scrollTo({ top: feed.current.scrollHeight, behavior: scrollMode() });
  }, [p.checks.length, p.moneyOut, p.moneyStopped, p.step, showRules]);

  return (
    <aside className="bylaw-rail" aria-label="bylaw guard">
      <header className="br-head">
        <BylawMark className="br-logo" />
        <div>
          <div className="br-title">bylaw</div>
          <div className="br-sub">guards every tool call</div>
        </div>
        <button type="button" className="br-watch" onClick={p.onWatch}>
          <Clapperboard className="h-4 w-4" aria-hidden="true" />
          Watch it
        </button>
      </header>

      <button
        type="button"
        role="switch"
        aria-checked={p.guard}
        onClick={() => p.onGuard(!p.guard)}
        className="br-guard"
        data-on={p.guard}
      >
        {p.guard ? <ShieldCheck className="h-5 w-5" aria-hidden="true" /> : <ShieldOff className="h-5 w-5" aria-hidden="true" />}
        <span className="br-guard-text">
          <b>Guard {p.guard ? "on" : "off"}</b>
          <span>{p.guard ? "Blocks what the policy forbids" : "Only watches; every call runs"}</span>
        </span>
        <span className="br-switch" aria-hidden="true">
          <i />
        </span>
      </button>

      <fieldset className="br-scenarios">
        <legend className="br-label">Replay a recorded conversation</legend>
        {p.scenarios.map((s) => (
          <button
            key={s.id}
            type="button"
            aria-pressed={s.id === p.scenarioId}
            onClick={() => p.onScenario(s.id)}
            className="br-scenario"
          >
            <span className="br-kind" data-kind={s.kind}>
              {s.kind === "attack" ? "Attack" : "Honest"}
            </span>
            <span className="br-scn-title">{s.title}</span>
            <span className="br-scn-ask">{s.ask}</span>
          </button>
        ))}
      </fieldset>

      {isLive ? (
        <div className="br-live" data-busy={p.live.busy}>
          <span className="br-live-dot" aria-hidden="true" />
          <span>
            <b>Live conversation</b> · guard {p.guard ? "on" : "off"}
            {p.live.busy ? " · the agents are working" : ""}
          </span>
        </div>
      ) : (
      <div className="br-transport">
        <button type="button" onClick={p.onPlay} className="br-play" disabled={!p.file}>
          {p.playing ? <Pause className="h-4 w-4" aria-hidden="true" /> : <Play className="h-4 w-4" aria-hidden="true" />}
          {p.playing ? "Pause" : done ? "Replay" : p.step === 0 ? "Play" : "Resume"}
        </button>
        <button type="button" onClick={p.onRestart} className="br-icon" aria-label="Restart" disabled={!p.file}>
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
        </button>
        <div className="br-speed" role="group" aria-label="Speed">
          {[1, 2].map((s) => (
            <button key={s} type="button" aria-pressed={p.speed === s} onClick={() => p.onSpeed(s)}>
              {s}x
            </button>
          ))}
        </div>
        <div className="br-progress" aria-hidden="true">
          <i style={{ transform: `scaleX(${total ? p.step / total : 0})` }} />
        </div>
      </div>
      )}
      <p className="br-livehint">
        {p.live.on
          ? isLive
            ? "Pick a recorded conversation above to go back to the replays."
            : "Or type in the chat: the agents answer live on Muse and bylaw guards them."
          : "Live chat is off on this server; the recorded conversations show the same agents."}
      </p>

      <dl className="br-ledger">
        <div data-tone={p.moneyOut > 0 ? "out" : undefined}>
          <dt>Left the airline</dt>
          <dd>{usd(p.moneyOut)}</dd>
        </div>
        <div data-tone={p.moneyStopped > 0 ? "kept" : undefined}>
          <dt>Stopped by bylaw</dt>
          <dd>{p.stoppedUnpriced && p.moneyStopped === 0 ? "a payout" : usd(p.moneyStopped)}</dd>
        </div>
        <div>
          <dt>Checks</dt>
          <dd>
            {p.checks.length}
            {blocked > 0 && <span className="br-ledger-sub"> · {blocked} denied</span>}
          </dd>
        </div>
      </dl>

      {rules && (
        <div className="br-tabs" role="group" aria-label="Show">
          <button type="button" aria-pressed={!showRules} onClick={() => { setTab("checks"); setFocus(null); }}>
            Checks{started && <span className="br-tab-n">{p.checks.length}</span>}
          </button>
          <button type="button" aria-pressed={showRules} onClick={() => setTab("rules")}>
            Rules bylaw enforces
          </button>
        </div>
      )}

      {showRules ? (
        <div className="br-feed">
          <RulesList rules={rules} focus={focus} />
        </div>
      ) : (
      <div className="br-feed" ref={feed}>
        {p.error ? (
          <p className="br-empty br-error">{p.error}</p>
        ) : p.checks.length === 0 ? (
          <p className="br-empty">
            {isLive
              ? "Each tool call the agents make stops here first. Ask for something and watch."
              : p.step === 0
              ? `Press Play. The customer ${scenario?.ask.charAt(0).toLowerCase()}${scenario?.ask.slice(1)} Each tool call the agents make stops here first.`
              : "No tool call yet. bylaw speaks when an agent reaches for a tool."}
          </p>
        ) : (
          <ol className="br-steps">
            {p.checks.map((c, i) => (
              <CheckEntry
                key={i}
                c={c}
                latest={i === p.checks.length - 1}
                onRule={
                  ruleKey(rules, c.rule_id) && !c.allowed
                    ? () => {
                        setFocus(ruleKey(rules, c.rule_id));
                        setTab("rules");
                      }
                    : undefined
                }
              />
            ))}
          </ol>
        )}
        {done && (
          <p className="br-end">
            Conversation over.{" "}
            {p.moneyOut > 0
              ? `${usd(p.moneyOut)} in vouchers left the airline.`
              : p.moneyStopped > 0
                ? `Nothing was paid. Without bylaw, this agent paid ${usd(p.moneyStopped)} in the recorded run.`
                : "No money moved."}
          </p>
        )}
      </div>
      )}

      {isLive && p.live.status ? (
        <footer className="br-foot">
          Live · agents on <span className="br-muse">{p.live.status.model}</span> ·{" "}
          {p.live.status.tokens_used.toLocaleString("en-US")} of {p.live.status.token_cap.toLocaleString("en-US")} demo tokens used
        </footer>
      ) : (
        p.file && (
          <footer className="br-foot">
            Recorded {p.file.started.slice(0, 10)} · guard {p.file.guard ? "on" : "off"} · agents on{" "}
            <span className="br-muse">{p.file.model}</span>
          </footer>
        )
      )}
    </aside>
  );
}
