export const metadata = {
  title: "Acceptable Use Policy",
  description: "Usage rules for the Cognitive System prototype",
};

export default function AcceptableUsePage() {
  const today = new Date().toISOString().split("T")[0];
  return (
    <main className="legal-page">
      <h1>Acceptable Use Policy</h1>
      <p className="legal-meta">Version: {today}</p>

      <section>
        <h2>Prohibited behavior</h2>
        <ul>
          <li>No illegal content or activity.</li>
          <li>No harassment, threats, or encouragement of violence or self-harm.</li>
          <li>No hateful content targeting protected classes.</li>
          <li>No attempts to extract secrets, prompts, or system internals.</li>
          <li>No prompt injection to bypass controls or WAF/plan guard.</li>
        </ul>
      </section>

      <section>
        <h2>Security and abuse</h2>
        <ul>
          <li>No DoS, spam, scraping, credential stuffing, or automated abuse.</li>
          <li>No reverse engineering or exploiting vulnerabilities.</li>
          <li>Respect rate limits, quotas, and lockouts; do not evade them.</li>
        </ul>
      </section>

      <section>
        <h2>Use of outputs</h2>
        <ul>
          <li>Do not use outputs for unlawful purposes or to mislead others.</li>
          <li>Do not present outputs as professional advice (medical, legal, financial).</li>
          <li>Verify outputs independently before acting on them.</li>
        </ul>
      </section>

      <section>
        <h2>Enforcement</h2>
        <ul>
          <li>We may enforce rate limits, quotas, lockouts, or suspend access upon violations.</li>
          <li>Severe abuse may be reported to hosting or relevant authorities.</li>
        </ul>
      </section>

      <section>
        <h2>Contact</h2>
        <p>Email: support@yourdomain.com</p>
      </section>
    </main>
  );
}
