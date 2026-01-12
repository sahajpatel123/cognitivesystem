"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { COMPANY_NAV_LINKS, PRODUCT_NAV_LINKS } from "../lib/static-data";

const transition = { duration: 0.18, ease: [0.33, 0.11, 0.22, 1] };

type DropdownKey = "product" | "company" | null;

export function TopNav() {
  const pathname = usePathname();
  const [openKey, setOpenKey] = useState<DropdownKey>(null);

  const handleEnter = (key: DropdownKey) => setOpenKey(key);
  const handleLeave = () => setOpenKey(null);
  const toggle = (key: DropdownKey) => setOpenKey((current) => (current === key ? null : key));

  const isActive = (href: string) => (href === "/" ? pathname === href : pathname.startsWith(href));

  const renderDropdown = (key: DropdownKey, links: typeof PRODUCT_NAV_LINKS) => (
    <AnimatePresence>
      {openKey === key && (
        <motion.div
          className="dropdown-panel"
          initial={{ opacity: 0, y: 8, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 4, scale: 0.98 }}
          transition={transition}
        >
          <ul>
            {links.map((item) => (
              <li key={item.href}>
                <Link href={item.href} onClick={() => setOpenKey(null)}>
                  <span className="dropdown-label">{item.label}</span>
                  <span className="dropdown-helper">{item.helper}</span>
                </Link>
              </li>
            ))}
          </ul>
        </motion.div>
      )}
    </AnimatePresence>
  );

  return (
    <div className="site-nav">
      <div className="nav-inner">
        <div className="nav-brand-block">
          <Link href="/" className="nav-brand">
            Cognitive System
          </Link>
        </div>

        <nav className="nav-links" aria-label="Primary">
          <Link className={isActive("/") ? "active" : ""} href="/">
            Home
          </Link>

          <div
            className="nav-dropdown"
            onMouseEnter={() => handleEnter("product")}
            onMouseLeave={handleLeave}
            onFocus={() => handleEnter("product")}
            onBlur={(event) => {
              const next = event.relatedTarget as Node | null;
              if (!next || !(event.currentTarget as HTMLElement).contains(next)) {
                handleLeave();
              }
            }}
          >
            <button
              type="button"
              className={`nav-trigger ${openKey === "product" ? "active" : ""}`}
              aria-haspopup="true"
              aria-expanded={openKey === "product"}
              onClick={() => toggle("product")}
            >
              Product <span className="nav-caret" />
            </button>
            {renderDropdown("product", PRODUCT_NAV_LINKS)}
          </div>

          <Link className={isActive("/pricing") ? "active" : ""} href="/pricing">
            Pricing
          </Link>

          <div
            className="nav-dropdown"
            onMouseEnter={() => handleEnter("company")}
            onMouseLeave={handleLeave}
            onFocus={() => handleEnter("company")}
            onBlur={(event) => {
              const next = event.relatedTarget as Node | null;
              if (!next || !(event.currentTarget as HTMLElement).contains(next)) {
                handleLeave();
              }
            }}
          >
            <button
              type="button"
              className={`nav-trigger ${openKey === "company" ? "active" : ""}`}
              aria-haspopup="true"
              aria-expanded={openKey === "company"}
              onClick={() => toggle("company")}
            >
              Company <span className="nav-caret" />
            </button>
            {renderDropdown("company", COMPANY_NAV_LINKS)}
          </div>
        </nav>

        <div className="nav-cta">
          <Link href="/product">Get for Mac</Link>
        </div>
      </div>
    </div>
  );
}
