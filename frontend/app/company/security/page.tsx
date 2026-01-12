const guarantees = [
  {
    title: "Immutable audit trails",
    description: "All pipeline executions, enforcement decisions, and operator escalations are logged in append-only stores surfaced in the UI.",
  },
  {
    title: "Schema-bound adapters",
    description: "Adapters enforce structure on ingress and egress. No unbounded transformations or hidden enrichment layers are introduced.",
  },
  {
    title: "Fail-closed enforcement",
    description: "Violations halt execution and surface exact contract clauses. There is no self-healing or silent retry.",
  },
];

const policies = [
  {
    label: "Access",
    detail: "Operator accounts use hardware-bound MFA and principle of least privilege. No shared credentials exist.",
  },
  {
    label: "Data handling",
    detail: "Payload retention follows TTL rules exposed in the Session surface. Out-of-scope content is rejected before storage.",
  },
  {
    label: "Change control",
    detail: "Any adjustment to reasoning, enforcement, or copy requires re-certification. We do not hotfix core behavior.",
  },
];

export default function SecurityPage() {
  return (
    <div className="surface-stack">
      <div className="page-header">
        <span className="status-strip">Company</span>
        <h2>Security</h2>
        <p>Security posture is anchored to the same deterministic contracts that govern the Cognitive System interface.</p>
      </div>

      <section className="surface-content surface-entrance" data-motion="card">
        <h3 className="section-heading">What stays locked</h3>
        <p className="section-caption">Security controls enforce the same guarantees the product exposes.</p>
        <div className="surface-grid">
          {guarantees.map((item) => (
            <div key={item.title} className="card">
              <h4 className="section-subheading">{item.title}</h4>
              <p>{item.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="surface-content surface-entrance" data-motion="panel">
        <h3 className="section-heading">Operational policies</h3>
        <p className="section-caption">Policies are public and aligned with what operators see inside the product.</p>
        <div className="surface-columns">
          <div className="card">
            <ul className="list-minor">
              {policies.map((policy) => (
                <li key={policy.label}>
                  <strong>{policy.label}:</strong> {policy.detail}
                </li>
              ))}
            </ul>
          </div>
          <aside className="hero-card">
            <h3>Zero dark corners</h3>
            <p className="helper-text">No background processes operate outside this disclosure. If an incident occurs, the enforcement ledger records it in real time.</p>
            <div className="divider-soft" />
            <p className="landing-footnote">Security questionnaires reference the same copy you see here.</p>
          </aside>
        </div>
      </section>
    </div>
  );
}
