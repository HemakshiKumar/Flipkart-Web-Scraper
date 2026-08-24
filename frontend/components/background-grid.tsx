"use client";

import { motion, useReducedMotion } from "motion/react";

/**
 * Page texture: a hairline grid, a whisper of noise, and one slow-moving glow.
 * Everything here is decorative and hidden from assistive technology.
 */
export function BackgroundGrid() {
  const reduceMotion = useReducedMotion();

  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 bg-grid [mask-image:radial-gradient(ellipse_at_50%_0%,black,transparent_78%)]" />
      <div className="absolute inset-0 opacity-[0.035] bg-noise mix-blend-overlay dark:opacity-[0.05]" />
      <motion.div
        className="absolute left-1/2 top-[-18rem] size-[42rem] -translate-x-1/2 rounded-full blur-3xl"
        style={{
          background:
            "radial-gradient(circle, color-mix(in oklab, var(--foreground) 12%, transparent), transparent 68%)",
        }}
        animate={reduceMotion ? undefined : { scale: [1, 1.08, 1], opacity: [0.55, 0.8, 0.55] }}
        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="absolute inset-x-0 bottom-0 h-64 bg-gradient-to-t from-background to-transparent" />
    </div>
  );
}
