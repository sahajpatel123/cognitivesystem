import { useState } from "react";

type ChatActionsMenuProps = {
  onRetry: () => void;
  onCopyLast: () => void;
  onCopyAll: () => void;
  onReset: () => void;
  canRetry: boolean;
  hasMessages: boolean;
};

export function ChatActionsMenu({
  onRetry,
  onCopyLast,
  onCopyAll,
  onReset,
  canRetry,
  hasMessages,
}: ChatActionsMenuProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  const handleReset = () => {
    setShowResetConfirm(true);
    setShowMenu(false);
  };

  const confirmReset = () => {
    onReset();
    setShowResetConfirm(false);
  };

  const cancelReset = () => {
    setShowResetConfirm(false);
  };

  return (
    <>
      <div className="chat-actions-menu">
        <button
          className="chat-actions-trigger"
          onClick={() => setShowMenu(!showMenu)}
          aria-label="More actions"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="1" />
            <circle cx="12" cy="5" r="1" />
            <circle cx="12" cy="19" r="1" />
          </svg>
        </button>
        {showMenu && (
          <>
            <div className="chat-actions-overlay" onClick={() => setShowMenu(false)} />
            <div className="chat-actions-dropdown">
              <button onClick={() => { onRetry(); setShowMenu(false); }} disabled={!canRetry}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="23 4 23 10 17 10" />
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                </svg>
                Retry last
              </button>
              <button onClick={() => { onCopyLast(); setShowMenu(false); }} disabled={!hasMessages}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
                Copy last response
              </button>
              <button onClick={() => { onCopyAll(); setShowMenu(false); }} disabled={!hasMessages}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
                  <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
                </svg>
                Copy conversation
              </button>
              <div className="chat-actions-divider" />
              <button onClick={handleReset} className="chat-actions-danger">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
                Reset chat
              </button>
            </div>
          </>
        )}
      </div>

      {showResetConfirm && (
        <div className="chat-confirm-overlay" onClick={cancelReset}>
          <div className="chat-confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Reset current chat?</h3>
            <p>This will clear all messages from the current session.</p>
            <div className="chat-confirm-actions">
              <button onClick={cancelReset} className="chat-confirm-cancel">
                Cancel
              </button>
              <button onClick={confirmReset} className="chat-confirm-ok">
                Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
