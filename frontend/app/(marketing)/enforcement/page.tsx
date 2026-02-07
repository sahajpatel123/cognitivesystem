import { PrimaryMetrics } from "../../components/primary-metrics";
import { ENFORCEMENT_ENTRIES, INITIAL_RUN } from "../../lib/static-data";
import { formatPipelineState, formatRiskClassification } from "../../lib/formatters";

const totalEntries = ENFORCEMENT_ENTRIES.length;
const rejectedCount = ENFORCEMENT_ENTRIES.filter((entry) => entry.outcome === "rejected").length;
const containedCount = ENFORCEMENT_ENTRIES.filter((entry) => entry.outcome === "contained").length;
const criticalCount = ENFORCEMENT_ENTRIES.filter((entry) => entry.severity === "critical").length;

const severityOrder = ["critical", "high", "medium", "low"] as const;

function severityRank(severity: (typeof severityOrder)[number]) {
  return severityOrder.indexOf(severity);
}

const sortedEntries = [...ENFORCEMENT_ENTRIES].sort((a, b) => severityRank(a.severity) - severityRank(b.severity));

export default function EnforcementLedgerPage() {
  const metrics = [
    {
      label: "Ledger entries",
      value: `${totalEntries} recorded`,
      tooltip: "Every enforcement event is immutable and timestamped.",
    },
    {
      label: "Rejected outcomes",
      value: `${rejectedCount} enforcement rejections`,
      tooltip: "Fail-closed enforcement prevents downstream expression.",
    },
    {
      label: "Contained outcomes",
      value: `${containedCount} contained violations`,
      tooltip: "Contained violations required no external escalation.",
    },
    {
      label: "Critical severity",
      value: `${criticalCount} critical incidents`,
      tooltip: "Critical incidents trigger mandatory operator review.",
    },
  ];

  return (
    <div className="surface-stack">
      <div className="page-header">
        <span className="status-strip">Enforcement & failure ledger</span>
        <h2>Immutable enforcement archive</h2>
        <p>Enforcement records expose structural, semantic, and boundary violations without concealment or aggregation.</p>
      </div>

      <PrimaryMetrics metrics={metrics} />

      <section className="surface-content surface-entrance" data-motion="card">
        <div className="surface-columns">
          <div className="card">
            <h3 className="section-heading">Latest execution enforcement</h3>
            <p className="section-caption">Execution ID: {INITIAL_RUN.id}</p>
            <div className="vertical-stack">
              <div>
                <span className="section-label">Pipeline state</span>
                <p className="helper-text">{formatPipelineState(INITIAL_RUN.state)}</p>
              </div>
              <div>
                <span className="section-label">Risk envelope</span>
                <p className="helper-text">{formatRiskClassification(INITIAL_RUN.riskClassification)}</p>
              </div>
              <div>
                <span className="section-label">Enforcement outcome</span>
                <p className="helper-text">{INITIAL_RUN.enforcementOutcome}</p>
              </div>
            </div>
          </div>
          <aside className="card">
            <h3>Operator note</h3>
            <p className="helper-text">Reasoning and expression remained in certified posture. Outcome recorded without retries or suppression.</p>
          </aside>
        </div>
      </section>

      <section className="surface-content surface-entrance" data-motion="table">
        <div className="surface-columns">
          <div className="card">
            <h3 className="section-heading">Ledger detail</h3>
            <p className="section-caption">Entries ordered by severity; no row is soft-deleted or rewritten.</p>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Timestamp</th>
                    <th scope="col">Stage</th>
                    <th scope="col">Violation</th>
                    <th scope="col">Severity</th>
                    <th scope="col">Outcome</th>
                    <th scope="col">Reference</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedEntries.map((entry) => (
                    <tr key={entry.id}>
                      <td>{entry.timestamp}</td>
                      <td>{entry.stage}</td>
                      <td>{entry.violationClass}</td>
                      <td>{entry.severity}</td>
                      <td>{entry.outcome}</td>
                      <td>{entry.reference}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <details className="fold" aria-label="Violation narratives">
            <summary>
              Violation narratives <span>Narratives expose cause and enforcement response.</span>
            </summary>
            <div className="fold-body">
              <div className="timeline">
                {sortedEntries.map((entry) => (
                  <div key={`${entry.id}-detail`} className="timeline-item">
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
    </div>
  );
}
