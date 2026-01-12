"use client";

import { motion } from "framer-motion";

const blobs = [
  {
    id: "one",
    className: "one",
    duration: 26,
    x: 32,
    y: -20,
    scale: 1.1,
  },
  {
    id: "two",
    className: "two",
    duration: 30,
    x: -26,
    y: 26,
    scale: 1.05,
  },
  {
    id: "three",
    className: "three",
    duration: 34,
    x: 16,
    y: -28,
    scale: 1.12,
  },
];

export function SoftBackground() {
  return (
    <div className="soft-background" aria-hidden>
      {blobs.map((blob) => (
        <motion.span
          key={blob.id}
          className={`background-blob ${blob.className}`}
          animate={{
            x: [0, blob.x, 0],
            y: [0, blob.y, 0],
            scale: [1, blob.scale, 1],
            opacity: [0.55, 0.9, 0.55],
          }}
          transition={{
            duration: blob.duration,
            repeat: Infinity,
            ease: [0.45, 0.05, 0.18, 1],
          }}
        />
      ))}
      <motion.div
        className="background-grid"
        animate={{ opacity: [0.2, 0.35, 0.2] }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}
