"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

export function CursorGlow() {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [active, setActive] = useState(false);

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      setActive(true);
      setPosition({ x: event.clientX, y: event.clientY });
    };

    window.addEventListener("pointermove", handlePointerMove);
    return () => window.removeEventListener("pointermove", handlePointerMove);
  }, []);

  return (
    <motion.div
      className={`cursor-glow${active ? " is-active" : ""}`}
      aria-hidden
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{
        x: position.x - 160,
        y: position.y - 160,
        opacity: active ? 1 : 0,
        scale: active ? 1 : 0.8,
      }}
      transition={{ type: "spring", stiffness: 120, damping: 22 }}
    />
  );
}
