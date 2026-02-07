type DebugPanelProps = {
  apiBase: string;
  uxState: string;
  cooldownSeconds: number | null;
  requestId: string | null;
  sessionExpired: boolean;
  remainingMinutes: number | null;
  lastSystemAction: string;
  uiState: string;
  failureType: string | null;
  transportDebug?: {
    lastUrl: string | null;
    lastStatus: number | null;
    lastRequestId: string | null;
    lastUxState: string | null;
    lastError: string | null;
  };
};

export function DebugPanel({
  apiBase,
  uxState,
  cooldownSeconds,
  requestId,
  sessionExpired,
  remainingMinutes,
  lastSystemAction,
  uiState,
  failureType,
  transportDebug,
}: DebugPanelProps) {
  const isDev = process.env.NODE_ENV !== "production";
  const debugTransport = process.env.NEXT_PUBLIC_DEBUG_TRANSPORT === "1";

  if (!isDev) return null;

  return (
    <details className="debug-panel">
      <summary>Debug Info (Development Only)</summary>
      <div className="debug-content">
        <div className="debug-section">
          <strong>Environment</strong>
          <div>API Base: {apiBase}</div>
          <div>ENV: {process.env.NEXT_PUBLIC_ENV || "development"}</div>
        </div>
        <div className="debug-section">
          <strong>State</strong>
          <div>UI State: {uiState}</div>
          <div>UX State: {uxState}</div>
          <div>Action: {lastSystemAction || "—"}</div>
          <div>Failure: {failureType || "NONE"}</div>
          <div>Session: {sessionExpired ? "EXPIRED" : "ACTIVE"}</div>
          {remainingMinutes !== null && <div>TTL: {remainingMinutes}m</div>}
        </div>
        <div className="debug-section">
          <strong>Request</strong>
          <div>Request ID: {requestId || "—"}</div>
          <div>Cooldown: {cooldownSeconds ? `${cooldownSeconds}s` : "—"}</div>
        </div>
        {debugTransport && transportDebug && (
          <div className="debug-section">
            <strong>Transport Debug</strong>
            <div>URL: {transportDebug.lastUrl || "—"}</div>
            <div>Status: {transportDebug.lastStatus || "—"}</div>
            <div>X-Request-ID: {transportDebug.lastRequestId || "—"}</div>
            <div>X-UX-State: {transportDebug.lastUxState || "—"}</div>
            {transportDebug.lastError && <div style={{ color: "#ef4444" }}>Error: {transportDebug.lastError}</div>}
          </div>
        )}
      </div>
    </details>
  );
}
