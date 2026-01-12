"use client";

import { motion } from "framer-motion";
import type { HTMLAttributes, PropsWithChildren } from "react";

interface SectionRevealProps extends HTMLAttributes<HTMLDivElement> {
  delay?: number;
}

export function SectionReveal({ children, delay = 0, className, ...rest }: PropsWithChildren<SectionRevealProps>) {
  return (
    <motion.div
      {...rest}
      className={className}
      initial={{ opacity: 0, y: 32 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay }}
      viewport={{ once: true, amount: 0.35 }}
    >
      {children}
    </motion.div>
  );
}
