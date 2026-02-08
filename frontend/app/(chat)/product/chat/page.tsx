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

type MessageStatus = "pending" | "done" | "error" | undefined;

type Message = {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
  status?: MessageStatus;
  action?: Action;
  failureType?: string | null;
  debug?: {
    statusCode?: number | null;
    contentType?: string | null;
    durationMs?: number | null;
    rawPreview?: string | null;
  };
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [isComposerFocused, setIsComposerFocused] = useState(false);
  const [idleHeadline, setIdleHeadline] = useState("Ready when you are.");
  const [attachments, setAttachments] = useState<any[]>([]);
  const [mounted, setMounted] = useState(false);
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
    setMounted(true);
    const headlines = ["Ready to dive in?", "How can I help?", "Ready when you are."];
    const randomHeadline = headlines[Math.floor(Math.random() * headlines.length)];
    setIdleHeadline(randomHeadline);
    
    if (typeof window !== "undefined") {
      const collapsed = localStorage.getItem("cs_chat_sidebar_collapsed") === "1";
      setSidebarCollapsed(collapsed);
    }
  }, []);

  useEffect(() => {
    if (mounted && typeof window !== "undefined") {
      localStorage.setItem("cs_chat_sidebar_collapsed", sidebarCollapsed ? "1" : "0");
    }
  }, [sidebarCollapsed, mounted]);

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
        const lastAssistant = [...currentSession.messages]
          .reverse()
          .find((m) => m.role === "assistant" || m.role === "system");
        if (lastAssistant && (lastAssistant.action === "REFUSE" || lastAssistant.action === "CLOSE")) {
          setUiState("TERMINAL");
        } else if (lastAssistant && lastAssistant.action === "FALLBACK") {
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
          status: m.status,
        })),
      };
      addOrUpdateSession(chatSession);
      setChatSessions(loadChatSessions());
    }
  }, [messages, session, currentChatSessionId]);

  const lastSystemAction = useMemo(() => {
    const sys = [...messages].reverse().find((m) => m.role === "assistant" || m.role === "system");
    return sys?.action;
  }, [messages]);

  const cooldownActive = !!(cooldownSeconds && cooldownSeconds > 0);
  const inputDisabled =
    uiState === "SENDING" ||
    uiState === "TERMINAL" ||
    (lastSystemAction && closedActions.includes(lastSystemAction)) ||
    cooldownActive;

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

  const extractMessageFromJson = (obj: any): { content: string; action?: string | null; failureType?: string | null } => {
    const tryPath = (path: Array<string | number>): any => {
      let cur: any = obj;
      for (const key of path) {
        if (cur == null) return undefined;
        cur = cur[key as keyof typeof cur];
      }
      return cur;
    };
    const candidates: Array<Array<string | number>> = [
      ["reply"],
      ["message"],
      ["content"],
      ["output"],
      ["data", "reply"],
      ["data", "message"],
      ["data", "content"],
      ["result", "content"],
      ["rendered_text"],
    ];
    for (const path of candidates) {
      const val = tryPath(path);
      if (typeof val === "string" && val.trim().length > 0) {
        return { content: val, action: obj?.action ?? null, failureType: obj?.failure_type ?? obj?.failureType ?? null };
      }
    }
    return { content: "", action: obj?.action ?? null, failureType: obj?.failure_type ?? obj?.failureType ?? null };
  };

  const replaceMessageById = (id: string, updater: (msg: Message) => Message): void => {
    setMessages((prev) => prev.map((m) => (m.id === id ? updater(m) : m)));
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
    const pendingAssistantId = `pending-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const pendingAssistant: Message = { id: pendingAssistantId, role: "assistant", text: "", status: "pending" };
    setMessages((prev) => [...prev, userMsg, pendingAssistant]);
    setInput("");
    setUiState("SENDING");
    const currentRequestId = pendingRequestId.current + 1;
    pendingRequestId.current = currentRequestId;
    const setUiStateForAction = (actionVal?: Action | null) => {
        if (actionVal === "REFUSE" || actionVal === "CLOSE" || actionVal === "BLOCK") {
          setUiState("TERMINAL");
        } else if (actionVal === "FALLBACK" || actionVal === "FAIL_GRACEFULLY") {
          setUiState("FAILED");
        } else {
          setUiState("IDLE");
        }
      };
    try {
      const fetchUrl = `${apiBase}/api/chat`;
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30000);
      const start = Date.now();
      if (debugTransport) {
        console.log("[TransportDebug] request start", { url: fetchUrl, start });
      }
      const res = await fetch(fetchUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        cache: "no-store",
        signal: controller.signal,
        body: JSON.stringify(requestBody),
      });
      clearTimeout(timeout);
      const duration = Date.now() - start;

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
      const contentType = res.headers.get("content-type") || "";
      const devLog = () => {
        const status = res.status;
        if (debugTransport) {
          console.log("[TransportDebug] response", { status, contentType, duration });
        }
      };
      devLog();

      const markError = (message: string, rawPreview: string, statusCode: number | null) => {
        replaceMessageById(pendingAssistantId, (msg) => ({
          ...msg,
          text: message,
          status: "error",
          debug: {
            statusCode,
            contentType,
            durationMs: duration,
            rawPreview: rawPreview.slice(0, 1500),
          },
        }));
        pushSystemMessage(message, "FALLBACK");
        setUiState("FAILED");
      };

      if (contentType.includes("text/event-stream") && res.body) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let accumulated = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          buffer += chunk;
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";
          for (const part of parts) {
            const dataLine = part
              .split("\n")
              .map((l) => l.trim())
              .find((l) => l.startsWith("data:"));
            if (dataLine) {
              const token = dataLine.replace(/^data:\s*/, "");
              if (token) {
                accumulated += token;
                const currentContent = accumulated;
                replaceMessageById(pendingAssistantId, (msg) => ({ ...msg, text: currentContent, status: "pending" }));
              }
            }
          }
        }
        const finalContent = accumulated || buffer.trim();
        if (!finalContent) {
          markError("Empty response body (200).", "", res.status);
        } else {
          const preview = finalContent.slice(0, 1500);
          if (debugTransport) {
            console.log("[TransportDebug] sse final", {
              status: res.status,
              contentType,
              duration,
              rawLength: finalContent.length,
              preview,
            });
          }
          replaceMessageById(pendingAssistantId, (msg) => ({
            ...msg,
            text: finalContent,
            status: "done",
            debug: {
              statusCode: res.status,
              contentType,
              durationMs: duration,
              rawPreview: preview,
            },
          }));
          setUiState("IDLE");
        }
        return;
      }

      const raw = await res.text();
      const rawPreview = raw.slice(0, 1500);
      if (debugTransport) {
        console.log("[TransportDebug] response body", {
          status: res.status,
          contentType,
          duration,
          rawLength: raw.length,
          preview: rawPreview,
        });
      }
      if (pendingRequestId.current !== currentRequestId) {
        return;
      }
      const rawTrim = raw.trim();
      if (!res.ok) {
        const friendly = rawTrim || "Request failed. Please retry.";
        markError(friendly, raw, res.status);
        return;
      }
      let parsed: any = null;
      let extracted = "";
      try {
        parsed = JSON.parse(raw);
        const { content, action, failureType } = extractMessageFromJson(parsed);
        extracted = content;
        if (!extracted && rawTrim) {
          extracted = rawTrim;
        }
        replaceMessageById(pendingAssistantId, (msg) => ({
          ...msg,
          text: extracted || "Unexpected response shape",
          status: extracted ? "done" : "error",
          action: (action as Action | undefined) ?? msg.action,
          failureType: (failureType as string | null | undefined) ?? msg.failureType,
          debug: {
            statusCode: res.status,
            contentType,
            durationMs: duration,
            rawPreview,
          },
        }));
      } catch (e) {
        if (!rawTrim) {
          markError("Empty response body (200).", raw, res.status);
          return;
        }
        extracted = rawTrim;
        replaceMessageById(pendingAssistantId, (msg) => ({
          ...msg,
          text: extracted,
          status: "done",
          debug: {
            statusCode: res.status,
            contentType,
            durationMs: duration,
            rawPreview,
          },
        }));
      }

      if (!extracted || extracted === "Unexpected response shape") {
        markError("Unexpected response shape", raw, res.status);
        return;
      }
      setUiState("IDLE");
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
      replaceMessageById(pendingAssistantId, (msg) => ({
        ...msg,
        text: "Request failed. Please retry.",
        status: "error",
      }));
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
  const hasMessages = messages.length > 0;
  const idleMode = !hasMessages && !isComposerFocused;

  const handleComposerFocus = () => {
    setIsComposerFocused(true);
  };

  const handleComposerBlur = () => {
    if (messages.length === 0) {
      setIsComposerFocused(false);
    }
  };

  return (
    <div className={`chat-layout ${sidebarCollapsed ? "sidebar-collapsed" : ""} ${idleMode ? "idle-mode" : ""}`}>
      <ChatSidebar
        sessions={chatSessions}
        currentSessionId={currentChatSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={beginNewSession}
        onDeleteSession={handleDeleteSession}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {sidebarCollapsed && (
        <button
          className="sidebar-toggle-floating"
          onClick={() => setSidebarCollapsed(false)}
          aria-label="Expand sidebar"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <line x1="9" y1="3" x2="9" y2="21" />
          </svg>
        </button>
      )}

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

        {idleMode ? (
          <div className="idle-stage">
            <div className="idle-cluster">
              <div className="idle-headline">{idleHeadline}</div>
              <ChatComposer
                value={input}
                onChange={setInput}
                onSubmit={handleSend}
                disabled={inputDisabled}
                isSending={uiState === "SENDING"}
                onFocus={handleComposerFocus}
                onBlur={handleComposerBlur}
                attachments={attachments}
                onAttachmentsChange={setAttachments}
              />
            </div>
          </div>
        ) : (
          <>
            <div className="chat-messages-container">
              <div className="chat-messages-inner">
                {messages.map((msg) => (
                  <ChatMessage
                    key={msg.id}
                    id={msg.id}
                    role={msg.role}
                    text={msg.text}
                    status={msg.status}
                    action={msg.action}
                    failureType={msg.failureType}
                    debug={msg.debug}
                  />
                ))}
              </div>
            </div>

            <div className="composer-shell">
              <ChatComposer
                value={input}
                onChange={setInput}
                onSubmit={handleSend}
                disabled={inputDisabled}
                isSending={uiState === "SENDING"}
                onFocus={handleComposerFocus}
                onBlur={handleComposerBlur}
                attachments={attachments}
                onAttachmentsChange={setAttachments}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
