const pillars = [
  {
    title: "Deliberate constraints",
    description: "We build every surface to foreground certifiable limits. No optional feature can bypass the contracts you review.",
  },
  {
    title: "Inspectable systems",
    description: "Interfaces expose reasoning, enforcement, and audit data directly. Trust is earned through visibility, not persuasion.",
  },
  {
    title: "Calm delivery",
    description: "The product is designed to orient operators quickly without removing the precision required for certified work.",
  },
];

const timeline = [
  {
    label: "Phase 1",
    detail: "Established cognitive contracts and separated reasoning from expression."
  },
  {
    label: "Phase 3",
    detail: "Integrated schema-bound adapters with stateless guarantees across deployments."
  },
  {
    label: "Phase 5",
    detail: "Certified the control surface to expose enforcement and audit posture without omission."
  },
];

export default function AboutPage() {
  return (
    <div className="surface-stack">
      <div className="page-header">
        <span className="status-strip">Company</span>
        <h2>Built with deliberate constraints</h2>
        <p>We craft deterministic interfaces that preserve Phase 1–5 semantics while presenting them with calm assurance.</p>
      </div>

      <section className="surface-content surface-entrance" data-motion="card">
        <div className="company-columns">
          <div className="company-hero">
            <h3>Principles</h3>
            <p>Every product decision reinforces the same contract-bound behavior that governs the Cognitive System. No hidden flows, no persuasive language.</p>
            <ul className="company-list">
              {pillars.map((pillar) => (
                <li key={pillar.title}>
                  <span className="pill">{pillar.title}</span>
                  <span>{pillar.description}</span>
                </li>
              ))}
            </ul>
            <p className="company-note">All public statements mirror the enforcement language inside the product.</p>
          </div>
          <aside className="card">
            <h3>What we uphold</h3>
            <p className="helper-text">Reasoning, execution, and enforcement transparency remain non-negotiable across every release.</p>
            <ul className="landing-pill-list">
              <li>
                <span className="pill">No personas</span>
                <span>We do not anthropomorphize. The system speaks in contract terms only.</span>
              </li>
              <li>
                <span className="pill">Fail-closed</span>
                <span>Violations never self-heal or disappear. Operators see the full ledger.</span>
              </li>
              <li>
                <span className="pill">Clarity first</span>
                <span>Human-friendly hierarchy helps orientation without weakening guarantees.</span>
              </li>
            </ul>
          </aside>
        </div>
      </section>

      <section className="surface-content surface-entrance" data-motion="panel">
        <h3 className="section-heading">Certification milestones</h3>
        <p className="section-caption">Progress anchored to the same audit trails exposed inside the product.</p>
        <div className="timeline">
          {timeline.map((entry) => (
            <div key={entry.label} className="timeline-item">
              <strong>{entry.label}</strong>
              <p>{entry.detail}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
