import Link from "next/link";
import { ChatHistory, ChatSession } from "./ChatHistory";

type ChatSidebarProps = {
  sessions: ChatSession[];
  currentSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
  onDeleteSession: (sessionId: string) => void;
  isOpen: boolean;
  onClose: () => void;
};

export function ChatSidebar({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  isOpen,
  onClose,
}: ChatSidebarProps) {
  return (
    <>
      {isOpen && <div className="chat-sidebar-overlay" onClick={onClose} />}
      <aside className={`chat-sidebar ${isOpen ? "open" : ""}`}>
        <div className="chat-sidebar-header">
          <Link href="/" className="chat-brand">
            Cognitive System
          </Link>
          <button className="chat-sidebar-close" onClick={onClose} aria-label="Close sidebar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <ChatHistory
          sessions={sessions}
          currentSessionId={currentSessionId}
          onSelectSession={onSelectSession}
          onNewChat={onNewChat}
          onDeleteSession={onDeleteSession}
        />
      </aside>
    </>
  );
}
