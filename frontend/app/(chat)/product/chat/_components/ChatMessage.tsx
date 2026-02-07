import { Action } from "../contract_runtime";

type ChatMessageProps = {
  id: string;
  role: "user" | "system";
  text: string;
  action?: Action;
  failureType?: string | null;
};

export function ChatMessage({ role, text, action, failureType }: ChatMessageProps) {
  return (
    <div className={`chat-message ${role}`}>
      <div className="chat-message-avatar">
        {role === "user" ? (
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
        <div className="chat-message-role">{role === "user" ? "You" : "Assistant"}</div>
        <div className="chat-message-text">{text}</div>
        {action && <span className="chat-message-badge">{action}</span>}
        {failureType && <span className="chat-message-failure">Failure: {failureType}</span>}
      </div>
    </div>
  );
}
