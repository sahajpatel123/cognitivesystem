"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { MacbookHero } from "../components/macbook-hero";
import { SectionReveal } from "../components/section-reveal";
import { RollingTape } from "../components/rolling-tape";
import { TrustSignals } from "../components/trust-signals";

const signalMetrics = [
  {
    value: "N/A",
    label: "Policies active",
    detail: "Guardrails applied across tools, data access, and response style. Policies are versioned and auditable.",
    secondary: "Shows the surface has been trusted enough to be promoted into production cycles repeatedly.",
    backTitle: "Execution model",
    backValue: "Deterministic, policy-first",
    backSubtext: "Constraints run before generation.",
    backOneLiner: "Same inputs. Same output.",
    constraintTitle: "Deterministic execution",
    constraintBody: "Same inputs under the same policy produce consistent behavior. No silent rewriting after the moment.",
  },
  {
    value: "≥ 98%",
    label: "In-policy target",
    detail: "Goal for interactions staying within defined boundaries without escalation. Designed for safe default behavior.",
    secondary: "Signals that teams keep the assistant in their workflow after the initial rollout.",
    backTitle: "Memory boundary",
    backValue: "Session-scoped by default",
    backSubtext: "No cross-session leakage.",
    backOneLiner: "Sealed context by default.",
    constraintTitle: "Isolated sessions",
    constraintBody: "Each session is treated as sealed context. You decide what persists—nothing leaks by default.",
  },
  {
    value: "≤ 60 ms",
    label: "Guardrail budget",
    detail: "Latency reserved for constraint checks + verification. Kept low enough to feel instant.",
    secondary: "Keeps guidance invisible to the cadence of the speaker and listener.",
    backTitle: "Audit trail",
    backValue: "Every action is logged",
    backSubtext: "Traceable inputs → outputs.",
    backOneLiner: "Every action is logged.",
    constraintTitle: "Auditable outputs",
    constraintBody: "Every tool call and constraint decision is recorded. Easy to review what happened and why.",
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
          <span className="hero-eyebrow">Governed AI · Private & Secure</span>
          <h1 className="hero-title">A Governed AI Multi-Agent Platform</h1>
          <p className="hero-subhead">
            Deploy and govern safe, auditable AI agents. Harness cognitive power while ensuring privacy, compliance, and full operational control.
          </p>
          <div className="hero-cta">
            <Link href="/product/chat" className="cta-mac">
              Chat
            </Link>
            <Link href="/product#flow" className="cta-outline">
              How it Works?
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
                <div className={`insight-entry-card${isFlipped ? ' is-flipped' : ''}`}>
                  <div className="insight-card-face insight-card-front">
                    <div className="metric-row">
                      <div className="metric-value">{metric.value}</div>
                      <div className="metric-label">{metric.label}</div>
                    </div>
                  </div>
                  <div className="insight-card-face insight-card-back">
                    <span className="insight-back-label">{metric.backTitle}</span>
                    <strong>{metric.backValue}</strong>
                    <small>{metric.backSubtext}</small>
                    <p className="metric-backline">{metric.backOneLiner}</p>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="insight-metrics">
          <span className="hero-eyebrow">{isFlipped ? "Safety guarantees" : "Governance signal"}</span>
          <h2>{isFlipped ? "Built for controlled operation." : "Real-time governed execution."}</h2>
          <p>
            {isFlipped
              ? "Clear boundaries, predictable behavior."
              : "Controls run before output reaches the user."}
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

      <RollingTape />

      <TrustSignals />

    </motion.main>
  );
}
