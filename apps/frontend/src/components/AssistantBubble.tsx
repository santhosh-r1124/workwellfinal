import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import type { ChatMessage } from "../types";
import Icon from "./Icon";

const OPENERS = [
  "Why am I getting this notification?",
  "It's because of a release",
  "How can I protect focus time?",
];

export default function AssistantBubble() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hi — I can explain anything on your dashboard. Everything I say is grounded in your own detected pattern, never a guess about how you feel.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    setSending(true);
    try {
      const res = await api.chat(trimmed, sessionId);
      setSessionId(res.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.reply, sources: res.sources || [] },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "I couldn't reach the assistant just now. Please try again." },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      {open && (
        <div
          className="fixed z-40 flex flex-col overflow-hidden panel-raised animate-fade-up
                     inset-x-3 bottom-3 top-16
                     sm:inset-auto sm:bottom-24 sm:right-6 sm:top-auto sm:w-[380px] sm:h-[520px]"
          role="dialog"
          aria-label="WorkWell assistant"
        >
          <header className="flex items-center justify-between gap-3 px-4 py-3 border-b border-line-soft bg-surface-sunken">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-7 w-7 items-center justify-center rounded-lg bg-accent-ghost text-accent">
                <Icon name="spark" className="w-3.5 h-3.5" />
              </span>
              <div>
                <div className="text-[13px] font-semibold leading-tight">WorkWell assistant</div>
                <div className="text-[11px] text-text-faint leading-tight">
                  Grounded in your own pattern
                </div>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="rounded-md p-1.5 text-text-faint hover:text-text hover:bg-surface-raised"
              aria-label="Close assistant"
            >
              <Icon name="close" />
            </button>
          </header>

          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3.5 space-y-2.5">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[88%] rounded-xl px-3.5 py-2.5 text-[13px] leading-relaxed animate-fade-up ${
                  m.role === "user"
                    ? "ml-auto bg-accent-deep text-[#04121d]"
                    : "bg-surface-sunken border border-line-soft"
                }`}
              >
                <p className="whitespace-pre-wrap">{m.content}</p>
                {m.sources && m.sources.length > 0 && (
                  <p className="mt-2 pt-2 border-t border-line-soft text-[11px] text-text-faint">
                    {m.sources.map((s) => s.title).join(" · ")}
                  </p>
                )}
              </div>
            ))}

            {sending && (
              <div className="flex gap-1 px-1" aria-label="Assistant is typing">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-1.5 w-1.5 rounded-full bg-text-faint animate-bounce"
                    style={{ animationDelay: `${i * 120}ms` }}
                  />
                ))}
              </div>
            )}

            {messages.length === 1 && !sending && (
              <div className="pt-1 space-y-1.5">
                {OPENERS.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="block w-full text-left text-[12.5px] rounded-lg border border-line
                               bg-surface-sunken px-3 py-2 text-text-muted hover:text-text hover:bg-surface-raised"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex items-center gap-2 border-t border-line-soft bg-surface-sunken px-3 py-2.5"
          >
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your work pattern..."
              className="field text-[13px] py-1.5"
              aria-label="Message the assistant"
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              className="btn-primary flex items-center justify-center !px-2.5 !py-2"
              aria-label="Send message"
            >
              <Icon name="send" />
            </button>
          </form>
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-6 right-6 z-40 flex h-13 w-13 items-center justify-center rounded-full
                   bg-accent text-[#05131f] shadow-lg shadow-accent/20 hover:bg-sky-300 h-14 w-14"
        aria-label={open ? "Close assistant" : "Open assistant"}
        aria-expanded={open}
      >
        {!open && (
          <span className="absolute inset-0 rounded-full bg-accent/40 animate-pulse-ring" aria-hidden="true" />
        )}
        <Icon name={open ? "close" : "chat"} className="relative w-5 h-5" />
      </button>
    </>
  );
}
