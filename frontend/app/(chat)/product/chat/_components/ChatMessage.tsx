import { Action } from "../contract_runtime";

type MessageStatus = "pending" | "done" | "error" | undefined;

type DebugInfo = {
  statusCode?: number | null;
  contentType?: string | null;
  durationMs?: number | null;
  rawPreview?: string | null;
};

type ChatMessageProps = {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
  status?: MessageStatus;
  action?: Action;
  failureType?: string | null;
  debug?: DebugInfo;
};

export function ChatMessage({ role, text, status, action, failureType, debug }: ChatMessageProps) {
  const isAssistant = role === "assistant" || role === "system";
  const isPending = status === "pending";
  const isError = status === "error";
  const showDebug = isError && process.env.NODE_ENV !== "production";
  const displayText = text && text.trim().length > 0 ? text : isPending ? "Thinking…" : "";
  return (
    <div className={`chat-message ${isAssistant ? "system" : "user"}`}>
      <div className="chat-message-avatar">
        {!isAssistant ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        )}
      </div>
      <div className="chat-message-content">
        <div className="chat-message-role">{isAssistant ? "Assistant" : "You"}</div>
        <div className={`chat-message-text${isPending ? " pending" : ""}${isError ? " error" : ""}`}>
          {isPending && <span className="chat-message-pending-indicator">●</span>}
          {displayText}
        </div>
        {action && <span className="chat-message-badge">{action}</span>}
        {failureType && <span className="chat-message-failure">Failure: {failureType}</span>}
        {showDebug && (
          <details className="chat-message-debug">
            <summary>Debug</summary>
            <div>Status: {debug?.statusCode ?? "n/a"}</div>
            <div>Content-Type: {debug?.contentType ?? "n/a"}</div>
            <div>Duration: {debug?.durationMs ?? "n/a"} ms</div>
            <pre>{debug?.rawPreview ?? ""}</pre>
          </details>
        )}
      </div>
    </div>
  );
}
