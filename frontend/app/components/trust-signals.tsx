"use client";

export function TrustSignals() {
  const trustCards = [
    {
      eyebrow: "POLICY",
      title: "Guardrails stay on",
      description: "Runs are constrained by declared policies—no hidden bypasses.",
      bullets: ["Explicit allowlists", "Refusal paths are logged"],
    },
    {
      eyebrow: "DATA",
      title: "Privacy boundary",
      description: "User data stays within defined boundaries. No surprise sharing.",
      bullets: ["Scoped access", "Least-privilege tooling"],
    },
  ];

  const socialLinks = [
    {
      name: "X / Twitter",
      href: "https://twitter.com",
      subtext: "Daily updates",
    },
    {
      name: "LinkedIn",
      href: "https://linkedin.com",
      subtext: "Professional network",
    },
    {
      name: "GitHub",
      href: "https://github.com",
      subtext: "Build with us",
    },
    {
      name: "YouTube",
      href: "https://youtube.com",
      subtext: "Demos & tutorials",
    },
    {
      name: "Discord",
      href: "https://discord.com",
      subtext: "Join the community",
    },
  ];

  return (
    <section id="transparent-by-design" className="trust-signals-section">
      <div className="trust-signals-container">
        <div className="trust-signals-header">
          <h2 className="trust-signals-title">Transparent by design</h2>
          <p className="trust-signals-subtitle">
            Governance-first by default. Clear boundaries. Audit-ready outputs.
          </p>
        </div>

        <div className="trust-cards">
          {trustCards.map((card) => (
            <div key={card.eyebrow} className="trust-card">
              <span className="trust-card-eyebrow">{card.eyebrow}</span>
              <h3 className="trust-card-title">{card.title}</h3>
              <p className="trust-card-description">{card.description}</p>
              <ul className="trust-card-bullets">
                {card.bullets.map((bullet) => (
                  <li key={bullet}>{bullet}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="socials-horizontal-section">
          <div className="socials-horizontal-header">
            <h3 className="socials-horizontal-title">Follow the build</h3>
            <p className="socials-horizontal-subtitle">Updates, demos, and milestones—no noise.</p>
          </div>
          <div className="socials-horizontal-grid">
            {socialLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="social-card"
              >
                <span className="social-card-name">{link.name}</span>
                <span className="social-card-subtext">{link.subtext}</span>
              </a>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
