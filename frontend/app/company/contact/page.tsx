const contactChannels = [
  {
    label: "Certification inquiries",
    detail: "certification@cognitivesystem.interface",
    description: "Coordinate Phase 5 assessments, review artifacts, and schedule operator walkthroughs.",
  },
  {
    label: "Operator support",
    detail: "ops@cognitivesystem.interface",
    description: "Escalate enforcement observations, request trace excerpts, or confirm session posture.",
  },
  {
    label: "Integration coordination",
    detail: "integration@cognitivesystem.interface",
    description: "Plan adapter deployment timelines and schema validation checkpoints.",
  },
];

const officeHours = [
  {
    title: "Structured touchpoints",
    items: [
      "Weekly enforcement review with designated operator leads",
      "Monthly audit readiness alignment",
      "Quarterly contract reaffirmation",
    ],
  },
  {
    title: "Response commitments",
    items: [
      "Critical enforcement issues: response within 2 hours",
      "Operational questions: response within 1 business day",
      "Certification document requests: response within 3 business days",
    ],
  },
];

export default function ContactPage() {
  return (
    <div className="surface-stack">
      <div className="page-header">
        <span className="status-strip">Company</span>
        <h2>Contact</h2>
        <p>Reach the team directly responsible for maintaining deterministic behavior and certification posture.</p>
      </div>

      <section className="surface-content surface-entrance" data-motion="card">
        <h3 className="section-heading">Primary channels</h3>
        <p className="section-caption">Every channel routes to humans accountable for contract fidelity—not assistants.</p>
        <div className="surface-grid">
          {contactChannels.map((channel) => (
            <div key={channel.label} className="card">
              <span className="pill">{channel.label}</span>
              <h4 className="section-subheading">{channel.detail}</h4>
              <p>{channel.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="surface-content surface-entrance" data-motion="panel">
        <h3 className="section-heading">Coordination cadence</h3>
        <p className="section-caption">Touchpoints reinforce transparency. Nothing happens off-channel.</p>
        <div className="surface-columns">
          {officeHours.map((group) => (
            <div key={group.title} className="card">
              <h4 className="section-subheading">{group.title}</h4>
              <ul className="list-minor">
                {group.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ))}
          <aside className="hero-card">
            <h3>Escalation posture</h3>
            <p className="helper-text">If enforcement or audit visibility is ever questioned, we stop deployment until clarity is restored.</p>
            <div className="divider-soft" />
            <p className="landing-footnote">Designed to be inspectable. No chatbots. No automated commitments.</p>
          </aside>
        </div>
      </section>
    </div>
  );
}
