"use client";

import { Bot } from "lucide-react";
import type { Agent, AgentEvent, BylawCheck, GuardrailCheck } from "@/lib/types";
import { AgentsList } from "./agents-list";
import { Guardrails } from "./guardrails";
import { ConversationContext } from "./conversation-context";
import { RunnerOutput } from "./runner-output";

interface AgentPanelProps {
  agents: Agent[];
  currentAgent: string;
  events: AgentEvent[];
  guardrails: GuardrailCheck[];
  context: Record<string, any>;
  /** Bylaw */
  bylaw: { check: BylawCheck | null; guard: boolean; count: number };
  changedKeys: string[];
}

export function AgentPanel({
  agents,
  currentAgent,
  events,
  guardrails,
  context,
  bylaw,
  changedKeys,
}: AgentPanelProps) {
  const activeAgent = agents.find((a) => a.name === currentAgent);
  const runnerEvents = events.filter(
    (e) => e.type !== "message" && e.type !== "progress_update"
  );

  return (
    <div className="w-3/5 max-md:w-full max-md:h-auto h-full flex flex-col border-r border-gray-200 bg-white rounded-xl shadow-sm">
      <div className="bg-blue-600 text-white h-12 px-4 flex items-center gap-3 shadow-sm rounded-t-xl">
        <Bot className="h-5 w-5" />
        <h1 className="font-semibold text-sm sm:text-base lg:text-lg">
          Agent View
        </h1>
        <span className="ml-auto text-xs font-light tracking-wide opacity-80">
          Airline&nbsp;Co.
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-6 bg-gray-50/50">
        <AgentsList agents={agents} currentAgent={currentAgent} />
        {/* Bylaw: Guardrails moved above Conversation Context so the Bylaw card is in view at 1440x900 */}
        <Guardrails
          guardrails={guardrails}
          inputGuardrails={activeAgent?.input_guardrails ?? []}
          bylaw={bylaw}
        />
        <ConversationContext context={context} changedKeys={changedKeys} />
        <RunnerOutput runnerEvents={runnerEvents} />
      </div>
    </div>
  );
}
