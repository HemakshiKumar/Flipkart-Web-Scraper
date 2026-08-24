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
        <motion.div variants={item} className="flex justify-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-muted/60 px-3 py-1 text-xs text-muted-foreground">
            <span className="relative flex size-1.5">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-foreground/40" />
              <span className="relative inline-flex size-1.5 rounded-full bg-foreground/70" />
            </span>
            Live Flipkart data · TF-IDF ranking
          </span>
        </motion.div>

        <motion.h1
          variants={item}
          className="text-balance text-4xl font-semibold tracking-tight sm:text-5xl"
        >
          Intelligent product discovery
        </motion.h1>

        <motion.p
          variants={item}
          className="mx-auto max-w-md text-balance text-base leading-relaxed text-muted-foreground sm:text-lg"
        >
          Find the best products based on what you actually want — described in plain English.
        </motion.p>
      </div>

      <motion.div variants={item}>{children}</motion.div>

      <motion.ol
        variants={item}
        className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 font-mono text-[0.7rem] uppercase tracking-widest text-muted-foreground"
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
