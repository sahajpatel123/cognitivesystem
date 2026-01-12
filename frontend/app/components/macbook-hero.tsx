"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion, useScroll, useTransform } from "framer-motion";

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
      { title: "Current call", body: "Investor sync – 14 min remaining", badge: "Live" },
      { title: "Tone guardrails", body: "Calm, confident, observational", badge: "Pinned" },
      { title: "Next action", body: "Share rollout cadence deck before Friday.", badge: "Ready" },
    ],
    panels: [
      { copy: "“We launch without announcing ourselves. Meet them calmly.”", label: "Real-time brief" },
      { copy: "Follow-up email draft is already staged with compliant tone.", label: "After-call" },
    ],
  },
  summary: {
    rows: [
      { title: "Key discussion", body: "Rolled through launch cadence + stakeholder map.", badge: "Notes" },
      { title: "Decisions made", body: "Greenlighted pilot for frontline enablement.", badge: "Locked" },
      { title: "Action items", body: "Send warm intro pack + compliance brief tonight.", badge: "Due" },
    ],
    panels: [
      { copy: "Three highlights and transcript snippets already clipped.", label: "Highlights" },
      { copy: "Auto-generated recap mail waiting in Drafts folder.", label: "Send-ready summary" },
    ],
  },
  safeguards: {
    rows: [
      { title: "Compliance status", body: "In-policy · SOC II / GDPR controls enforced.", badge: "Clear" },
      { title: "Tone constraints", body: "Stay calm, observational, never directive.", badge: "Tone" },
      { title: "Risk flags", body: "Zero escalations in last 48 hours.", badge: "Low" },
    ],
    panels: [
      { copy: "Policy alignment confirmed for finance + healthcare cohorts.", label: "Policy alignment" },
      { copy: "Live guardrails throttling any speculative phrasing.", label: "Active enforcement" },
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
              <span>Calm Speak</span>
              <span>10:24</span>
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
