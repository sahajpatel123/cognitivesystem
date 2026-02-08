import { Action } from "../contract_runtime";

type MessageStatus = "pending" | "done" | "error" | undefined;

type MessageBubbleProps = {
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
  onCopy: (text: string) => void;
};

export function MessageBubble({ role, text, status, action, failureType, debug, onCopy }: MessageBubbleProps) {
  const isAssistant = role === "assistant" || role === "system";
  const isPending = status === "pending";
  const isError = status === "error";
  const displayText = text && text.trim().length > 0 ? text : isPending ? "Thinking…" : "";
  const showDebug = isError && process.env.NODE_ENV !== "production";
  return (
    <div className={`message-bubble-wrapper ${isAssistant ? "system" : "user"}`}>
      <div className="message-bubble">
        <div className="message-header">
          <span className="message-role">{isAssistant ? "Assistant" : "You"}</span>
          {action && <span className="message-badge">{action}</span>}
        </div>
        <p className={`message-text${isPending ? " pending" : ""}${isError ? " error" : ""}`}>
          {isPending && <span className="chat-message-pending-indicator">●</span>}
          {displayText}
        </p>
        {failureType && <span className="message-failure">Failure: {failureType}</span>}
        <button
          type="button"
          className="message-copy-btn"
          onClick={() => onCopy(displayText || text)}
          aria-label="Copy message"
          title="Copy message"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
        </button>
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
