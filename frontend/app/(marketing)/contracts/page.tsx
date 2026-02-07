import { PrimaryMetrics } from "../../components/primary-metrics";
import { CONTRACT_SECTIONS, INITIAL_RUN } from "../../lib/static-data";
import { formatRiskClassification } from "../../lib/formatters";

const contractMetrics = [
  {
    label: "Contract pillars",
    value: "Phase 1 – Phase 4",
    tooltip: "Reasoning, expression, integration, and system framing remain locked.",
  },
  {
    label: "Enforcement posture",
    value: "Fail-closed",
    tooltip: "No self-healing or adaptive retries are permitted.",
  },
  {
    label: "Current risk envelope",
    value: formatRiskClassification(INITIAL_RUN.riskClassification),
    tooltip: "Contracts enforce visibility into the active risk classification.",
  },
  {
    label: "Reference revision",
    value: "Certified 2026-01-02",
    tooltip: "References match the locked Phase 5 certification timestamp.",
  },
];

export default function ContractReferencePage() {
  return (
    <div className="surface-stack">
      <div className="page-header">
        <span className="status-strip">Contract & constraint reference</span>
        <h2>Locked cognitive and integration clauses</h2>
        <p>Contracts remain immutable; this surface exposes operative language and enforcement signatures.</p>
      </div>

      <PrimaryMetrics metrics={contractMetrics} />

      <section className="surface-content surface-entrance" data-motion="card">
        <div className="surface-columns">
          <div className="card">
            <h3 className="section-heading">Contract index</h3>
            <p className="section-caption">Sections organized by certification phase. No modifications permitted.</p>
            <div className="vertical-stack">
              {CONTRACT_SECTIONS.map((section) => (
                <details key={section.id} className="fold" aria-label={section.title}>
                  <summary>
                    {section.title} <span>Immutable contract excerpts.</span>
                  </summary>
                  <div className="fold-body">
                    <ul className="list-minor">
                      {section.content.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </details>
              ))}
            </div>
          </div>
          <aside className="hero-card">
            <h3>Certification posture</h3>
            <p className="helper-text">Reasoning, expression, integration, and system framing remain locked. Enforcement is fail-closed.</p>
            <div className="divider-soft" />
            <ul className="calm-list">
              <li>
                <span className="pill">Phase 1</span>
                <span>Reasoning and expression remain isolated stages.</span>
              </li>
              <li>
                <span className="pill">Phase 3</span>
                <span>Adapter enforces schema-bound IO and stateless calls.</span>
              </li>
              <li>
                <span className="pill">Phase 4</span>
                <span>Risk envelope distinguishes low, elevated, and out-of-scope contexts.</span>
              </li>
            </ul>
          </aside>
        </div>
      </section>

      <section className="surface-content surface-entrance" data-motion="panel">
        <h3 className="section-heading">Operator guidance</h3>
        <p className="section-caption">Guidance clarifies intent; any deviation requires re-certification.</p>
        <div className="timeline">
          <div className="timeline-item">
            <strong>Cognitive separation</strong>
            <div>
              <p>Reasoning and expression must remain isolated. No single surface combines proposal and delivery.</p>
              <p className="tooltip">Violations escalate to structural enforcement with mandatory rejection.</p>
            </div>
          </div>
          <div className="timeline-item">
            <strong>Stateless integration</strong>
            <div>
              <p>Adapters operate without memory; all state appears explicitly on certified surfaces.</p>
              <p className="tooltip">Hidden state constitutes a contract breach.</p>
            </div>
          </div>
          <div className="timeline-item">
            <strong>Risk classification</strong>
            <div>
              <p>Risk transitions must appear instantly with supporting enforcement entries.</p>
              <p className="tooltip">Elevated or out-of-scope contexts demand operator acknowledgement.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
