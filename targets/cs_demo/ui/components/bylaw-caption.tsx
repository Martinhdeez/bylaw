"use client";

// Bylaw: the captions of the "Watch it" intro. Every number comes from the replayed event files.
import { useEffect } from "react";
import { RotateCcw, X } from "lucide-react";
import type { ReplayView } from "@/lib/replay";

export type Act = 1 | 2 | "end";

const usd = (n: number) => `$${n.toLocaleString("en-US")}`;

export function caption(act: Act, v: ReplayView, finished: boolean): string {
  const denied = [...v.checks].reverse().find((c) => !c.allowed);
  if (act === 1) {
    if (v.moneyOut > 0) return `${usd(v.moneyOut)} in vouchers just left the airline, for a flight that was on time.`;
    if (denied) return `bylaw sees it: ${denied.reason} But the guard is off, so it only watches.`;
    return "Guard off. On a flight that was on time, the customer asks for delay vouchers.";
  }
  if (act === 2) {
    if (finished || v.moneyStopped > 0)
      return `Blocked before it ran. Nothing was paid: ${usd(v.moneyStopped)} stayed with the airline.`;
    if (denied) return `Blocked before it ran. ${denied.reason}`;
    return "Same request, bylaw on. Every tool call stops at bylaw first.";
  }
  return "Same agents, same model. The model proposes; the application decides.";
}

interface Props {
  act: Act;
  text: string;
  onSkip: () => void;
  onAgain: () => void;
}

export function BylawCaption({ act, text, onSkip, onAgain }: Props) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onSkip();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onSkip]);

  return (
    <div className="bylaw-caption" role="region" aria-label="Intro" data-act={act}>
      <div className="bc-step">
        {act === "end" ? "bylaw" : act === 1 ? "1 of 2 · guard off" : "2 of 2 · guard on"}
      </div>
      <p className="bc-text" aria-live="polite" key={text}>
        {text}
      </p>
      <div className="bc-actions">
        {act === "end" ? (
          <>
            <button type="button" className="bc-btn" onClick={onAgain}>
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              Watch again
            </button>
            <button type="button" className="bc-btn bc-primary" onClick={onSkip}>
              Try it yourself
            </button>
          </>
        ) : (
          <button type="button" className="bc-btn" onClick={onSkip}>
            <X className="h-4 w-4" aria-hidden="true" />
            Skip intro
          </button>
        )}
      </div>
    </div>
  );
}
