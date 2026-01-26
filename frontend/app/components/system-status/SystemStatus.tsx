"use client";

import { useMemo } from "react";
import { UXState, getUxCopy } from "@/app/lib/ux_state";

export type SystemStatusProps = {
  uxState: UXState;
  cooldownSeconds: number | null;
  requestId: string | null;
  onRetry?: () => void;
};

export function SystemStatus({ uxState, cooldownSeconds, requestId, onRetry }: SystemStatusProps) {
  const copy = useMemo(() => getUxCopy(uxState, cooldownSeconds), [uxState, cooldownSeconds]);

  if (uxState === "OK") {
    return null;
  }

  const truncatedRequestId = requestId ? requestId.slice(-8) : null;
  const showRetry = Boolean(onRetry) && ["ERROR", "RATE_LIMITED", "DEGRADED"].includes(uxState);
  const retryDisabled = Boolean(cooldownSeconds && cooldownSeconds > 0);

  return (
    <div
      className={`system-status tone-${copy.tone}`}
      role="status"
      aria-live="polite"
      aria-label={`System state ${uxState}`}
    >
      <div className="status-main">
        <div className="status-text">
          <div className="status-title">{copy.title}</div>
          {copy.body && <div className="status-body">{copy.body}</div>}
          {cooldownSeconds ? <div className="status-body">Cooldown: {cooldownSeconds}s</div> : null}
        </div>
        <div className="status-actions">
          {showRetry ? (
            <button type="button" onClick={onRetry} disabled={retryDisabled} aria-disabled={retryDisabled}>
              Retry
            </button>
          ) : null}
          {requestId ? (
            <button
              type="button"
              onClick={() => {
                void navigator.clipboard?.writeText(requestId);
              }}
              aria-label="Copy request id"
            >
              {truncatedRequestId ? `Request ID: …${truncatedRequestId}` : "Copy Request ID"}
            </button>
          ) : null}
        </div>
      </div>
      <style jsx>{`
        .system-status {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 12px;
          padding: 10px 14px;
          border-radius: 10px;
          border: 1px solid #1f2937;
          background: #0f172a;
          color: #e5e7eb;
          font-size: 14px;
          align-items: center;
        }
        .status-main {
          display: flex;
          width: 100%;
          justify-content: space-between;
          gap: 12px;
          flex-wrap: wrap;
        }
        .status-text {
          display: grid;
          gap: 4px;
        }
        .status-title {
          font-weight: 600;
        }
        .status-body {
          font-size: 13px;
          color: #cbd5e1;
        }
        .status-actions {
          display: flex;
          gap: 8px;
          align-items: center;
        }
        .status-actions button {
          border-radius: 8px;
          border: 1px solid #1f2937;
          background: #0b1222;
          color: #e5e7eb;
          padding: 8px 10px;
          font-size: 13px;
        }
        .status-actions button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .tone-warn {
          border-color: #f59e0b;
          background: #0f172a;
        }
        .tone-error {
          border-color: #ef4444;
          background: #1f0f12;
        }
        .tone-success {
          border-color: #10b981;
          background: #0f1f1a;
        }
        .tone-neutral {
          border-color: #334155;
          background: #0f172a;
        }
        @media (max-width: 640px) {
          .system-status {
            grid-template-columns: 1fr;
          }
          .status-main {
            flex-direction: column;
            align-items: flex-start;
          }
          .status-actions {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}
