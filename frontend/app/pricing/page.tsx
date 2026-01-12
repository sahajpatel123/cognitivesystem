"use client";

import { motion } from "framer-motion";
import Link from "next/link";

const tiers = [
  {
    name: "Starter",
    price: "Included",
    summary: "Everything you saw on the homepage and product demo—ready to install.",
    perks: ["macOS app", "Invisible presence", "Instant recap"],
  },
  {
    name: "Guided rollout",
    price: "Custom",
    summary: "We help your team adopt the product with workshops and copy polish.",
    perks: ["Team onboarding", "Usage playbooks", "Priority support"],
  },
  {
    name: "Enterprise",
    price: "Talk to us",
    summary: "Compliance-ready deployment with bespoke assurances.",
    perks: ["Dedicated manager", "Custom legal reviews", "SLA-backed support"],
  },
];

export default function PricingPage() {
  return (
    <motion.div className="page-frame" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      <section className="hero">
        <div>
          <h1 className="hero-heading">Pricing that mirrors Cluely.</h1>
          <p className="hero-sub">Simple cards, calm gradients, same rhythm.</p>
        </div>
      </section>

      <section className="section">
        <h2 className="section-heading">Plans</h2>
        <p className="section-sub">Choose the engagement style that matches your rollout.</p>
        <div className="card-grid">
          {tiers.map((tier) => (
            <article key={tier.name} className="pricing-card">
              <span className="mini-pill">{tier.name}</span>
              <strong>{tier.price}</strong>
              <p>{tier.summary}</p>
              <ul>
                {tier.perks.map((perk) => (
                  <li key={perk}>{perk}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="cta-banner">
        <h3>Questions?</h3>
        <p>We’ll walk through each plan on a quick call.</p>
        <Link href="/company/contact">Talk to us</Link>
      </section>
    </motion.div>
  );
}
