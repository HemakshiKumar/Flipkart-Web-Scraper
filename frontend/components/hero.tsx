"use client";

import type { ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";

const STEPS = ["Scrape", "Clean", "Vectorise", "Rank"] as const;

export function Hero({ children }: { children: ReactNode }) {
  const reduceMotion = useReducedMotion();

  const container = {
    hidden: {},
    show: {
      transition: { staggerChildren: reduceMotion ? 0 : 0.08, delayChildren: 0.05 },
    },
  };

  const item = {
    hidden: reduceMotion ? { opacity: 0 } : { opacity: 0, y: 14 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] as const },
    },
  };

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-10">
      <div className="space-y-5 text-center">
        <motion.h1
          variants={item}
          className="mx-auto max-w-2xl text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl"
        >
          Find the best products based on what you actually want!
        </motion.h1>
      </div>

      <motion.div variants={item}>{children}</motion.div>

      <motion.ol
        variants={item}
        className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 text-xs uppercase tracking-widest text-muted-foreground"
      >
        {STEPS.map((step, index) => (
          <li key={step} className="flex items-center gap-2">
            <span>{step}</span>
            {index < STEPS.length - 1 ? <span aria-hidden className="opacity-40">→</span> : null}
          </li>
        ))}
      </motion.ol>
    </motion.div>
  );
}
