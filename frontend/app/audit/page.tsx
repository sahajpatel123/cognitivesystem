import Link from "next/link";
import { PrimaryMetrics } from "../components/primary-metrics";
import { AUDIT_RUNS } from "../lib/static-data";
import { formatPipelineState, formatRiskClassification } from "../lib/formatters";

const totalRuns = AUDIT_RUNS.length;
const failedRuns = AUDIT_RUNS.filter((run) => run.state === "failed").length;
const elevatedRuns = AUDIT_RUNS.filter((run) => run.riskClassification !== "low").length;
const latestRun = AUDIT_RUNS[0];

export default function AuditArchivePage() {
  const metrics = [
    {
      label: "Audit records",
      value: `${totalRuns} executions",
      tooltip: "Immutable archive bounded by certified retention window.",
    },
    {
      label: "Failure count",
      value: `${failedRuns} recorded failures",
      tooltip: "Failed runs remain visible; no suppression is permitted.",
    },
    {
      label: "Elevated risk",
      value: `${elevatedRuns} elevated contexts",
      tooltip: "Elevated or out-of-scope designations require operator acknowledgement.",
    },
    {
      label: "Latest execution",
      value: latestRun.id,
      tooltip: "Most recent execution available for trace drilldown.",
    },
  ];

  return (
    <div className="surface-stack">
      <div className="page-header">
        <span className="status-strip">Audit & trace archive</span>
        <h2>Immutable execution history</h2>
        <p>Each execution trace remains accessible with stage-aligned evidence, risk shifts, and enforcement outcomes.</p>
      </div>

      <PrimaryMetrics metrics={metrics} />

      <section className="surface-content surface-entrance" data-motion="card">
        <div className="surface-columns">
          <div className="hero-card">
            <h3>Execution roster</h3>
            <p className="helper-text">Select an execution to review reasoning, expression, and enforcement evidence.</p>
            <div className="divider-soft" />
            <p className="helper-text">Latest execution: {latestRun.id}</p>
            <p className="helper-text">{latestRun.reasoningTrace.summary}</p>
          </div>
          <details className="fold" aria-label="Execution roster list">
            <summary>
              Execution roster <span>Immutable execution history within retention scope.</span>
            </summary>
            <div className="fold-body">
              <ul className="history-list">
                {AUDIT_RUNS.map((run) => (
                  <li key={run.id}>
                    <div className="control-row" style={{ justifyContent: "space-between" }}>
                      <span className="code-chip">{run.id}</span>
                      <span className="code-chip">{run.timestamp}</span>
                    </div>
                    <p className="tooltip">State: {formatPipelineState(run.state)}</p>
                    <p className="tooltip">Risk: {run.riskClassification}</p>
                    <Link className="detail-emphasis" href={`/execution?run=${run.id}`}>
                      View pipeline surface
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </details>
        </div>
      </section>

      <section className="surface-content surface-entrance" data-motion="panel">
        <h3 className="section-heading">Trace excerpts</h3>
        <p className="section-caption">Hypothesis deltas and enforcement responses are surfaced for inspection.</p>
        <div className="surface-grid wide">
          <div className="card">
            <h4 className="section-subheading">Hypothesis deltas</h4>
            <ul className="list-minor">
              {latestRun.hypotheses.map((hypothesis) => (
                <li key={hypothesis.id}>
                  <strong>{hypothesis.claim}</strong>
                  <div className="tag-row">
                    <span className="code-chip">Δsupport: {hypothesis.supportScoreDelta.toFixed(2)}</span>
                    <span className="code-chip">Δrefute: {hypothesis.refuteScoreDelta.toFixed(2)}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <div className="card">
            <h4 className="section-subheading">Enforcement signals</h4>
            <div className="timeline">
              {latestRun.failureDetail ? (
                <div className="timeline-item">
                  <strong>Failure detail</strong>
                  <div>
                    <p>{latestRun.failureDetail}</p>
                    <p className="tooltip">Outcome: {latestRun.enforcementOutcome}</p>
                  </div>
                </div>
              ) : (
                <div className="timeline-item">
                  <strong>Pass condition</strong>
                  <div>
                    <p>Enforcement outcome recorded as pass; compliance confirmed without retries.</p>
                    <p className="tooltip">Outcome: {latestRun.enforcementOutcome}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
