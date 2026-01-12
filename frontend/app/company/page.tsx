"use client";

import { motion } from "framer-motion";
import Link from "next/link";

const cards = [
  {
    title: "About",
    copy: "Read the calm story behind Cognitive System.",
    href: "/company/about",
  },
  {
    title: "Contact",
    copy: "Reach the team directly—no forms, no bots.",
    href: "/company/contact",
  },
  {
    title: "Support",
    copy: "We respond with the same friendly tone you see here.",
    href: "/company/support",
  },
  {
    title: "Security",
    copy: "See the safeguards that stay on by default.",
    href: "/company/security",
  },
];

export default function CompanyPage() {
  return (
    <motion.div className="page-frame" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      <section className="hero">
        <div>
          <h1 className="hero-heading">Company</h1>
          <p className="hero-sub">Same layout and pacing as Cluely’s supporting page.</p>
        </div>
      </section>

      <section className="card-grid">
        {cards.map((card) => (
          <Link key={card.title} href={card.href} className="company-card">
            <h4>{card.title}</h4>
            <p>{card.copy}</p>
          </Link>
        ))}
      </section>

      <section className="cta-banner">
        <h3>Need more details?</h3>
        <p>We’ll share everything live.</p>
        <Link href="/product">Book a session</Link>
      </section>
    </motion.div>
  );
}
