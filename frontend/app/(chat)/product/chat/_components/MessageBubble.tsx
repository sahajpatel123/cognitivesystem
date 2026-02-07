import { Action } from "../contract_runtime";

type MessageBubbleProps = {
  id: string;
  role: "user" | "system";
  text: string;
  action?: Action;
  failureType?: string | null;
  onCopy: (text: string) => void;
};

export function MessageBubble({ role, text, action, failureType, onCopy }: MessageBubbleProps) {
  return (
    <div className={`message-bubble-wrapper ${role}`}>
      <div className="message-bubble">
        <div className="message-header">
          <span className="message-role">{role === "user" ? "You" : "Assistant"}</span>
          {action && <span className="message-badge">{action}</span>}
        </div>
        <p className="message-text">{text}</p>
        {failureType && <span className="message-failure">Failure: {failureType}</span>}
        <button
          type="button"
          className="message-copy-btn"
          onClick={() => onCopy(text)}
          aria-label="Copy message"
          title="Copy message"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
        </button>
      </div>
    </div>
  );
}
