import { PrimaryMetrics } from "../../components/primary-metrics";
import { ExecutionStage } from "../../components/panels/execution-stage";
import { AUDIT_RUNS, INITIAL_RUN } from "../../lib/static-data";
import {
  formatPipelineState,
  formatRiskClassification,
  formatSecondsAsClock,
} from "../../lib/formatters";

const enforcementOutcomeCopy: Record<typeof INITIAL_RUN.enforcementOutcome, string> = {
  pass: "Enforcement outcome: Pass",
  structural_violation: "Enforcement outcome: Structural violation",
  semantic_violation: "Enforcement outcome: Semantic violation",
};

export default function PipelineExecutionSurfacePage() {
  const metrics = [
    {
      label: "Current state",
      value: formatPipelineState(INITIAL_RUN.state),
      tooltip: "Deterministic stage alignment across reasoning and expression.",
      state: INITIAL_RUN.state,
    },
    {
      label: "Risk status",
      value: formatRiskClassification(INITIAL_RUN.riskClassification),
      tooltip: "Risk envelope sourced from Phase 4 classification.",
    },
    {
      label: "Most recent execution",
      value: INITIAL_RUN.id,
      tooltip: "Latest certified pipeline execution identifier.",
    },
    {
      label: "Average reasoning duration",
      value: formatSecondsAsClock(152),
      tooltip: "Illustrative timing; no adaptive pacing is introduced.",
    },
  ];

  const failureRuns = AUDIT_RUNS.filter(
    (run) => run.state === "failed" || run.enforcementOutcome !== "pass",
  );

  return (
    <div className="surface-stack">
      <div className="page-header">
        <span className="status-strip">Pipeline execution surface</span>
        <h2>Deterministic stage visibility</h2>
        <p>Stages remain isolated with reasoning, hypothesis, expression, and enforcement outputs exposed without omission.</p>
      </div>

      <PrimaryMetrics metrics={metrics} />

      <section className="surface-content surface-entrance" data-motion="card">
        <div className="surface-columns">
          <div className="hero-card">
            <h3>Latest execution</h3>
            <p className="helper-text">Execution ID: {INITIAL_RUN.id}</p>
            <p className="helper-text">{INITIAL_RUN.reasoningTrace.summary}</p>
            <div className="divider-soft" />
            <span className="badge badge-success">{enforcementOutcomeCopy[INITIAL_RUN.enforcementOutcome]}</span>
          </div>
          <aside className="card">
            <h3>Adapter metadata</h3>
            <div className="tag-row">
              <span className="code-chip">Model: reasoning-reference-v1</span>
              <span className="code-chip">Tokens: 152 / 238</span>
              <span className="code-chip">Call ID: {INITIAL_RUN.id}-call</span>
            </div>
            <p className="helper-text">No cross-session memory accessed. Stateless execution enforced.</p>
          </aside>
        </div>
      </section>

      <section className="surface-content surface-entrance" data-motion="panel">
        <div className="surface-columns">
          <div className="card">
            <h3 className="section-heading">Stage outputs</h3>
            <p className="section-caption">Reasoning trace, hypothesis deltas, and expression remain isolated per contract.</p>
            <ExecutionStage run={INITIAL_RUN} />
          </div>
          <details className="fold" aria-label="Audit sample">
            <summary>
              Audit sample <span>Immutable execution history excerpt.</span>
            </summary>
            <div className="fold-body">
              <ul className="history-list">
                {AUDIT_RUNS.slice(0, 3).map((run) => (
                  <li key={run.id}>
                    <div className="control-row" style={{ justifyContent: "space-between" }}>
                      <span className="code-chip">{run.id}</span>
                      <span className="code-chip">{run.timestamp}</span>
                    </div>
                    <p className="tooltip">State: {formatPipelineState(run.state)}</p>
                    <p className="tooltip">Risk: {run.riskClassification}</p>
                  </li>
                ))}
              </ul>
            </div>
          </details>
        </div>
      </section>

      <section className="surface-content surface-entrance" data-motion="panel">
        <h3 className="section-heading">Failure visibility</h3>
        <p className="section-caption">All structural, semantic, and boundary failures surface immediately and do not self-heal.</p>
        <details className="fold" aria-label="Failure runs">
          <summary>
            Failure runs <span>Structural, semantic, and boundary failures.</span>
          </summary>
          <div className="fold-body">
            <div className="surface-summary">
              {failureRuns.map((run) => (
                <div key={run.id} className="card" data-interactive="true">
                  <span className="section-label">Execution ID</span>
                  <span className="code-chip">{run.id}</span>
                  <p className="tooltip">State: {formatPipelineState(run.state)}</p>
                  <p className="tooltip">Risk: {run.riskClassification}</p>
                  <div className="section-divider" />
                  <p className="detail-emphasis">Enforcement outcome: {run.enforcementOutcome}</p>
                  {run.failureDetail ? <p>{run.failureDetail}</p> : <p>No explicit failure detail recorded.</p>}
                </div>
              ))}
            </div>
          </div>
        </details>
      </section>
    </div>
  );
}
