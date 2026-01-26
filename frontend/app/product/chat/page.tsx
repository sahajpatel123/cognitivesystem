"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Action,
  FailClosedError,
  SafeChatResponse,
  validateChatRequest,
  validateChatResponse,
} from "./contract_runtime";
import {
  loadSession,
  persist as persistSession,
  startNewSession,
  SessionState,
  isExpired,
} from "./session_runtime";
import { SystemStatus } from "../../components/system-status";
import { UXState, clampCooldownSeconds, normalizeUxState } from "../../lib/ux_state";

type Message = {
  id: string;
  role: "user" | "system";
  text: string;
  action?: Action;
  failureType?: string | null;
};

const closedActions: Action[] = ["CLOSE", "REFUSE"];

type UiState = "IDLE" | "SENDING" | "TERMINAL" | "FAILED";

export default function ChatPage() {
  const apiBase = useMemo(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    try {
      const url = new URL(base);
      if (url.protocol !== "http:" && url.protocol !== "https:") {
        throw new FailClosedError("API base invalid protocol");
      }
      return base.replace(/\/$/, "");
    } catch {
      throw new FailClosedError("API base invalid");
    }
  }, []);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [lastUserText, setLastUserText] = useState<string | null>(null);
  const [uiState, setUiState] = useState<UiState>("IDLE");
  const uiStateRef = useRef<UiState>("IDLE");
  const [uxState, setUxState] = useState<UXState>("OK");
  const [cooldownSeconds, setCooldownSeconds] = useState<number | null>(null);
  const [cooldownEndsAtMs, setCooldownEndsAtMs] = useState<number | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [session, setSession] = useState<SessionState | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const listRef = useRef<HTMLDivElement | null>(null);
  const pendingRequestId = useRef(0);

  useEffect(() => {
    uiStateRef.current = uiState;
  }, [uiState]);

  useEffect(() => {
    if (!cooldownEndsAtMs) return;
    const id = setInterval(() => {
      const remainingMs = cooldownEndsAtMs - Date.now();
      const remainingSeconds = Math.max(0, Math.ceil(remainingMs / 1000));
      const clamped = clampCooldownSeconds(remainingSeconds);
      if (!clamped) {
        setCooldownSeconds(null);
        setCooldownEndsAtMs(null);
      } else {
        setCooldownSeconds(clamped);
      }
    }, 1000);
    return () => clearInterval(id);
  }, [cooldownEndsAtMs]);

  useEffect(() => {
    const restored = loadSession();
    setSession(restored.session);
    setMessages(restored.messages);
    const lastUser = [...restored.messages].reverse().find((m) => m.role === "user");
    if (lastUser) setLastUserText(lastUser.text);
    const lastSystem = [...restored.messages].reverse().find((m) => m.role === "system");
    if (lastSystem && (lastSystem.action === "REFUSE" || lastSystem.action === "CLOSE")) {
      setUiState("TERMINAL");
    } else if (lastSystem && lastSystem.action === "FALLBACK") {
      setUiState("FAILED");
    }
  }, []);

  useEffect(() => {
    if (session) {
      persistSession(session, messages);
    }
  }, [messages, session]);

  const lastSystemAction = useMemo(() => {
    const sys = [...messages].reverse().find((m) => m.role === "system");
    return sys?.action;
  }, [messages]);

  const cooldownActive = !!(cooldownSeconds && cooldownSeconds > 0);
  const inputDisabled =
    uiState === "SENDING" ||
    uiState === "TERMINAL" ||
    (lastSystemAction && closedActions.includes(lastSystemAction)) ||
    cooldownActive;
  const sendDisabled = inputDisabled || cooldownActive || input.trim().length === 0;

  const remainingMinutes = useMemo(() => {
    if (!session) return null;
    const remainingMs = session.expiresAt - Date.now();
    return Math.max(0, Math.ceil(remainingMs / 60000));
  }, [session]);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  const pushSystemMessage = (text: string, action: Action, failureType?: string | null) => {
    const sysMsg: Message = {
      id: crypto.randomUUID(),
      role: "system",
      text,
      action,
      failureType: failureType ?? null,
    };
    setMessages((prev) => [...prev, sysMsg]);
  };

  const beginNewSession = () => {
    const fresh = startNewSession();
    setSession(fresh.session);
    setMessages([]);
    setLastUserText(null);
    setUiState("IDLE");
    setSessionExpired(false);
    pendingRequestId.current = pendingRequestId.current + 1;
  };

  const sendMessage = async (text: string, allowWhenFailed = false) => {
    if (!session) {
      beginNewSession();
    }
    const activeSession = session;
    if (activeSession && isExpired(activeSession)) {
      setSessionExpired(true);
      beginNewSession();
    }
    if (uiState !== "IDLE" && !(allowWhenFailed && uiState === "FAILED")) return;

    let requestBody;
    try {
      requestBody = validateChatRequest(text);
    } catch (err) {
      pushSystemMessage("Request failed. Please retry.", "FALLBACK");
      setUiState("FAILED");
      return;
    }

    const trimmed = requestBody.user_text;
    setLastUserText(trimmed);
    const userMsg: Message = { id: crypto.randomUUID(), role: "user", text: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setUiState("SENDING");
    const currentRequestId = pendingRequestId.current + 1;
    pendingRequestId.current = currentRequestId;
    try {
      const res = await fetch(`${apiBase}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      const hdrUx = res.headers.get("X-UX-State") || res.headers.get("x-ux-state");
      const hdrCd = res.headers.get("X-Cooldown-Seconds") || res.headers.get("x-cooldown-seconds");
      const hdrRid = res.headers.get("X-Request-Id") || res.headers.get("x-request-id");
      const newUx = normalizeUxState(hdrUx);
      const newCooldown = clampCooldownSeconds(hdrCd ? Number(hdrCd) : null);
      setUxState(newUx);
      setRequestId(hdrRid);
      if (newCooldown) {
        setCooldownSeconds(newCooldown);
        setCooldownEndsAtMs(Date.now() + newCooldown * 1000);
      } else {
        setCooldownSeconds(null);
        setCooldownEndsAtMs(null);
      }
      if (!res.ok) {
        let friendly = "Request failed. Please retry.";
        if (res.status === 415) {
          friendly = "Content type not supported. Use application/json.";
        } else if (res.status === 429) {
          friendly = "Rate limit or quota reached. Please wait and try again.";
        } else if (res.status >= 500) {
          friendly = "Service is unavailable right now. Please try again.";
        }
        pushSystemMessage(friendly, "FALLBACK");
        setUiState("FAILED");
        return;
      }
      const raw = await res.json();
      if (pendingRequestId.current !== currentRequestId) {
        return;
      }
      const data: SafeChatResponse = validateChatResponse(raw);
      const action = data.action;
      pushSystemMessage(data.rendered_text, action, data.failure_type ?? null);
      if (action === "REFUSE" || action === "CLOSE") {
        setUiState("TERMINAL");
      } else if (action === "FALLBACK") {
        setUiState("FAILED");
      } else {
        setUiState("IDLE");
      }
    } catch (err) {
      if (pendingRequestId.current !== currentRequestId) {
        return;
      }
      pushSystemMessage("Request failed. Please retry.", "FALLBACK");
      setUiState("FAILED");
    } finally {
      if (pendingRequestId.current !== currentRequestId) {
        return;
      }
      if (uiStateRef.current === "SENDING") {
        // handlers set final state; no override
      }
    }
  };

  const resetChat = () => {
    if (session) persistSession(session, []);
    setMessages([]);
    setInput("");
    setLastUserText(null);
    setUiState("IDLE");
    setSessionExpired(false);
    pendingRequestId.current = pendingRequestId.current + 1;
  };

  const retryLast = () => {
    if (uiState !== "FAILED" || !lastUserText) return;
    setUiState("IDLE");
    void sendMessage(lastUserText, true);
  };

  const copyLastResponse = async () => {
    const lastSystem = [...messages].reverse().find((m) => m.role === "system");
    if (!lastSystem) return;
    try {
      await navigator.clipboard?.writeText(lastSystem.text);
    } catch {
      pushSystemMessage("Copy failed locally.", "FALLBACK");
    }
  };

  const copyTranscript = async () => {
    if (!messages.length) return;
    const text = messages.map((m) => `${m.role.toUpperCase()}: ${m.text}`).join("\n\n");
    try {
      await navigator.clipboard?.writeText(text);
    } catch {
      pushSystemMessage("Copy failed locally.", "FALLBACK");
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!inputDisabled) {
      void sendMessage(input);
    }
  };

  const renderBadge = (action?: Action) => {
    if (!action) return null;
    return <span className="chat-badge">{action}</span>;
  };

  const lastSystem = useMemo(() => [...messages].reverse().find((m) => m.role === "system"), [messages]);
  const statusLabel = uiState === "TERMINAL" ? "TERMINAL" : uiState === "FAILED" ? "FAILED" : uiState === "SENDING" ? "SENDING" : "IDLE";
  const truncatedRid = requestId ? requestId.slice(-8) : null;
  const failureLabel = lastSystem?.failureType ? lastSystem.failureType : "NONE";
  const actionLabel = lastSystem?.action ?? "—";

  const closed = uiState === "TERMINAL" || (lastSystemAction && closedActions.includes(lastSystemAction));

  return (
    <div className="page-frame">
      <div className="section-header">
        <span className="eyebrow">Governed chat</span>
        <h1>Text-in / text-out, tool-only.</h1>
        <p>All responses flow through the certified governance pipeline. No retries, no bypasses.</p>
        <div className="chat-disclaimer" role="note">
          <p>Not medical, legal, or financial advice. Verify independently. We may enforce rate limits and quotas to prevent abuse.</p>
        </div>
        {process.env.NEXT_PUBLIC_ENV !== "production" && (
          <div className="env-banner" role="status">
            DEV MODE — Using {process.env.NEXT_PUBLIC_API_BASE_URL ?? "unset"} as API base
          </div>
        )}
      </div>

      <div className="chat-shell">
        <SystemStatus
          uxState={uxState}
          cooldownSeconds={cooldownSeconds}
          requestId={requestId}
          onRetry={lastUserText ? () => void sendMessage(lastUserText, true) : undefined}
        />
        <div className="state-strip" aria-label="System state">
          <span>Action: {actionLabel}</span>
          <span>Status: {statusLabel}</span>
          <span>Failure: {failureLabel}</span>
          <span>Session: {sessionExpired ? "EXPIRED" : "ACTIVE"}</span>
          {remainingMinutes !== null && <span>TTL: {remainingMinutes}m</span>}
          {truncatedRid ? (
            <button
              type="button"
              className="rid-copy"
              onClick={() => {
                if (requestId) {
                  void navigator.clipboard?.writeText(requestId);
                }
              }}
              aria-label="Copy request id"
            >
              Req ID …{truncatedRid}
            </button>
          ) : null}
        </div>
        <div className="chat-messages" ref={listRef} aria-live="polite">
          {messages.length === 0 && <div className="chat-empty">Send a message to begin.</div>}
          {messages.map((msg) => (
            <div key={msg.id} className={`chat-row ${msg.role}`}>
              <div className="chat-meta">
                <span className="chat-role">{msg.role === "user" ? "You" : "System"}</span>
                {renderBadge(msg.action)}
              </div>
              <div className="chat-bubble">
                <p className="chat-text">{msg.text}</p>
                {msg.failureType && <span className="chat-note">Failure: {msg.failureType}</span>}
              </div>
            </div>
          ))}
          {closed && <div className="chat-note closed-note">Conversation closed.</div>}
        </div>

        <form className="chat-input-row" onSubmit={handleSubmit}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (!sendDisabled) {
                  void sendMessage(input);
                }
              }
            }}
            placeholder={inputDisabled ? "Interaction closed" : "Type a governed prompt..."}
            disabled={inputDisabled}
          />
          <button type="submit" disabled={sendDisabled}>
            {uiState === "SENDING" ? "Sending..." : "Send"}
          </button>
        </form>
        {uiState === "FAILED" && <div className="chat-note limit-note">Session encountered a failure; you may retry.</div>}
        {closed && <div className="chat-note closed-note">This session is closed by the system’s governance rules.</div>}
        {sessionExpired && <div className="chat-note closed-note">Session expired. Start a new session to continue.</div>}
        <div className="chat-controls">
          <button type="button" onClick={resetChat}>
            Reset chat
          </button>
          <button type="button" onClick={retryLast} disabled={uiState !== "FAILED" || !lastUserText}>
            Retry last
          </button>
          <button type="button" onClick={copyLastResponse} disabled={!messages.some((m) => m.role === "system")}>
            Copy last response
          </button>
          <button type="button" onClick={copyTranscript} disabled={messages.length === 0}>
            Copy conversation
          </button>
          <button type="button" onClick={beginNewSession}>
            New session
          </button>
        </div>
      </div>

      <style jsx>{`
        .chat-shell {
          border: 1px solid #1f2937;
          border-radius: 16px;
          background: #0b0f1a;
          min-height: 520px;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .chat-messages {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          display: grid;
          gap: 12px;
        }
        .state-strip {
          display: flex;
          gap: 12px;
          padding: 10px 16px;
          border-bottom: 1px solid #1f2937;
          background: #0d1320;
          color: #cbd5e1;
          font-size: 12px;
          flex-wrap: wrap;
        }
        .state-strip .rid-copy {
          border: 1px solid #1f2937;
          background: #0f172a;
          color: #e5e7eb;
          border-radius: 8px;
          padding: 4px 8px;
          font-size: 12px;
        }
        .state-strip .rid-copy:hover {
          background: #111827;
        }
        .chat-row {
          display: grid;
          gap: 6px;
        }
        .chat-row.user .chat-bubble {
          background: #111827;
          align-self: start;
        }
        .chat-row.system .chat-bubble {
          background: #0d1930;
        }
        .chat-meta {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          color: #9ca3af;
        }
        .chat-role {
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .chat-bubble {
          border-radius: 12px;
          padding: 12px 14px;
          border: 1px solid #1f2937;
          color: #e5e7eb;
          line-height: 1.45;
        }
        .chat-text {
          white-space: pre-wrap;
          margin: 0;
        }
        .chat-badge {
          display: inline-flex;
          align-items: center;
          padding: 2px 8px;
          border-radius: 9999px;
          border: 1px solid #374151;
          color: #cbd5e1;
          font-size: 11px;
          letter-spacing: 0.04em;
        }
        .chat-note {
          display: block;
          margin-top: 6px;
          font-size: 12px;
          color: #fbbf24;
        }
        .closed-note {
          color: #9ca3af;
        }
        .chat-empty {
          text-align: center;
          color: #9ca3af;
          padding: 24px 0;
        }
        .chat-input-row {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 10px;
          padding: 12px 16px;
          border-top: 1px solid #1f2937;
          background: #0b0f1a;
        }
        .chat-input-row input {
          width: 100%;
          border-radius: 10px;
          border: 1px solid #1f2937;
          background: #0d1320;
          color: #e5e7eb;
          padding: 10px 12px;
        }
        .chat-input-row button {
          border-radius: 10px;
          border: 1px solid #2563eb;
          background: #1d4ed8;
          color: #e5e7eb;
          padding: 10px 14px;
        }
        .chat-input-row button:disabled,
        .chat-input-row input:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .limit-note {
          padding: 6px 16px 12px;
        }
        .chat-controls {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          padding: 10px 16px 0;
        }
        .chat-controls button {
          border-radius: 10px;
          border: 1px solid #1f2937;
          background: #0d1320;
          color: #e5e7eb;
          padding: 8px 10px;
        }
        .chat-controls button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .chat-disclaimer {
          margin-top: 8px;
          padding: 10px 12px;
          border: 1px solid #1f2937;
          border-radius: 10px;
          background: #0d1320;
          color: #cbd5e1;
          font-size: 13px;
        }
      `}</style>
    </div>
  );
}
