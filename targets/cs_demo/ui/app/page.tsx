"use client";

// Bylaw: the demo's two panes, driven by a recorded event file instead of a ChatKit thread, plus the Bylaw rail.
import { useCallback, useEffect, useMemo, useState } from "react";
import { AgentPanel } from "@/components/agent-panel";
import { ChatPanel } from "@/components/chat-panel";
import { BylawRail } from "@/components/bylaw-rail";
import type { Agent, Message } from "@/lib/types";
import { AGENTS } from "@/lib/agents";
import { SCENARIOS, derive, fetchLiveFile, gapMs, type LiveFile } from "@/lib/replay";

const LIVE_NOTE =
  "Live typing is not wired in this prototype: Muse answers and Bylaw guards once the live endpoint exists. Pick a recorded conversation in the Bylaw rail to watch one.";

let stepUsed = false; // ?step= applies to the first file only

function param(name: string) {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get(name);
}

export default function Home() {
  const [agents] = useState<Agent[]>(AGENTS);
  const [scenarioId, setScenarioId] = useState("d1");
  const [guard, setGuard] = useState(true);
  const [file, setFile] = useState<LiveFile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [typed, setTyped] = useState<Message[]>([]);

  // ?scenario=d1&guard=off&speed=2&autoplay=1&step=12, for screenshots and recordings
  useEffect(() => {
    const s = param("scenario");
    if (s && SCENARIOS.some((x) => x.id === s)) setScenarioId(s);
    if (param("guard") === "off") setGuard(false);
    if (param("speed")) setSpeed(Number(param("speed")) || 1);
    if (param("autoplay") === "1") setPlaying(true);
  }, []);

  const scenario = SCENARIOS.find((s) => s.id === scenarioId)!;
  const fileName = guard ? scenario.files.on : scenario.files.off;

  useEffect(() => {
    let live = true;
    setFile(null);
    setError(null);
    fetchLiveFile(fileName)
      .then((f) => {
        if (!live) return;
        setFile(f);
        const s = Number(param("step"));
        if (s && !stepUsed) setStep(s === -1 ? f.events.length : Math.min(s, f.events.length));
        stepUsed = true;
      })
      .catch((e) => live && setError(String(e.message ?? e)));
    return () => {
      live = false;
    };
  }, [fileName]);

  useEffect(() => {
    if (!playing || !file) return;
    if (step >= file.events.length) {
      setPlaying(false);
      return;
    }
    const id = setTimeout(() => setStep((n) => n + 1), step === 0 ? 400 : gapMs(file, step - 1, speed));
    return () => clearTimeout(id);
  }, [playing, file, step, speed]);

  const view = useMemo(() => derive(file, step), [file, step]);

  const restart = useCallback((play: boolean) => {
    setTyped([]);
    setStep(0);
    setPlaying(play);
  }, []);

  const next = file?.events[step];
  const typingAgent = playing && next && next.type !== "user" ? view.currentAgent : null;
  const replaying = playing || (step > 0 && !!file && step < file.events.length);
  const messages = typed.length ? typed : view.messages;

  return (
    <main className="flex h-screen gap-2 bg-gray-100 p-2 max-md:h-auto max-md:flex-col">
      <div className="flex flex-1 min-w-0 gap-2 max-md:contents">
        <div className="contents max-md:block max-md:order-3">
          <AgentPanel
            agents={agents}
            currentAgent={view.currentAgent}
            events={view.events}
            guardrails={[]}
            context={view.context}
            bylaw={{ check: view.checks.at(-1) ?? null, guard, count: view.checks.length }}
            changedKeys={view.changedKeys}
          />
        </div>
        <div className="contents max-md:block max-md:order-1">
          <ChatPanel
            messages={messages}
            typingAgent={typed.length ? null : typingAgent}
            replaying={replaying}
            liveNote={typed.length ? LIVE_NOTE : null}
            onSend={(text) => {
              setStep(0);
              setPlaying(false);
              setTyped([{ id: "typed", role: "user", content: text, timestamp: new Date() }]);
            }}
          />
        </div>
      </div>
      <BylawRail
        scenarios={SCENARIOS}
        scenarioId={scenarioId}
        onScenario={(id) => {
          setScenarioId(id);
          restart(true);
        }}
        guard={guard}
        onGuard={(on) => {
          setGuard(on);
          restart(playing || step > 0);
        }}
        playing={playing}
        onPlay={() => {
          if (file && step >= file.events.length) restart(true);
          else {
            setTyped([]);
            setPlaying((p) => !p);
          }
        }}
        onRestart={() => restart(true)}
        speed={speed}
        onSpeed={setSpeed}
        file={file}
        step={step}
        checks={view.checks}
        moneyOut={view.moneyOut}
        moneyStopped={view.moneyStopped}
        error={error}
      />
    </main>
  );
}
