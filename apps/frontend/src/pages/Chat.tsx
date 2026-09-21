import { useState } from "react";

import { api } from "../api/client";
import type { ChatMessage } from "../types";

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Hi, I'm the WorkWell assistant. Ask me about a recent notification or how things have been going.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const send = async () => {
    if (!input.trim() || sending) return;
    const userMessage: ChatMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSending(true);
    try {
      const res = await api.chat(userMessage.content, sessionId);
      setSessionId(res.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply, sources: res.sources || [] }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Something went wrong reaching the assistant." }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 flex flex-col h-[calc(100vh-64px)]">
      <h1 className="text-xl font-semibold text-white mb-4">WorkWell Assistant</h1>
      <div className="flex-1 overflow-y-auto space-y-3 mb-4">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
              m.role === "user" ? "ml-auto bg-sky-600 text-white" : "bg-slate-800 text-slate-200"
            }`}
          >
            <p className="whitespace-pre-wrap">{m.content}</p>
            {m.sources && m.sources.length > 0 && (
              <p className="text-xs text-slate-400 mt-2">Sources: {m.sources.map((s) => s.title).join(", ")}</p>
            )}
          </div>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your work pattern..."
          className="flex-1 px-3 py-2 rounded-md bg-slate-800 border border-slate-700 text-white"
        />
        <button
          type="submit"
          disabled={sending}
          className="px-4 py-2 rounded-md bg-sky-500 hover:bg-sky-400 disabled:opacity-50 text-slate-950 font-medium"
        >
          Send
        </button>
      </form>
    </div>
  );
}
