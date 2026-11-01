"use client";

// Bylaw: the demo's two panes, driven by a recorded event file (replay) or by the live chat (VZ3 contract C2),
// plus the Bylaw rail and the "Watch it" intro.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AgentPanel } from "@/components/agent-panel";
import { ChatPanel } from "@/components/chat-panel";
import { BylawRail } from "@/components/bylaw-rail";
import { BylawCaption, caption, type Act } from "@/components/bylaw-caption";
import type { Agent } from "@/lib/types";
import { AGENTS } from "@/lib/agents";
import { SCENARIOS, derive, fetchLiveFile, gapMs, type LiveEvent, type LiveFile } from "@/lib/replay";
import { createSession, explain, fetchAgents, fetchStatus, sendTurn, type LiveStatus } from "@/lib/live";

const INTRO_KEY = "bylaw-intro-seen";
const INTRO_SPEED = 1.5;
let stepUsed = false; // ?step= applies to the first file only

function param(name: string) {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get(name);
}

function storage(read: boolean) {
  try {
    if (read) return window.localStorage.getItem(INTRO_KEY);
    window.localStorage.setItem(INTRO_KEY, "1");
  } catch {}
  return null;
}

/** Index of the second customer turn: the intro starts there, after the flight-status small talk. */
function secondTurn(f: LiveFile) {
  const users = f.events.flatMap((e, i) => (e.type === "user" ? [i] : []));
  return users[1] ?? 0;
}

