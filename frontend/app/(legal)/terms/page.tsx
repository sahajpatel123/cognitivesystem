import Link from "next/link";

export const metadata = {
  title: "Terms of Service",
  description: "Usage terms for the Cognitive System prototype",
};

export default function TermsPage() {
  const today = new Date().toISOString().split("T")[0];
  return (
    <main className="legal-page">
      <h1>Terms of Service</h1>
      <p className="legal-meta">Version: {today}</p>

      <section>
        <h2>Who can use this service</h2>
        <ul>
          <li>Use only if you are 18+ and legally permitted in your region.</li>
          <li>No medical, legal, or financial advice. Verify independently.</li>
        </ul>
      </section>

      <section>
        <h2>Service nature</h2>
        <ul>
          <li>Provided “as is” without warranties.</li>
          <li>Subject to maintenance, rate limits, and quota enforcement.</li>
        </ul>
      </section>

      <section>
        <h2>User responsibilities</h2>
        <ul>
          <li>Provide lawful, non-abusive inputs.</li>
          <li>Do not attempt to bypass security, WAF, or rate limits.</li>
          <li>Respect intellectual property and third-party rights.</li>
        </ul>
      </section>

      <section>
        <h2>Prohibited conduct</h2>
        <p>See the <Link href="/acceptable-use">Acceptable Use Policy</Link> for specifics. Highlights:</p>
        <ul>
          <li>No spam, harassment, threats, or violence advocacy.</li>
          <li>No malicious automation, DoS, scraping, or credential attacks.</li>
          <li>No attempts to extract secrets, prompts, or bypass controls.</li>
        </ul>
      </section>

      <section>
        <h2>Enforcement</h2>
        <ul>
          <li>We may apply rate limits, quotas, lockouts, or suspend access to protect the service.</li>
          <li>Abuse may be reported to hosting providers if required.</li>
        </ul>
      </section>

      <section>
        <h2>Liability</h2>
        <ul>
          <li>No liability for indirect, incidental, or consequential damages.</li>
          <li>Total liability, if any, is limited to amounts paid (if any).</li>
        </ul>
      </section>

      <section>
        <h2>Changes</h2>
        <ul>
          <li>We may update these terms; continued use means acceptance.</li>
          <li>Material changes will be dated above.</li>
        </ul>
      </section>

      <section>
        <h2>Governing law</h2>
        <p>Jurisdiction: India (placeholder unless superseded by local requirements).</p>
      </section>

      <section>
        <h2>Contact</h2>
        <p>Email: support@yourdomain.com</p>
      </section>
    </main>
  );
}
