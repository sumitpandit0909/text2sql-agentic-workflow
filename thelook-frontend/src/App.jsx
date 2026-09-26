import { useEffect, useRef, useState } from "react";
import ChartRenderer from "./ChartRenderer.jsx";

function newId() {
  return crypto.randomUUID();
}

export default function App() {
  const [sessionId, setSessionId] = useState(() => newId());
  const [userId, setUserId] = useState("dev-user");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]); // {id, role, kind, content, chart, statusTrail}
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || busy) return;

    const userMsg = { id: newId(), role: "user", kind: "text", content: text };
    const agentMsgId = newId();
    setMessages((m) => [
      ...m,
      userMsg,
      { id: agentMsgId, role: "agent", kind: "pending", content: "", chart: null, statusTrail: [] },
    ]);
    setInput("");
    setBusy(true);

    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, user_id: userId, message: text }),
      });
      if (!res.ok || !res.body) throw new Error(`Request failed: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop(); // last (possibly incomplete) line stays in buffer

        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line);
          applyEvent(agentMsgId, event);
        }
      }
    } catch (err) {
      applyEvent(agentMsgId, { type: "text", content: `[Error: ${err.message}]` });
    } finally {
      setBusy(false);
    }
  }

  function applyEvent(agentMsgId, event) {
    setMessages((prev) =>
      prev.map((m) => {
        if (m.id !== agentMsgId) return m;
        if (event.type === "status") {
          return { ...m, kind: "pending", statusTrail: [...m.statusTrail, event.message] };
        }
        if (event.type === "chart") {
          return { ...m, kind: "final", chart: event.chart };
        }
        if (event.type === "text") {
          return { ...m, kind: "final", content: (m.content || "") + event.content };
        }
        return m;
      })
    );
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="console">
      <header className="console-header">
        <div className="console-title">
          <span className="dot" />
          TheLook Data Intelligence — Console
        </div>
        <div className="console-meta">
          <label>
            user_id
            <input value={userId} onChange={(e) => setUserId(e.target.value)} />
          </label>
          <label>
            session_id
            <input value={sessionId} readOnly />
          </label>
          <button className="ghost-btn" onClick={() => setSessionId(newId())}>
            New session
          </button>
        </div>
      </header>

      <main className="thread" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="empty-state">
            Ask about revenue, orders, forecasts, or request a chart — the agent
            decides which workflow to use.
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`bubble-row ${m.role}`}>
            <div className={`bubble ${m.role}`}>
              {m.role === "agent" && m.statusTrail.length > 0 && m.kind === "pending" && (
                <div className="status-trail">
                  {m.statusTrail.map((s, i) => (
                    <div key={i} className="status-line">
                      {s}
                    </div>
                  ))}
                </div>
              )}
              {m.content && <div className="bubble-text">{m.content}</div>}
              {m.chart && <ChartRenderer config={m.chart} />}
              {m.kind === "pending" && !m.content && m.statusTrail.length === 0 && (
                <span className="typing-dots">
                  <span /><span /><span />
                </span>
              )}
            </div>
          </div>
        ))}
      </main>

      <footer className="composer">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. What is total revenue by product category?"
          rows={1}
        />
        <button onClick={sendMessage} disabled={busy || !input.trim()}>
          Send
        </button>
      </footer>
    </div>
  );
}
