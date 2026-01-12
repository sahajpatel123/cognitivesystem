import Link from "next/link";
import { PrimaryMetrics } from "../components/primary-metrics";
import {
  AUDIT_RUNS,
  ENFORCEMENT_ENTRIES,
  INITIAL_RUN,
  NAV_ITEMS,
  SESSION_BASELINE,
} from "../lib/static-data";
import {
  formatPipelineState,
  formatRiskClassification,
  formatSecondsAsClock,
  operationalPatternLabel,
} from "../lib/formatters";

const overviewDirectory = NAV_ITEMS.filter((item) => item.href !== "/");

export default function SystemOverviewPage() {
  const metrics = [
    {
      label: "Session scope",
      value: operationalPatternLabel(SESSION_BASELINE.operationalPattern),
      tooltip: "Bounded by Phase 4 operational patterns.",
    },
    {
      label: "Session TTL",
      value: formatSecondsAsClock(SESSION_BASELINE.ttlSeconds),
      tooltip: "No cross-session memory or retention.",
    },
    {
      label: "Execution state",
      value: formatPipelineState(INITIAL_RUN.state),
      tooltip: "Deterministic pipeline status.",
      state: INITIAL_RUN.state,
    },
    {
      label: "Risk status",
      value: formatRiskClassification(INITIAL_RUN.riskClassification),
      tooltip: "Risk envelope from Phase 4.",
    },
  ];

  const latestEnforcement = ENFORCEMENT_ENTRIES.slice(0, 3);

  return (
    <div className="system-page">
      <div className="page-header">
        <span className="status-strip">Phase 5 certified interface</span>
        <h2>System overview</h2>
        <p>Certified control surface exposing reasoning, expression, enforcement, and audit guarantees.</p>
      </div>

      <PrimaryMetrics metrics={metrics} />

      <section className="surface-content surface-entrance" data-motion="card">
        <div className="surface-columns">
          <div className="vertical-stack">
            <h3 className="section-heading">Certified surfaces</h3>
            <p className="section-caption">Each surface enforces deterministic visibility for Phase 1–5 contracts.</p>
            <div className="directory-grid">
              {overviewDirectory.map((item) => (
                <Link key={item.href} href={item.href} className="directory-card" aria-label={item.label}>
                  <h3>{item.label}</h3>
                  <p>{item.description}</p>
                </Link>
              ))}
            </div>
          </div>
          <aside className="hero-card" aria-label="Deterministic exposure summary">
            <h3>Deterministic exposure</h3>
            <p className="helper-text">Certified control surface exposing reasoning, expression, enforcement, and audit guarantees.</p>
            <div className="divider-soft" />
            <ul className="calm-list">
              <li>
                <span className="pill">Reasoning</span>
                <span>Reasoning and expression remain isolated stages.</span>
              </li>
              <li>
                <span className="pill">Enforcement</span>
                <span>Enforcement is fail-closed; no adaptive retries.</span>
              </li>
              <li>
                <span className="pill">Visibility</span>
                <span>UI must surface enforcement and risk classifications without concealment.</span>
              </li>
            </ul>
          </aside>
        </div>
      </section>

      <section className="surface-content surface-entrance" data-motion="panel">
        <div className="surface-columns reverse">
          <div className="vertical-stack">
            <div className="card">
              <h3>Latest execution posture</h3>
              <p className="section-caption">Execution ID: {INITIAL_RUN.id}</p>
              <p className="helper-text">{INITIAL_RUN.reasoningTrace.summary}</p>
              <div className="metric-callout">
                <strong>State</strong>
                <span>{formatPipelineState(INITIAL_RUN.state)}</span>
              </div>
              <div className="metric-callout">
                <strong>Risk envelope</strong>
                <span>{INITIAL_RUN.riskClassification}</span>
              </div>
              <div className="metric-callout">
                <strong>Enforcement outcome</strong>
                <span>{INITIAL_RUN.enforcementOutcome}</span>
              </div>
              <details className="fold" aria-label="Reasoning trace detail">
                <summary>
                  Reasoning trace steps <span>Trace remains fully visible.</span>
                </summary>
                <div className="fold-body">
                  <ul className="list-minor">
                    {INITIAL_RUN.reasoningTrace.steps.map((step) => (
                      <li key={step.id}>
                        <span className="code-chip">{step.status}</span> {step.description}
                      </li>
                    ))}
                  </ul>
                </div>
              </details>
            </div>
          </div>
          <aside className="card" aria-label="Adapter metadata">
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

      <section className="surface-content surface-entrance" data-motion="table">
        <div className="surface-columns">
          <div className="card">
            <h3>Operational patterns in scope</h3>
            <p className="section-caption">Direct excerpts from Phase 4 deployment framing.</p>
            <ul className="list-minor">
              {overviewDirectory.map((item) => (
                <li key={item.href}>{item.description}</li>
              ))}
            </ul>
          </div>
          <details className="fold" aria-label="Recent enforcement events">
            <summary>
              Recent enforcement events <span>Recorded enforcement outcomes and violations.</span>
            </summary>
            <div className="fold-body">
              <div className="timeline">
                {latestEnforcement.map((entry) => (
                  <div key={entry.id} className="timeline-item">
                    <strong>{entry.timestamp}</strong>
                    <div>
                      <p className="detail-emphasis">{entry.violationClass}</p>
                      <p>{entry.detail}</p>
                      <p className="tooltip">Outcome: {entry.outcome}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </details>
        </div>
      </section>

      <section className="surface-content surface-entrance" data-motion="panel">
        <div className="surface-columns">
          <div className="card">
            <h3 className="section-heading">Audit excerpts</h3>
            <p className="section-caption">Immutable execution history sample within retention window.</p>
            <div className="surface-summary">
              {AUDIT_RUNS.slice(0, 3).map((run) => (
                <div key={run.id} className="card">
                  <span className="section-label">Execution ID</span>
                  <span className="code-chip">{run.id}</span>
                  <p className="tooltip">Timestamp: {run.timestamp}</p>
                  <p className="tooltip">State: {run.state}</p>
                  <p className="tooltip">Risk: {run.riskClassification}</p>
                </div>
              ))}
            </div>
          </div>
          <aside className="card">
            <h3>History drilldown</h3>
            <p className="helper-text">Immutable execution history remains navigable without overwhelming the default surface.</p>
            <div className="divider-soft" />
            <details className="fold" aria-label="Execution history list">
              <summary>
                Execution history <span>Immutable execution history within retention scope.</span>
              </summary>
              <div className="fold-body">
                <ul className="history-list">
                  {AUDIT_RUNS.map((run) => (
                    <li key={run.id}>
                      <div className="control-row" style={{ justifyContent: "space-between" }}>
                        <span className="code-chip">{run.id}</span>
                        <span className="code-chip">{run.timestamp}</span>
                      </div>
                      <p className="tooltip">State: {run.state}</p>
                      <p className="tooltip">Risk: {run.riskClassification}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </details>
          </aside>
        </div>
      </section>
    </div>
  );
}
