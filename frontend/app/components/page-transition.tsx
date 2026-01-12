"use client";

import { AnimatePresence, motion } from "framer-motion";
import { usePathname } from "next/navigation";

const transition = { duration: 0.28, ease: [0.32, 0.02, 0.24, 1] };

export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <AnimatePresence mode="wait">
      <motion.main
        key={pathname}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={transition}
        className={`page-frame${pathname === "/" ? " is-landing" : ""}`}
      >
        {children}
      </motion.main>
    </AnimatePresence>
  );
}
