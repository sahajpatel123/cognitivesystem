import Link from "next/link";

export const metadata = {
  title: "Privacy Policy",
  description: "Privacy practices for the Cognitive System prototype",
};

export default function PrivacyPage() {
  const today = new Date().toISOString().split("T")[0];
  return (
    <main className="legal-page">
      <h1>Privacy Policy</h1>
      <p className="legal-meta">Version: {today}</p>

      <section>
        <h2>What we collect</h2>
        <ul>
          <li>Anon session cookie (httpOnly) to keep rate limits consistent.</li>
          <li>Session identifiers and bounded quota/rate counters.</li>
          <li>Minimal invocation metadata: route, status_code, latency_ms, error_code, hashed_subject, session_id.</li>
          <li>No raw user_text, prompts, or chat transcripts are stored.</li>
        </ul>
      </section>

      <section>
        <h2>Retention</h2>
        <ul>
          <li>Metadata is retained for short, bounded windows to enforce quotas and audit abuse.</li>
          <li>We rotate and purge according to operational needs; no long-term transcripts exist.</li>
        </ul>
      </section>

      <section>
        <h2>How we use data</h2>
        <ul>
          <li>Protect the service (WAF, rate limits, quotas, circuit breakers).</li>
          <li>Operate sessions and anon cookies; optional Supabase JWT verification.</li>
          <li>Monitor health and reliability with passive, redacted observability.</li>
        </ul>
      </section>

      <section>
        <h2>Subprocessors</h2>
        <ul>
          <li>Frontend hosting: Vercel.</li>
          <li>Backend hosting: Railway (FastAPI).</li>
          <li>Database/Auth: Supabase Postgres + Supabase Auth.</li>
          <li>Model provider(s): configured per environment (keys kept in env vars).</li>
        </ul>
      </section>

      <section>
        <h2>Security</h2>
        <ul>
          <li>Secrets are stored in environment variables; least-privilege access.</li>
          <li>Bounded metadata only; no transcript storage.</li>
          <li>Governed model calls with rate limits and circuit breakers.</li>
        </ul>
      </section>

      <section>
        <h2>User rights & contact</h2>
        <ul>
          <li>Contact us to request deletion of anon session or metadata: support@yourdomain.com.</li>
          <li>Provide any request_id or session identifier to help us locate records.</li>
        </ul>
      </section>

      <section>
        <h2>International transfers</h2>
        <p>Services may operate globally via our hosting and subprocessors. We use standard safeguards and minimal data scope.</p>
      </section>

      <section>
        <h2>Changes</h2>
        <p>We may update this policy; material changes are dated above. Continued use means acceptance.</p>
      </section>

      <section>
        <h2>Related documents</h2>
        <p>
          See the <Link href="/acceptable-use">Acceptable Use Policy</Link> for prohibited uses and the{" "}
          <Link href="/terms">Terms of Service</Link> for contractual terms.
        </p>
      </section>
    </main>
  );
}
