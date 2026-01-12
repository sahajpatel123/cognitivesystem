"use client";

import { motion } from "framer-motion";

const halos = [
  { id: "halo-1", duration: 42, delay: 0, scale: 1.05 },
  { id: "halo-2", duration: 56, delay: -10, scale: 1.15 },
];

const orbs = [
  { id: "orb-1", x: 40, y: -30, size: 320, duration: 38 },
  { id: "orb-2", x: -50, y: 20, size: 260, duration: 44 },
  { id: "orb-3", x: 10, y: 60, size: 280, duration: 52 },
];

export function AmbientField() {
  return (
    <div className="ambient-field" aria-hidden>
      <div className="ambient-noise" />
      {halos.map((halo) => (
        <motion.div
          key={halo.id}
          className="ambient-halo"
          animate={{ opacity: [0.4, 0.85, 0.4], scale: [1, halo.scale, 1] }}
          transition={{ duration: halo.duration, delay: halo.delay, repeat: Infinity, ease: [0.42, 0, 0.25, 1] }}
        />
      ))}
      {orbs.map((orb) => (
        <motion.span
          key={orb.id}
          className="ambient-orb"
          style={{ width: orb.size, height: orb.size }}
          animate={{ x: [0, orb.x, 0], y: [0, orb.y, 0] }}
          transition={{ duration: orb.duration, repeat: Infinity, ease: [0.32, 0.02, 0.24, 0.99] }}
        />
      ))}
    </div>
  );
}