export default function Home() {
  const [agents, setAgents] = useState<Agent[]>(AGENTS);
  const [mode, setMode] = useState<"replay" | "live">("replay");
  const [scenarioId, setScenarioId] = useState("d1");
  const [guard, setGuard] = useState(true);
  const [file, setFile] = useState<LiveFile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [act, setAct] = useState<Act | null>(null);
  const positioned = useRef<Act | null>(null);

  // live chat (C2, C6)
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const [session, setSession] = useState<{ id: string; guard: boolean } | null>(null);
  const [live, setLive] = useState<LiveFile | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [liveBlocked, setLiveBlocked] = useState(false); // a 503 or the token cap holds until reload
  const liveOn = !liveBlocked && !!status?.enabled && status.tokens_used < status.token_cap;

  useEffect(() => {
    const s = param("scenario");
    if (s && SCENARIOS.some((x) => x.id === s)) setScenarioId(s);
    if (param("guard") === "off") setGuard(false);
    if (param("speed")) setSpeed(Number(param("speed")) || 1);
    if (param("autoplay") === "1") setPlaying(true);
    const tour = param("tour");
    if (tour === "1" || (tour !== "0" && !param("scenario") && !storage(true))) {
      const id = setTimeout(() => startIntro(), 900);
      return () => clearTimeout(id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void fetchStatus().then(setStatus);
    void fetchAgents().then((a) => a && setAgents(a));
  }, []);

  const scenario = SCENARIOS.find((s) => s.id === scenarioId)!;
  const fileName = guard ? scenario.files.on : scenario.files.off;

  useEffect(() => {
    let alive = true;
    setFile(null);
    setError(null);
    fetchLiveFile(fileName)
      .then((f) => {
        if (!alive) return;
        setFile(f);
        const s = Number(param("step"));
        if (s && !stepUsed) setStep(s === -1 ? f.events.length : Math.min(s, f.events.length));
        stepUsed = true;
      })
      .catch((e) => alive && setError(String(e.message ?? e)));
    return () => {
      alive = false;
    };
  }, [fileName]);

  // the intro: once the act's file is loaded, jump to the second customer turn and play
  useEffect(() => {
    if ((act === 1 || act === 2) && file && positioned.current !== act && file.guard === (act === 2)) {
      positioned.current = act;
      setStep(secondTurn(file));
      setPlaying(true);
    }
  }, [act, file]);

  // replay clock
  useEffect(() => {
    if (mode !== "replay" || !playing || !file) return;
    if (step >= file.events.length) {
      setPlaying(false);
      return;
    }
    const id = setTimeout(() => setStep((n) => n + 1), step === 0 ? 400 : gapMs(file, step - 1, speed));
    return () => clearTimeout(id);
  }, [mode, playing, file, step, speed]);

  const finished = !!file && step >= file.events.length;

  // the intro moves on when an act's conversation ends
  useEffect(() => {
    if (!finished || positioned.current !== act) return;
    if (act === 1) {
      const id = setTimeout(() => {
        setAct(2);
        setGuard(true);
      }, 3000);
      return () => clearTimeout(id);
    }
    if (act === 2) {
      const id = setTimeout(() => setAct("end"), 3500);
      return () => clearTimeout(id);
    }
  }, [finished, act]);

  const startIntro = useCallback(() => {
    storage(false);
    positioned.current = null;
    setMode("replay");
    setNote(null);
    setScenarioId("d1");
    setGuard(false);
    setSpeed(INTRO_SPEED);
    setPlaying(false);
    setAct(1);
  }, []);

  const endIntro = useCallback(() => {
    setAct((a) => {
      if (a !== null) setSpeed(1); // leave the intro's speed behind, keep a speed the viewer chose
      return null;
    });
    positioned.current = null;
  }, []);

  const restart = useCallback((play: boolean) => {
    setMode("replay");
    setNote(null);
    setStep(0);
    setPlaying(play);
  }, []);

  const send = async (text: string) => {
    if (!liveOn || busy) return;
    endIntro();
    setMode("live");
    setPlaying(false);
    setNote(null);
    setBusy(true);
    try {
      let s = session;
      let base = live;
      if (!s || s.guard !== guard) {
        const created = await createSession(guard);
        s = { id: created.session, guard: created.guard };
        setSession(s);
        base = { name: `live-${created.session}`, guard: created.guard, model: created.model, started: new Date().toISOString(), events: [], final_state: {} };
      }
      const t0 = base!.events.at(-1)?.t ?? 0;
      const mine: LiveEvent = { t: t0, type: "user", text };
      setLive({ ...base!, events: [...base!.events, mine] });
      let echoed = false;
      await sendTurn(s.id, text, {
        onEvent: (e) => {
          if (e.type === "user" && !echoed && e.text === text) {
            echoed = true; // the server's copy of the message already shown
            return;
          }
          setLive((f) => (f ? { ...f, events: [...f.events, e] } : f));
        },
        onDone: () => undefined,
        onError: (message) => setNote(message),
      });
    } catch (err) {
      const why = explain(err);
      setNote(why.text);
      if (why.liveOff) setLiveBlocked(true);
      if (why.newSession) setSession(null);
    } finally {
      setBusy(false);
      void fetchStatus().then((st) => st && setStatus(st));
    }
  };

  const shown = mode === "live" ? live : file;
  const view = useMemo(
    () => (mode === "live" ? derive(live, live?.events.length ?? 0) : derive(file, step)),
    [mode, live, file, step]
  );

  const next = file?.events[step];
  const typingAgent =
    mode === "live" ? (busy ? view.currentAgent : null) : playing && next && next.type !== "user" ? view.currentAgent : null;
  const replaying = mode === "replay" && (playing || (step > 0 && !!file && step < file.events.length));
  const inChat = mode === "live" && (live?.events.length ?? 0) > 0;

  const placeholder = !liveOn
    ? "Live chat is off. Watch a replay."
    : busy
      ? "The agents are answering…"
      : replaying
        ? "Replaying a recorded conversation…"
        : `Message… (live on ${status?.model ?? "Muse"}, guard ${guard ? "on" : "off"})`;

  const pickScenario = (id: string) => {
    endIntro();
    setScenarioId(id);
    restart(true);
  };

  return (
    <main className="flex h-screen gap-2 bg-gray-100 p-2 max-xl:h-auto max-xl:flex-wrap max-md:flex-col">
      <div className="flex flex-1 min-w-0 gap-2 max-xl:contents">
        <div className="contents max-xl:block max-xl:order-3 max-xl:w-full">
          <AgentPanel
            agents={agents}
            currentAgent={view.currentAgent}
            events={view.events}
            guardrails={view.guardrails}
            context={view.context}
            bylaw={{ check: view.checks.at(-1) ?? null, guard: mode === "live" && session ? session.guard : guard, count: view.checks.length }}
            changedKeys={view.changedKeys}
          />
        </div>
        <div className="contents max-xl:block max-xl:order-1 max-xl:flex-1 max-xl:min-w-0 max-xl:h-[760px] max-md:h-[640px]">
          <ChatPanel
            messages={mode === "live" && !inChat ? [] : view.messages}
            typingAgent={typingAgent}
            disabled={!liveOn || busy || replaying || act === 1 || act === 2}
            placeholder={placeholder}
            note={note}
            onSend={(t) => void send(t)}
            replays={liveOn ? null : SCENARIOS.map((s) => ({ label: `Watch: ${s.title}`, onClick: () => pickScenario(s.id) }))}
          />
        </div>
      </div>
      <BylawRail
        scenarios={SCENARIOS}
        scenarioId={mode === "live" ? "" : scenarioId}
        onScenario={pickScenario}
        guard={guard}
        onGuard={(on) => {
          endIntro();
          setGuard(on);
          if (mode === "live") {
            setSession(null);
            setLive(null);
            setNote(`Guard ${on ? "on" : "off"}. Your next message starts a new conversation.`);
          } else restart(playing || step > 0);
        }}
        mode={mode}
        live={{ on: liveOn, status, busy }}
        playing={playing}
        onPlay={() => {
          endIntro();
          if (mode === "live" || finished) restart(true);
          else setPlaying((p) => !p);
        }}
        onRestart={() => {
          endIntro();
          restart(true);
        }}
        onWatch={startIntro}
        speed={speed}
        onSpeed={setSpeed}
        file={shown}
        step={mode === "live" ? live?.events.length ?? 0 : step}
        checks={view.checks}
        moneyOut={view.moneyOut}
        moneyStopped={view.moneyStopped}
        error={mode === "replay" ? error : null}
      />
      {act !== null && (
        <BylawCaption
          act={act}
          text={caption(act, view, finished)}
          onSkip={endIntro}
          onAgain={startIntro}
        />
      )}
    </main>
  );
}
