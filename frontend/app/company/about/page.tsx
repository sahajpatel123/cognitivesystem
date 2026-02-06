"use client";

import Link from "next/link";
import { motion } from "framer-motion";

const principles = [
  {
    title: "Deterministic execution",
    description: "Same inputs + policy = consistent outputs. No silent rewrites, no surprises.",
  },
  {
    title: "Session boundaries",
    description: "Sealed context by default. No accidental memory bleed across conversations.",
  },
  {
    title: "Auditable outputs",
    description: "Tool calls + constraints logged. Easy to review what happened and why.",
  },
];

const buildingBlocks = [
  "Multi-agent orchestration",
  "Guardrails + policy engine",
  "Tool sandboxing + permissions",
  "Trace logs + replayable runs",
  "Human override / escalation paths",
];

export default function AboutPage() {
  return (
    <motion.div
      className="page-frame"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Hero Section */}
      <section className="hero" style={{ paddingTop: "120px", paddingBottom: "80px" }}>
        <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "0 24px" }}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.6 }}
          >
            <p
              style={{
                fontSize: "13px",
                fontWeight: 600,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "rgba(59, 130, 246, 0.8)",
                marginBottom: "16px",
              }}
            >
              COMPANY
            </p>
            <h1
              style={{
                fontSize: "clamp(36px, 5vw, 56px)",
                fontWeight: 600,
                lineHeight: 1.1,
                marginBottom: "20px",
                color: "#1e293b",
              }}
            >
              Built for governed intelligence.
            </h1>
            <p
              style={{
                fontSize: "18px",
                lineHeight: 1.6,
                color: "rgba(30, 41, 59, 0.7)",
                maxWidth: "720px",
                marginBottom: "40px",
              }}
            >
              We build AI systems with safety, auditability, and deterministic behavior at the core.
              Privacy by default. Policy-first execution.
            </p>

            {/* Stat Cards */}
            <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
              <div
                style={{
                  padding: "16px 24px",
                  background: "rgba(255, 255, 255, 0.7)",
                  backdropFilter: "blur(12px)",
                  border: "1px solid rgba(255, 255, 255, 0.5)",
                  borderRadius: "12px",
                  boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)",
                  fontSize: "14px",
                  fontWeight: 500,
                  color: "#475569",
                }}
              >
                Policy-first execution
              </div>
              <div
                style={{
                  padding: "16px 24px",
                  background: "rgba(255, 255, 255, 0.7)",
                  backdropFilter: "blur(12px)",
                  border: "1px solid rgba(255, 255, 255, 0.5)",
                  borderRadius: "12px",
                  boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)",
                  fontSize: "14px",
                  fontWeight: 500,
                  color: "#475569",
                }}
              >
                Auditable by default
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Principles Section */}
      <section style={{ padding: "80px 24px", maxWidth: "1100px", margin: "0 auto" }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
        >
          <h2
            style={{
              fontSize: "32px",
              fontWeight: 600,
              marginBottom: "48px",
              color: "#1e293b",
              textAlign: "center",
            }}
          >
            Principles
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: "24px",
            }}
          >
            {principles.map((principle, idx) => (
              <motion.div
                key={principle.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 + idx * 0.1, duration: 0.6 }}
                style={{
                  padding: "32px",
                  background: "rgba(255, 255, 255, 0.6)",
                  backdropFilter: "blur(20px)",
                  border: "1px solid rgba(255, 255, 255, 0.4)",
                  borderRadius: "16px",
                  boxShadow: "0 8px 24px rgba(0, 0, 0, 0.06)",
                }}
              >
                <h3
                  style={{
                    fontSize: "18px",
                    fontWeight: 600,
                    marginBottom: "12px",
                    color: "#1e293b",
                  }}
                >
                  {principle.title}
                </h3>
                <p style={{ fontSize: "15px", lineHeight: 1.6, color: "rgba(30, 41, 59, 0.7)" }}>
                  {principle.description}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* What We're Building Section */}
      <section style={{ padding: "80px 24px", maxWidth: "1100px", margin: "0 auto" }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.6 }}
          style={{
            padding: "48px",
            background: "rgba(255, 255, 255, 0.6)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(255, 255, 255, 0.4)",
            borderRadius: "20px",
            boxShadow: "0 12px 32px rgba(0, 0, 0, 0.08)",
          }}
        >
          <h2
            style={{
              fontSize: "28px",
              fontWeight: 600,
              marginBottom: "32px",
              color: "#1e293b",
            }}
          >
            What we're building
          </h2>
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {buildingBlocks.map((block, idx) => (
              <li
                key={block}
                style={{
                  fontSize: "16px",
                  lineHeight: 1.8,
                  color: "rgba(30, 41, 59, 0.8)",
                  paddingLeft: "28px",
                  position: "relative",
                  marginBottom: idx < buildingBlocks.length - 1 ? "16px" : 0,
                }}
              >
                <span
                  style={{
                    position: "absolute",
                    left: 0,
                    top: "8px",
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    background: "#3b82f6",
                  }}
                />
                {block}
              </li>
            ))}
          </ul>
        </motion.div>
      </section>

      {/* Footer CTA */}
      <section style={{ padding: "80px 24px 120px", maxWidth: "1100px", margin: "0 auto" }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.6 }}
          style={{
            padding: "48px",
            background: "linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(147, 197, 253, 0.1))",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(59, 130, 246, 0.2)",
            borderRadius: "20px",
            boxShadow: "0 12px 32px rgba(59, 130, 246, 0.1)",
            textAlign: "center",
          }}
        >
          <h3
            style={{
              fontSize: "24px",
              fontWeight: 600,
              marginBottom: "24px",
              color: "#1e293b",
            }}
          >
            Try the governed chat surface.
          </h3>
          <div style={{ display: "flex", gap: "16px", justifyContent: "center", flexWrap: "wrap" }}>
            <Link
              href="/product/chat"
              style={{
                display: "inline-block",
                padding: "14px 32px",
                background: "#3b82f6",
                color: "white",
                borderRadius: "12px",
                fontSize: "15px",
                fontWeight: 600,
                textDecoration: "none",
                boxShadow: "0 4px 12px rgba(59, 130, 246, 0.3)",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.boxShadow = "0 6px 16px rgba(59, 130, 246, 0.4)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = "0 4px 12px rgba(59, 130, 246, 0.3)";
              }}
            >
              Open Chat
            </Link>
            <Link
              href="/company/contact"
              style={{
                display: "inline-block",
                padding: "14px 32px",
                background: "rgba(255, 255, 255, 0.8)",
                color: "#3b82f6",
                borderRadius: "12px",
                fontSize: "15px",
                fontWeight: 600,
                textDecoration: "none",
                border: "1px solid rgba(59, 130, 246, 0.3)",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 1)";
                e.currentTarget.style.transform = "translateY(-2px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.8)";
                e.currentTarget.style.transform = "translateY(0)";
              }}
            >
              Contact
            </Link>
          </div>
        </motion.div>
      </section>
    </motion.div>
  );
}
