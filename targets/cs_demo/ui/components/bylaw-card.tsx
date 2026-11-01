"use client";

// Bylaw: a third card in the demo's Guardrails grid. Same card frame as Relevance and Jailbreak,
// Bylaw's own mark and colours for its verdict.
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CheckCircle, XCircle, CircleDashed, AlertTriangle } from "lucide-react";
import type { BylawCheck } from "@/lib/types";
import { BylawMark } from "./bylaw-mark";

interface BylawCardProps {
  check: BylawCheck | null;
  guard: boolean;
  count: number;
}

export function BylawCard({ check, guard, count }: BylawCardProps) {
  const state = !check ? "idle" : check.allowed ? "allowed" : check.enforced ? "blocked" : "would-block";
  return (
    <Card className="bylaw-card bg-white transition-all" data-state={state} aria-live="polite">
      <CardHeader className="p-3 pb-1">
        <CardTitle className="text-sm flex items-center gap-1.5 text-zinc-900">
          <BylawMark className="h-4 w-4" />
          Bylaw
          <span className="bylaw-card-mode">{guard ? "enforcing" : "watching only"}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-3 pt-1">
        <p className="text-xs font-light text-zinc-500 mb-1">
          {state === "idle"
            ? "Checks every tool call against the ratified policy before it runs"
            : state === "blocked" || state === "would-block"
              ? check!.reason
              : `${check!.wants}. ${count} call${count === 1 ? "" : "s"} checked.`}
        </p>
        <div className="flex text-xs">
          {state === "idle" && (
            <span className="bylaw-badge" data-tone="idle">
              <CircleDashed className="h-4 w-4" aria-hidden="true" />
              Waiting for a tool call
            </span>
          )}
          {state === "allowed" && (
            <span className="bylaw-badge" data-tone="green">
              <CheckCircle className="h-4 w-4" aria-hidden="true" />
              Allowed
            </span>
          )}
          {state === "blocked" && (
            <span className="bylaw-badge" data-tone="red">
              <XCircle className="h-4 w-4" aria-hidden="true" />
              Blocked
            </span>
          )}
          {state === "would-block" && (
            <span className="bylaw-badge" data-tone="amber">
              <AlertTriangle className="h-4 w-4" aria-hidden="true" />
              Would block
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
