import { useState } from "react";

type ChatToolbarProps = {
  onReset: () => void;
  onRetry: () => void;
  onCopyLast: () => void;
  onCopyAll: () => void;
  onNewSession: () => void;
  canRetry: boolean;
  hasMessages: boolean;
};

export function ChatToolbar({
  onReset,
  onRetry,
  onCopyLast,
  onCopyAll,
  onNewSession,
  canRetry,
  hasMessages,
}: ChatToolbarProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  const handleReset = () => {
    setShowResetConfirm(true);
  };

  const confirmReset = () => {
    onReset();
    setShowResetConfirm(false);
    setShowMenu(false);
  };

  const cancelReset = () => {
    setShowResetConfirm(false);
  };

  return (
    <div className="chat-toolbar">
      <button type="button" className="toolbar-btn-primary" onClick={onNewSession}>
        New session
      </button>
      <div className="toolbar-menu-wrapper">
        <button
          type="button"
          className="toolbar-btn-menu"
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
          <div className="toolbar-dropdown">
            <button
              type="button"
              onClick={() => {
                onRetry();
                setShowMenu(false);
              }}
              disabled={!canRetry}
            >
              Retry last
            </button>
            <button
              type="button"
              onClick={() => {
                onCopyLast();
                setShowMenu(false);
              }}
              disabled={!hasMessages}
            >
              Copy last response
            </button>
            <button
              type="button"
              onClick={() => {
                onCopyAll();
                setShowMenu(false);
              }}
              disabled={!hasMessages}
            >
              Copy conversation
            </button>
            <button type="button" onClick={handleReset} className="toolbar-danger">
              Reset chat
            </button>
          </div>
        )}
      </div>

      {showResetConfirm && (
        <div className="toolbar-confirm-overlay" onClick={cancelReset}>
          <div className="toolbar-confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Reset chat?</h3>
            <p>This will clear all messages from the current session.</p>
            <div className="toolbar-confirm-actions">
              <button type="button" onClick={cancelReset} className="toolbar-confirm-cancel">
                Cancel
              </button>
              <button type="button" onClick={confirmReset} className="toolbar-confirm-ok">
                Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
