"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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
import { UXState, clampCooldownSeconds, normalizeUxState } from "../../../lib/ux_state";
import {
  ChatSidebar,
  ChatMessage,
  ChatComposer,
  ChatActionsMenu,
  ChatSession,
  loadChatSessions,
  saveChatSessions,
  getCurrentSessionId,
  setCurrentSessionId,
  createSessionTitle,
  addOrUpdateSession,
  deleteSession as deleteStoredSession,
  getSessionById,
} from "./_components";
import "./chatgpt.css";

type Message = {
  id: string;
  role: "user" | "system";
  text: string;
  action?: Action;
  failureType?: string | null;
};

const closedActions: Action[] = ["CLOSE", "REFUSE", "BLOCK"];

type UiState = "IDLE" | "SENDING" | "TERMINAL" | "FAILED";

export default function ChatPage() {
  const apiBase = useMemo(() => {
    const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
    const isProd = process.env.NEXT_PUBLIC_ENV === "production";
    // In production, NEXT_PUBLIC_API_BASE_URL is required - fail closed
    if (isProd && !raw) {
      throw new FailClosedError("NEXT_PUBLIC_API_BASE_URL required in production");
    }
    const base = raw ?? "http://localhost:8000";
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
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentChatSessionId, setCurrentChatSessionId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);
  const pendingRequestId = useRef(0);

  // Transport debug state (dev-only, no user text)
  const [transportDebug, setTransportDebug] = useState<{
    lastUrl: string | null;
    lastStatus: number | null;
    lastRequestId: string | null;
    lastUxState: string | null;
    lastError: string | null;
  }>({ lastUrl: null, lastStatus: null, lastRequestId: null, lastUxState: null, lastError: null });
  const debugTransport = process.env.NEXT_PUBLIC_DEBUG_TRANSPORT === "1";

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
    const sessions = loadChatSessions();
    setChatSessions(sessions);
    const currentId = getCurrentSessionId();
    if (currentId) {
      const currentSession = getSessionById(currentId);
      if (currentSession) {
        setCurrentChatSessionId(currentId);
        setMessages(currentSession.messages);
        const lastUser = [...currentSession.messages].reverse().find((m) => m.role === "user");
        if (lastUser) setLastUserText(lastUser.text);
        const lastSystem = [...currentSession.messages].reverse().find((m) => m.role === "system");
        if (lastSystem && (lastSystem.action === "REFUSE" || lastSystem.action === "CLOSE")) {
          setUiState("TERMINAL");
        } else if (lastSystem && lastSystem.action === "FALLBACK") {
          setUiState("FAILED");
        }
      }
    }
    const restored = loadSession();
    setSession(restored.session);
  }, []);

  useEffect(() => {
    if (session) {
      persistSession(session, messages);
    }
    if (currentChatSessionId && messages.length > 0) {
      const firstUserMsg = messages.find((m) => m.role === "user");
      const title = firstUserMsg ? createSessionTitle(firstUserMsg.text) : "New chat";
      const chatSession: ChatSession = {
        id: currentChatSessionId,
        title,
        createdAt: Date.now(),
        messages: messages.map((m) => ({
          id: m.id,
          role: m.role,
          text: m.text,
          action: m.action,
          failureType: m.failureType,
        })),
      };
      addOrUpdateSession(chatSession);
      setChatSessions(loadChatSessions());
    }
  }, [messages, session, currentChatSessionId]);

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


  const pushSystemMessage = (text: string, action: Action, failureType?: string | null) => {
    const sysMsg: Message = {
      id: crypto.randomUUID(),
      role: "system",
      text,
      action,
      failureType: failureType ?? null,
    };
    // Dedupe: don't append if last system message has same action + text
    setMessages((prev) => {
      const lastSys = [...prev].reverse().find((m) => m.role === "system");
      if (lastSys && lastSys.action === action && lastSys.text === text) {
        return prev; // Skip duplicate
      }
      return [...prev, sysMsg];
    });
  };

  const beginNewSession = () => {
    const fresh = startNewSession();
    setSession(fresh.session);
    setMessages([]);
    setLastUserText(null);
    setUiState("IDLE");
    setSessionExpired(false);
    pendingRequestId.current = pendingRequestId.current + 1;
    const newChatId = crypto.randomUUID();
    setCurrentChatSessionId(newChatId);
    setCurrentSessionId(newChatId);
    setSidebarOpen(false);
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
      const fetchUrl = `${apiBase}/api/chat`;
      const res = await fetch(fetchUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(requestBody),
      });

      // Transport debug (structure-only, no user text)
      if (debugTransport) {
        const dbgRid = res.headers.get("x-request-id") || res.headers.get("X-Request-ID");
        const dbgUx = res.headers.get("x-ux-state") || res.headers.get("X-UX-State");
        setTransportDebug({ lastUrl: fetchUrl, lastStatus: res.status, lastRequestId: dbgRid, lastUxState: dbgUx, lastError: null });
        console.log("[TransportDebug]", { url: fetchUrl, status: res.status, requestId: dbgRid, uxState: dbgUx, corsExposeHeaders: res.headers.get("access-control-expose-headers") });
      }

      const hdrUx = res.headers.get("X-UX-State") || res.headers.get("x-ux-state");
      const hdrCd = res.headers.get("X-Cooldown-Seconds") || res.headers.get("x-cooldown-seconds");
      const hdrRid = res.headers.get("X-Request-Id") || res.headers.get("x-request-id");
      // On success (2xx), default to OK; on failure, default to ERROR
      const newUx = normalizeUxState(hdrUx, res.ok ? "OK" : "ERROR");
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
      if (action === "REFUSE" || action === "CLOSE" || action === "BLOCK") {
        setUiState("TERMINAL");
      } else if (action === "FALLBACK" || action === "FAIL_GRACEFULLY") {
        setUiState("FAILED");
      } else {
        // ANSWER, ASK_ONE_QUESTION, ASK_CLARIFY, ANSWER_DEGRADED -> allow continued input
        setUiState("IDLE");
      }
    } catch (err) {
      if (pendingRequestId.current !== currentRequestId) {
        return;
      }
      // Transport debug for errors (structure-only, no user text)
      if (debugTransport) {
        const errMsg = err instanceof Error ? err.message : "unknown";
        setTransportDebug((prev) => ({ ...prev, lastError: errMsg }));
        console.log("[TransportDebug] error", { error: errMsg });
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
    if (currentChatSessionId) {
      const chatSession: ChatSession = {
        id: currentChatSessionId,
        title: "New chat",
        createdAt: Date.now(),
        messages: [],
      };
      addOrUpdateSession(chatSession);
      setChatSessions(loadChatSessions());
    }
  };

  const retryLast = () => {
    if (uiState !== "FAILED" || !lastUserText) return;
    setUiState("IDLE");
    void sendMessage(lastUserText, true);
  };

  const copyMessage = async (text: string) => {
    try {
      await navigator.clipboard?.writeText(text);
    } catch {
      pushSystemMessage("Copy failed locally.", "FALLBACK");
    }
  };

  const copyLastResponse = async () => {
    const lastSystem = [...messages].reverse().find((m) => m.role === "system");
    if (!lastSystem) return;
    await copyMessage(lastSystem.text);
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

  const handleSend = () => {
    if (!inputDisabled && input.trim()) {
      if (!currentChatSessionId) {
        const newChatId = crypto.randomUUID();
        setCurrentChatSessionId(newChatId);
        setCurrentSessionId(newChatId);
      }
      void sendMessage(input);
    }
  };

  const handleSelectSession = (sessionId: string) => {
    const chatSession = getSessionById(sessionId);
    if (chatSession) {
      setCurrentChatSessionId(sessionId);
      setCurrentSessionId(sessionId);
      setMessages(chatSession.messages);
      const lastUser = [...chatSession.messages].reverse().find((m) => m.role === "user");
      if (lastUser) setLastUserText(lastUser.text);
      const lastSystem = [...chatSession.messages].reverse().find((m) => m.role === "system");
      if (lastSystem && (lastSystem.action === "REFUSE" || lastSystem.action === "CLOSE")) {
        setUiState("TERMINAL");
      } else if (lastSystem && lastSystem.action === "FALLBACK") {
        setUiState("FAILED");
      } else {
        setUiState("IDLE");
      }
      setSidebarOpen(false);
    }
  };

  const handleDeleteSession = (sessionId: string) => {
    deleteStoredSession(sessionId);
    setChatSessions(loadChatSessions());
    if (currentChatSessionId === sessionId) {
      beginNewSession();
    }
  };


  const lastSystem = useMemo(() => [...messages].reverse().find((m) => m.role === "system"), [messages]);

  const closed = uiState === "TERMINAL" || (lastSystemAction && closedActions.includes(lastSystemAction));

  return (
    <div className="chat-layout">
      <ChatSidebar
        sessions={chatSessions}
        currentSessionId={currentChatSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={beginNewSession}
        onDeleteSession={handleDeleteSession}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="chat-main">
        <header className="chat-header">
          <div className="chat-header-left">
            <button
              className="chat-menu-toggle"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
          </div>
          <div className="chat-header-right">
            <ChatActionsMenu
              onRetry={retryLast}
              onCopyLast={copyLastResponse}
              onCopyAll={copyTranscript}
              onReset={resetChat}
              canRetry={uiState === "FAILED" && !!lastUserText}
              hasMessages={messages.some((m) => m.role === "system")}
            />
          </div>
        </header>

        <div className="chat-messages-container">
          <div className="chat-messages-inner">
            {messages.length === 0 && (
              <div className="chat-empty-state">Ask anything</div>
            )}
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                id={msg.id}
                role={msg.role}
                text={msg.text}
                action={msg.action}
                failureType={msg.failureType}
              />
            ))}
            {uiState === "SENDING" && (
              <div className="chat-message system">
                <div className="chat-message-avatar">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </div>
                <div className="chat-message-content">
                  <div className="chat-message-role">Assistant</div>
                  <div className="chat-message-text">Thinking...</div>
                </div>
              </div>
            )}
          </div>
        </div>

        <ChatComposer
          value={input}
          onChange={setInput}
          onSubmit={handleSend}
          disabled={inputDisabled}
          isSending={uiState === "SENDING"}
        />
      </div>
    </div>
  );
}
