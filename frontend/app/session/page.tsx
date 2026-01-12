import { PrimaryMetrics } from "../components/primary-metrics";
import {
  INITIAL_RUN,
  OPERATIONAL_PATTERNS,
  SESSION_BASELINE,
} from "../lib/static-data";
import {
  formatPipelineState,
  formatRiskClassification,
  formatSecondsAsClock,
  operationalPatternLabel,
} from "../lib/formatters";

const constraintChecklist = [
  "Token budget: 4,096 reasoning / 2,048 expression",
  "Session TTL: 05:00 – resets on expiry",
  "Stateless adapter: enforced",
  "Enforcement: fail-closed, no retries",
  "Memory: session-local hypotheses only",
];

const payloadPreview = JSON.stringify(
  {
    session_id: SESSION_BASELINE.sessionId,
    operational_pattern: SESSION_BASELINE.operationalPattern,
    user_message: SESSION_BASELINE.userMessage,
    context_summary: SESSION_BASELINE.contextSummary,
    cognitive_style: SESSION_BASELINE.cognitiveStyle,
  },
  null,
  2,
);

export default function SessionCommandSurfacePage() {
  const metrics = [
    {
      label: "Operational pattern",
      value: operationalPatternLabel(SESSION_BASELINE.operationalPattern),
      tooltip: "Bounded by Phase 4 operational patterns.",
    },
    {
      label: "Session TTL",
      value: formatSecondsAsClock(SESSION_BASELINE.ttlSeconds),
      tooltip: "Session expires without extension capability.",
    },
    {
      label: "Execution state",
      value: formatPipelineState("idle"),
      tooltip: "Pipeline awaits certified invocation.",
      state: "idle",
    },
    {
      label: "Risk status",
      value: formatRiskClassification(INITIAL_RUN.riskClassification),
      tooltip: "Risk envelope remains within certified bounds until escalation.",
    },
  ];

  return (
    <div className="surface-stack">
      <div className="page-header">
        <span className="status-strip">Session command surface</span>
        <h2>Structured request composition</h2>
        <p>Compose deterministic session payloads while exposing contract constraints without modification.</p>
      </div>

      <PrimaryMetrics metrics={metrics} />

      <section className="surface-content surface-entrance" data-motion="card">
        <div className="surface-columns">
          <div className="card">
            <h3 className="section-heading">Request schema</h3>
            <p className="section-caption">Inputs remain bound to certified operational patterns and cognitive constraints.</p>
            <div className="grid-two">
              <div className="form-block">
                <label htmlFor="session-id">Session identifier</label>
                <input id="session-id" value={SESSION_BASELINE.sessionId} disabled />
              </div>
              <div className="form-block">
                <label htmlFor="ttl">TTL remaining</label>
                <input id="ttl" value={formatSecondsAsClock(SESSION_BASELINE.ttlSeconds)} disabled />
              </div>
            </div>
            <div className="grid-two">
              <div className="form-block">
                <label htmlFor="pattern">Operational pattern</label>
                <select id="pattern" value={SESSION_BASELINE.operationalPattern} disabled>
                  {OPERATIONAL_PATTERNS.map((pattern) => (
                    <option key={pattern.id} value={pattern.id}>
                      {pattern.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-block">
                <label htmlFor="cognitive-style">Cognitive style</label>
                <select id="cognitive-style" value={SESSION_BASELINE.cognitiveStyle} disabled>
                  <option value="neutral">Neutral</option>
                  <option value="formal">Formal</option>
                  <option value="casual">Casual</option>
                </select>
              </div>
            </div>
            <div className="form-block">
              <label htmlFor="user-message">User directive</label>
              <textarea id="user-message" value={SESSION_BASELINE.userMessage} disabled />
            </div>
            <div className="form-block">
              <label htmlFor="context-summary">Context summary</label>
              <textarea id="context-summary" value={SESSION_BASELINE.contextSummary} disabled />
            </div>
            <div className="control-row">
              <button type="button" className="primary-action" disabled>
                Submit request
              </button>
              <button type="button" className="secondary-action" disabled>
                Reset form
              </button>
            </div>
          </div>
          <aside className="card" aria-label="Session constraints">
            <h3>Constraint checklist</h3>
            <p className="helper-text">Bounded controls ensure adherence to certified enforcement posture.</p>
            <ul className="list-minor">
              {constraintChecklist.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <details className="fold" aria-label="Outbound payload preview">
              <summary>
                Outbound payload preview <span>Serialized payload remains fully visible.</span>
              </summary>
              <div className="fold-body">
                <pre className="monospace-block" aria-label="Serialized payload">
                  {payloadPreview}
                </pre>
              </div>
            </details>
          </aside>
        </div>
      </section>
    </div>
  );
}
