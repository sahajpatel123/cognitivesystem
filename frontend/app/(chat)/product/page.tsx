"use client";

import { motion } from "framer-motion";
import Link from "next/link";

const overlays = [
  { title: "What should I say?", copy: "Context-aware suggestions surface in a soft, rounded bubble." },
  { title: "Follow-up email", copy: "Drafts appear while the call is still in progress." },
  { title: "Speaker insight", copy: "A gentle card explains who is speaking and their background." },
];

const flow = [
  { title: "Capture", copy: "The app listens locally—no bots, no transcripts in the cloud." },
  { title: "Guide", copy: "Cards float above your call with questions, answers, and nudges." },
  { title: "Deliver", copy: "Recaps, tasks, and follow-ups are ready the moment you hang up." },
];

const reassurance = [
  "Everything renders on your desktop, not in the meeting.",
  "Animations follow Cluely’s pacing: soft fades, gentle lifts.",
  "Buttons, pills, and dropdowns share the same gradient rhythm.",
];

export default function ProductPage() {
  return (
    <motion.div className="page-frame" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}>
      <section className="hero">
        <div>
          <h1>The product experience.</h1>
          <p>Quiet overlays, Mac-style polish, and humane language—just like Cluely.</p>
          <div className="hero-actions">
            <Link href="/pricing">See pricing</Link>
            <Link href="/" className="ghost-link">
              Back to home
            </Link>
          </div>
        </div>

        <motion.div className="hero-window" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
          <div className="mac-window">
            <div className="mac-titlebar">
              <span className="mac-dot" />
              <span className="mac-dot" />
              <span className="mac-dot" />
            </div>
            <div className="window-overlay">Live overlay</div>
            <div className="window-caption">“Ask about their renewal timeline and confirm budget owners.”</div>
          </div>
        </motion.div>
      </section>

      <section className="section">
        <div className="section-header">
          <span className="eyebrow">Overlays</span>
          <h2>Mac-style windows, zero clutter.</h2>
          <p>Cards stack with consistent spacing, matching Cluely’s depth and tone.</p>
        </div>
        <div className="card-grid">
          {overlays.map((item) => (
            <article key={item.title} className="feature-card">
              <h3>{item.title}</h3>
              <p>{item.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-header">
          <h2>How it flows.</h2>
          <p>Three steps with matching cards, soft shadows, and confident spacing.</p>
        </div>
        <div className="steps-grid">
          {flow.map((step) => (
            <div key={step.title} className="step-card">
              <h3>{step.title}</h3>
              <p>{step.copy}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-header">
          <h2>Why teams trust it.</h2>
        </div>
        <div className="trust-ribbon">
          {reassurance.map((item) => (
            <p key={item} className="trust-note">
              {item}
            </p>
          ))}
        </div>
      </section>

      <section className="cta-panel">
        <h3>Ready for the calmest AI experience?</h3>
        <p>Install the Mac app and feel the same premium finish you saw above.</p>
        <Link href="/pricing">Choose a plan</Link>
      </section>
    </motion.div>
  );
}
