"use client";

import Link from "next/link";
import { motion } from "framer-motion";

const whatWeBuild = [
  {
    title: "Policy engine",
    description: "Rules that run before output. Constraints are enforced, not suggested.",
  },
  {
    title: "Tool permissions",
    description: "Explicit allow/deny + scopes. No ambient authority.",
  },
  {
    title: "Session boundaries",
    description: "Sealed context by default. You decide what persists.",
  },
  {
    title: "Audit trail",
    description: "Traceable tool calls + decisions. Every action is reviewable.",
  },
];

const howItWorks = [
  {
    step: "Intent + constraints",
    description: "You provide input and policy. The system validates boundaries before proceeding.",
  },
  {
    step: "Plan + tools",
    description: "The system plans actions, requests tool permissions, and executes within scope.",
  },
  {
    step: "Response + trace",
    description: "Output is returned with full audit trail. You can replay or review any decision.",
  },
];

const whyDifferent = [
  "Deterministic by design (same policy, consistent behavior).",
  "Memory is controlled (you decide what persists).",
  "Every action is reviewable (logs are first-class).",
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
                fontSize: "14px",
                fontWeight: 600,
                letterSpacing: "0.06em",
                color: "rgba(59, 130, 246, 0.9)",
                marginBottom: "12px",
              }}
            >
              Cognitive System
            </p>
            <p
              style={{
                fontSize: "13px",
                fontWeight: 600,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "rgba(59, 130, 246, 0.7)",
                marginBottom: "20px",
              }}
            >
              ABOUT
            </p>
            <h1
              style={{
                fontSize: "clamp(36px, 5vw, 56px)",
                fontWeight: 600,
                lineHeight: 1.1,
                marginBottom: "24px",
                color: "#1e293b",
              }}
            >
              Governed intelligence for real work.
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
              A governed AI system with policy-first execution. Reliable outputs, bounded memory, and auditable actions.
              Built for people who need control, not just convenience.
            </p>

            {/* CTA Buttons */}
            <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
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
        </div>
      </section>

      {/* What We Build Section */}
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
            What we build
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "24px",
            }}
          >
            {whatWeBuild.map((item, idx) => (
              <motion.div
                key={item.title}
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
                  {item.title}
                </h3>
                <p style={{ fontSize: "15px", lineHeight: 1.6, color: "rgba(30, 41, 59, 0.7)" }}>
                  {item.description}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* How It Works Section */}
      <section style={{ padding: "80px 24px", maxWidth: "1100px", margin: "0 auto" }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.6 }}
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
            How it works
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "24px",
            }}
          >
            {howItWorks.map((item, idx) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 + idx * 0.1, duration: 0.6 }}
                style={{
                  padding: "32px",
                  background: "rgba(255, 255, 255, 0.6)",
                  backdropFilter: "blur(20px)",
                  border: "1px solid rgba(255, 255, 255, 0.4)",
                  borderRadius: "16px",
                  boxShadow: "0 8px 24px rgba(0, 0, 0, 0.06)",
                  position: "relative",
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    top: "24px",
                    left: "24px",
                    width: "32px",
                    height: "32px",
                    borderRadius: "50%",
                    background: "rgba(59, 130, 246, 0.1)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "14px",
                    fontWeight: 600,
                    color: "#3b82f6",
                  }}
                >
                  {idx + 1}
                </div>
                <h3
                  style={{
                    fontSize: "18px",
                    fontWeight: 600,
                    marginBottom: "12px",
                    marginTop: "40px",
                    color: "#1e293b",
                  }}
                >
                  {item.step}
                </h3>
                <p style={{ fontSize: "15px", lineHeight: 1.6, color: "rgba(30, 41, 59, 0.7)" }}>
                  {item.description}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Why It's Different Section */}
      <section style={{ padding: "80px 24px", maxWidth: "1100px", margin: "0 auto" }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.6 }}
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
            Why it's different
          </h2>
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {whyDifferent.map((point, idx) => (
              <li
                key={idx}
                style={{
                  fontSize: "16px",
                  lineHeight: 1.8,
                  color: "rgba(30, 41, 59, 0.8)",
                  paddingLeft: "28px",
                  position: "relative",
                  marginBottom: idx < whyDifferent.length - 1 ? "20px" : 0,
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
                {point}
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
          transition={{ delay: 0.8, duration: 0.6 }}
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
              marginBottom: "12px",
              color: "#1e293b",
            }}
          >
            Ready to test governed chat?
          </h3>
          <p
            style={{
              fontSize: "15px",
              color: "rgba(30, 41, 59, 0.7)",
              marginBottom: "28px",
            }}
          >
            Safe by default, flexible when needed.
          </p>
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
        </motion.div>
      </section>
    </motion.div>
  );
}
