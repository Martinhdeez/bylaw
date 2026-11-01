"use client";

// Bylaw: a plain chat box in place of ChatKit (ChatKit loads from OpenAI's CDN and needs a domain allowlist).
// Same frame, header and start screen as the upstream ChatKitPanel.
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { ArrowUp } from "lucide-react";
import type { Message } from "@/lib/types";

const PROMPTS = [
  { label: "Change my seat", prompt: "Can you move me to seat 14C?" },
  { label: "Flight status", prompt: "What's the status of flight FLT-123?" },
  {
    label: "Missed connection",
    prompt:
      "My flight from Paris to New York was delayed and I missed my connection to Austin. Also, my checked bag is missing and I need to spend the night in New York. Can you help me?",
  },
];

interface ChatPanelProps {
  messages: Message[];
  typingAgent: string | null;
  replaying: boolean;
  onSend: (text: string) => void;
  liveNote: string | null;
}

export function ChatPanel({ messages, typingAgent, replaying, onSend, liveNote }: ChatPanelProps) {
  const [draft, setDraft] = useState("");
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: messages.length > 1 ? "smooth" : "auto" });
  }, [messages.length, typingAgent, liveNote]);

  const send = (text: string) => {
    const t = text.trim();
    if (!t || replaying) return;
    onSend(t);
    setDraft("");
  };

  return (
    <div className="flex flex-col h-full flex-1 min-w-0 bg-white shadow-sm border border-gray-200 border-t-0 rounded-xl max-md:h-[640px]">
      <div className="bg-blue-600 text-white h-12 px-4 flex items-center rounded-t-xl">
        <h2 className="font-semibold text-sm sm:text-base lg:text-lg">Customer View</h2>
      </div>

      <div ref={scroller} className="flex-1 overflow-y-auto px-5 py-4" aria-live="polite">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center gap-5">
            <p className="text-xl font-semibold text-zinc-900 max-w-[22ch]">
              Hi! I&apos;m your airline assistant. How can I help today?
            </p>
            <div className="flex flex-col gap-2 w-full max-w-sm">
              {PROMPTS.map((p) => (
                <button
                  key={p.label}
                  type="button"
                  onClick={() => send(p.prompt)}
                  disabled={replaying}
                  className="text-left text-sm rounded-full border border-gray-200 px-4 py-2 text-zinc-700 hover:bg-gray-50 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <ol className="flex flex-col gap-4">
            {messages.map((m) =>
              m.role === "user" ? (
                <li key={m.id} className="self-end max-w-[85%] rounded-2xl bg-gray-100 px-4 py-2 text-sm text-zinc-900 chat-in">
                  {m.content}
                </li>
              ) : (
                <li key={m.id} className="self-start max-w-[92%] chat-in">
                  <div className="text-[11px] text-zinc-500 mb-1">{m.agent}</div>
                  <div className="chat-md text-sm text-zinc-900 leading-relaxed">
                    <ReactMarkdown>{m.content}</ReactMarkdown>
                  </div>
                </li>
              )
            )}
            {liveNote && (
              <li className="self-stretch rounded-xl border border-dashed border-gray-300 px-4 py-3 text-xs text-zinc-600">
                {liveNote}
              </li>
            )}
            {typingAgent && (
              <li className="self-start flex items-center gap-2 text-xs text-zinc-500" aria-label={`${typingAgent} is working`}>
                <span className="typing-dots" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </span>
                {typingAgent}
              </li>
            )}
          </ol>
        )}
      </div>

      <form
        className="p-3 pt-0"
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
      >
        <div className="flex items-center gap-2 rounded-full border border-gray-200 bg-white pl-4 pr-1.5 py-1.5 shadow-sm focus-within:border-blue-600">
          <label htmlFor="composer" className="sr-only">
            Message
          </label>
          <input
            id="composer"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={replaying}
            placeholder={replaying ? "Replaying a recorded conversation…" : "Message…"}
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-zinc-400 disabled:cursor-not-allowed"
            autoComplete="off"
          />
          <button
            type="submit"
            disabled={replaying || !draft.trim()}
            aria-label="Send message"
            className="grid place-items-center h-8 w-8 rounded-full bg-blue-600 text-white disabled:bg-gray-200 disabled:text-gray-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
          >
            <ArrowUp className="h-4 w-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
