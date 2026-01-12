const supportStatements = [
  {
    title: "Designed to be inspectable",
    description: "Support interactions rely on the same immutable logs exposed in the product. We do not paraphrase or soften enforcement results.",
  },
  {
    title: "Deterministic playbooks",
    description: "Procedures follow contract-aligned steps. Every escalation references the exact clauses surfaced in the interface.",
  },
  {
    title: "No hidden triage",
    description: "Operators see the same status changes we do. There are no silent remediations or off-channel fixes.",
  },
];

const responseFlow = [
  {
    label: "1. Capture evidence",
    detail: "Provide enforcement IDs, timestamps, and affected surfaces. We reference ledger entries, not summaries.",
  },
  {
    label: "2. Validate contracts",
    detail: "We restate applicable Phase clauses and confirm whether the reported behavior aligns with certified outcomes.",
  },
  {
    label: "3. Resolve in the open",
    detail: "Resolution steps are documented in the audit trail. If remediation requires changes, new certification is triggered.",
  },
];

export default function SupportPage() {
  return (
    <div className="surface-stack">
      <div className="page-header">
        <span className="status-strip">Company</span>
        <h2>Support</h2>
        <p>Assistance focused on maintaining deterministic behavior, not introducing workarounds or personas.</p>
      </div>

      <section className="surface-content surface-entrance" data-motion="card">
        <h3 className="section-heading">What to expect</h3>
        <p className="section-caption">Support keeps the same tone as the interface: direct, confident, and contract-faithful.</p>
        <div className="surface-grid">
          {supportStatements.map((statement) => (
            <div key={statement.title} className="card">
              <h4 className="section-subheading">{statement.title}</h4>
              <p>{statement.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="surface-content surface-entrance" data-motion="panel">
        <h3 className="section-heading">Engagement flow</h3>
        <p className="section-caption">We reduce uncertainty by anchoring every interaction to visible evidence.</p>
        <div className="timeline">
          {responseFlow.map((entry) => (
            <div key={entry.label} className="timeline-item">
              <strong>{entry.label}</strong>
              <p>{entry.detail}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="surface-content surface-entrance" data-motion="panel">
        <h3 className="section-heading">Immediate assistance</h3>
        <p className="section-caption">Choose a path based on the evidence you have. We will reference contract language first.</p>
        <div className="surface-columns">
          <div className="card">
            <h4 className="section-subheading">Ledger anomaly</h4>
            <p>If enforcement outcomes differ from expected posture, include execution ID and ledger reference. We cross-check within minutes.</p>
          </div>
          <div className="card">
            <h4 className="section-subheading">Interface clarity</h4>
            <p>Questions about copy or grouping? We confirm phrasing against certified language before suggesting changes.</p>
          </div>
          <aside className="hero-card">
            <h3>Support posture</h3>
            <p className="helper-text">Trust through visibility, not persuasion. We escalate rather than speculate.</p>
            <div className="divider-soft" />
            <p className="landing-footnote">Contact ops@cognitivesystem.interface for urgent enforcement issues.</p>
          </aside>
        </div>
      </section>
    </div>
  );
}
