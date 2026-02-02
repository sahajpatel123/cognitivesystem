"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { MacbookHero } from "./components/macbook-hero";
import { CardDeckSection } from "./components/card-deck-section";
import { SectionReveal } from "./components/section-reveal";
import { SocialsCelebration } from "./components/socials-celebration";

const signalMetrics = [
  {
    value: "312",
    label: "Deployments",
    detail: "Indicates the number of production environments where the system runs quietly and repeatedly.",
    secondary: "Shows the surface has been trusted enough to be promoted into production cycles repeatedly.",
    backTitle: "Execution model",
    backValue: "Synchronous, in-call only",
    backSubtext: "No rewrites or delayed prompts.",
    constraintTitle: "Deterministic execution",
    constraintBody: "All guidance is generated synchronously during the conversation. Nothing is revised after the moment passes.",
  },
  {
    value: "94%",
    label: "Adoption",
    detail: "Represents teams that continue using the surface after onboarding, showing the habit sticks.",
    secondary: "Signals that teams keep the assistant in their workflow after the initial rollout.",
    backTitle: "Memory boundary",
    backValue: "Session-scoped",
    backSubtext: "Nothing from one call touches the next.",
    constraintTitle: "Isolated session memory",
    constraintBody: "Each call is treated as a sealed environment. Context does not leak across meetings.",
  },
  {
    value: "41 ms",
    label: "Latency",
    detail: "Guidance appears quickly enough to stay within the conversation’s cadence.",
    secondary: "Keeps guidance invisible to the cadence of the speaker and listener.",
    backTitle: "Output discipline",
    backValue: "Guardrail-locked",
    backSubtext: "Tone, scope, and claims stay constrained.",
    constraintTitle: "Controlled output surface",
    constraintBody: "Suggestions are filtered through active guardrails for tone, scope, and intent before they appear.",
  },
];

export default function HomePage() {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <motion.main className="landing-shell" initial={{ opacity: 0.9 }} animate={{ opacity: 1 }}>
      <section id="hero-anchor" className="cinema-hero">
        <motion.div
          className="hero-copy"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, ease: [0.23, 1, 0.32, 1] }}
        >
          <span className="hero-eyebrow">Cognitive System</span>
          <h1 className="hero-title">The quietly confident AI companion for Mac.</h1>
          <p className="hero-subhead">
            A cinematic hero surface, glass-depth Mac window, and dock interactions that echo Cluely's polish. The system feels
            alive even when idle.
          </p>
          <div className="hero-cta">
            <Link href="/product" className="cta-mac">
              Get for Mac
            </Link>
            <Link href="/product#flow" className="cta-outline">
              Watch the walkthrough
            </Link>
          </div>
        </motion.div>

        <motion.div
          className="hero-visual"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.1, ease: [0.23, 1, 0.32, 1], delay: 0.1 }}
        >
          <MacbookHero />
        </motion.div>
      </section>

      <SectionReveal id="signal-anchor" className="insight-section">
        <div className="insight-panel" aria-label="Live system view">
          <div className="insight-panel-header">
            <div>
              <p>Quiet room · Cognitive System</p>
              <strong>Live guidance surface</strong>
            </div>
            <button
              type="button"
              className="insight-flip"
              onClick={() => setIsFlipped((prev) => !prev)}
              aria-pressed={isFlipped}
            >
              Flip
            </button>
          </div>

          <div className="insight-panel-body">
            {signalMetrics.map((metric) => (
              <article key={metric.label} className="insight-entry">
                <motion.div
                  className="insight-entry-card"
                  animate={{ rotateY: isFlipped ? 180 : 0 }}
                  transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
                >
                  <div className="insight-card-face insight-card-front">
                    <div className="insight-entry-value">{metric.value}</div>
                    <p>{metric.label}</p>
                  </div>
                  <div className="insight-card-face insight-card-back">
                    <span className="insight-back-label">{metric.backTitle}</span>
                    <strong>{metric.backValue}</strong>
                    <small>{metric.backSubtext}</small>
                  </div>
                </motion.div>
              </article>
            ))}
          </div>
        </div>

        <div className="insight-metrics">
          <span className="hero-eyebrow">Signal fidelity</span>
          <h2>Real-time cognitive guidance.</h2>
          <p>
            {isFlipped
              ? "The system operates under strict constraints designed for live use."
              : "The desktop surface follows the meeting, not the other way around."}
          </p>

          <div className="metric-stack-shell">
            <AnimatePresence mode="wait">
              {isFlipped ? (
                <motion.div
                  key="constraints"
                  className="metric-stack"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                >
                  {signalMetrics.map((metric) => (
                    <article key={metric.constraintTitle} className="metric-row">
                      <div className="metric-copy">
                        <h3>{metric.constraintTitle}</h3>
                        <p>{metric.constraintBody}</p>
                      </div>
                    </article>
                  ))}
                </motion.div>
              ) : (
                <motion.div
                  key="metrics"
                  className="metric-stack"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                >
                  {signalMetrics.map((metric) => (
                    <article key={metric.label} className="metric-row">
                      <div className="metric-value">{metric.value}</div>
                      <div className="metric-copy">
                        <h3>{metric.label}</h3>
                        <p>{metric.detail}</p>
                      </div>
                    </article>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </SectionReveal>

      <CardDeckSection />

      <SectionReveal className="socials-section">
        <div className="socials-box" aria-label="Social channels placeholder">
          <SocialsCelebration />
          <span>Socials</span>
        </div>
      </SectionReveal>

    </motion.main>
  );
}
