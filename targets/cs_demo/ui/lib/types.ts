export interface Message {
  id: string
  content: string
  role: "user" | "assistant"
  agent?: string
  timestamp: Date
}

export interface Agent {
  name: string
  description: string
  handoffs: string[]
  tools: string[]
  /** List of input guardrail identifiers for this agent */
  input_guardrails: string[]
}

export type EventType =
  | "message"
  | "handoff"
  | "tool_call"
  | "tool_output"
  | "context_update"
  | "progress_update"
  | "bylaw_check"

export interface AgentEvent {
  id: string
  type: EventType
  agent: string
  content: string
  timestamp: Date
  metadata?: {
    source_agent?: string
    target_agent?: string
    tool_name?: string
    tool_args?: Record<string, any>
    tool_result?: any
    context_key?: string
    context_value?: any
    changes?: Record<string, any>
    icon?: string
    /** Bylaw: present on bylaw_check events */
    check?: BylawCheck
  }
}

export interface GuardrailCheck {
  id: string
  name: string
  input: string
  reasoning: string
  passed: boolean
  timestamp: Date
}

/** Bylaw: one check of a tool call, as the CS-C3 event file records it, plus its plain-language narration. */
export interface BylawCheck {
  tool: string
  args: Record<string, any>
  allowed: boolean
  enforced: boolean
  rule_id: string | null
  policy_ref: string | null
  /** what the agent wants to do, in plain words */
  wants: string
  /** the facts the rules read, in plain words */
  reads: { label: string; value: string; ok: boolean }[]
  /** why it was denied, in plain words (null when allowed) */
  reason: string | null
  /** money that left the airline (positive) or was stopped (negative) by this call, in dollars */
  money: number
  readOnly: boolean
}
