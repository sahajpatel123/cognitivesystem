"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { NAV_ITEMS } from "../lib/static-data";

const transition = { duration: 0.24, ease: [0.4, 0, 0.2, 1] };

export function NavRail() {
  const pathname = usePathname();

  return (
    <nav className="nav-rail" aria-label="Primary">
      <h1>Cognitive System Control Surface</h1>
      <p className="nav-subtitle">
        Certified human interface exposing reasoning, expression, enforcement, and audit posture without ambiguity.
      </p>
      <div className="contract-banner">
        <strong>Phase 5 certification</strong>
        Phase 1–4 contracts are immutable. No memory, autonomy, or persona.
      </div>
      <div className="nav-section">
        <span className="nav-label">Surfaces</span>
        <div className="nav-surface">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <div key={item.href} className="nav-item-wrapper">
                {isActive && (
                  <motion.span
                    layoutId="nav-active"
                    className="nav-active-indicator"
                    transition={transition}
                  />
                )}
                <Link href={item.href} className={isActive ? "active" : ""}>
                  <span className="nav-item-label">{item.label}</span>
                  <span className="helper-text">{item.description}</span>
                </Link>
              </div>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
