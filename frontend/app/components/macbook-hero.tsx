"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion, useScroll, useTransform } from "framer-motion";
import { LiveClock } from "./LiveClock";

const tabs = [
  { id: "guidance", label: "Guidance" },
  { id: "summary", label: "Summary" },
  { id: "safeguards", label: "Safeguards" },
] as const;

type TabKey = (typeof tabs)[number]["id"];

const tabContent: Record<
  TabKey,
  {
    rows: { title: string; body: string; badge: string }[];
    panels: { copy: string; label: string }[];
  }
> = {
  guidance: {
    rows: [
      { title: "Active session", body: "Policy-governed agent run — awaiting input", badge: "Live" },
      { title: "Operation mode", body: "Verified mode · auditable steps · deterministic tools", badge: "Pinned" },
      { title: "Next step", body: "Select objective → constraints → tools → output format", badge: "Ready" },
    ],
    panels: [
      { copy: "Every action is logged. Every tool call is traceable.", label: "Trace log" },
      { copy: "A safe plan is generated before execution. You approve the final run.", label: "Control layer" },
    ],
  },
  summary: {
    rows: [
      { title: "Key output", body: "Drafted a compliant multi-agent workflow with checkpoints.", badge: "Notes" },
      { title: "Decisions", body: "Guardrails enabled: data boundaries + tool allowlist.", badge: "Locked" },
      { title: "Action items", body: "Connect sources → run evaluation → promote to production.", badge: "Due" },
    ],
    panels: [
      { copy: "3 runs compared across cost, latency, and reliability.", label: "Evaluation" },
      { copy: "Incident-ready audit trail prepared for export.", label: "Report" },
    ],
  },
  safeguards: {
    rows: [
      { title: "Compliance status", body: "In-policy · access scoped · retention controlled.", badge: "Clear" },
      { title: "Safety constraints", body: "No secrets exfiltration · no untrusted tools · no unsafe actions.", badge: "Tone" },
      { title: "Risk flags", body: "Zero policy violations in last 48 hours.", badge: "Low" },
    ],
    panels: [
      { copy: "Role-based access enforced for agents and connectors.", label: "Access control" },
      { copy: "Live guardrails block risky phrasing and unsafe tool use.", label: "Active enforcement" },
    ],
  },
};

export function MacbookHero() {
  const heroRef = useRef<HTMLDivElement | null>(null);
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ["start end", "end start"] });
  const tilt = useTransform(scrollYProgress, [0, 1], [-2, -8]);
  const float = useTransform(scrollYProgress, [0, 1], [0, -18]);
  const [activeTab, setActiveTab] = useState<TabKey>("guidance");

  return (
    <div className="device-stage" ref={heroRef}>
      <motion.div className="device-shell" style={{ rotateX: tilt, y: float }}>
        <div className="device-screen">
          <div className="device-chrome">
            <div className="device-lights">
              <span />
              <span />
              <span />
            </div>
            <div className="device-status">
              <span>COGNITIVE SYSTEM</span>
              <LiveClock />
            </div>
          </div>

          <div className="device-window">
            <div className="window-header">
              <div className="window-tabs" role="tablist" aria-label="Call surface views">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    role="tab"
                    aria-selected={activeTab === tab.id}
                    tabIndex={activeTab === tab.id ? 0 : -1}
                    className={`window-tab${activeTab === tab.id ? " active" : ""}`}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <div className="window-signal" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
            </div>

            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                className="window-body"
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
              >
                {tabContent[activeTab].rows.map((row) => (
                  <div key={row.title} className="window-row">
                    <div>
                      <p>{row.title}</p>
                      <strong>{row.body}</strong>
                    </div>
                    <span className="window-badge">{row.badge}</span>
                  </div>
                ))}

                <div className="window-panels">
                  {tabContent[activeTab].panels.map((panel) => (
                    <motion.div
                      key={panel.label}
                      className="window-panel"
                      animate={{ opacity: [0.85, 1, 0.85], y: [0, -6, 0] }}
                      transition={{ duration: 6, repeat: Infinity, ease: [0.65, 0, 0.35, 1], delay: 0.2 }}
                    >
                      <p>{panel.copy}</p>
                      <span>{panel.label}</span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        <motion.div className="device-shadow" animate={{ opacity: [0.35, 0.55, 0.35] }} transition={{ duration: 7, repeat: Infinity }} />
      </motion.div>
    </div>
  );
}
