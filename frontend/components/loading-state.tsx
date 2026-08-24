"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Check } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/** Mirrors the real backend stages so the status text stays honest. */
const STAGES = [
  "Searching Flipkart…",
  "Reading product pages…",
  "Cleaning product data…",
  "Ranking recommendations…",
] as const;

const STAGE_INTERVAL_MS = 2200;

export function LoadingState({ rows = 6 }: { rows?: number }) {
  const [stage, setStage] = useState(0);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const timer = window.setInterval(() => {
      setStage((current) => Math.min(current + 1, STAGES.length - 1));
    }, STAGE_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="space-y-8" aria-busy="true">
      <div
        role="status"
        aria-live="polite"
        className="rounded-xl border border-border/80 bg-card/60 p-5 backdrop-blur-sm"
      >
        <ol className="space-y-2.5">
          {STAGES.map((label, index) => {
            const done = index < stage;
            const active = index === stage;
            return (
              <li
                key={label}
                className={cn(
                  "flex items-center gap-3 text-sm transition-colors duration-300",
                  done && "text-muted-foreground",
                  active && "text-foreground",
                  !done && !active && "text-muted-foreground/45",
                )}
              >
                <span className="flex size-4 items-center justify-center">
                  <AnimatePresence mode="wait" initial={false}>
                    {done ? (
                      <motion.span
                        key="done"
                        initial={reduceMotion ? false : { scale: 0.6, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="text-foreground/70"
                      >
                        <Check className="size-3.5" aria-hidden />
                      </motion.span>
                    ) : active ? (
                      <motion.span
                        key="active"
                        className="size-1.5 rounded-full bg-foreground"
                        animate={reduceMotion ? undefined : { opacity: [1, 0.3, 1] }}
                        transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
                      />
                    ) : (
                      <span key="idle" className="size-1.5 rounded-full bg-border" />
                    )}
                  </AnimatePresence>
                </span>
                <span>{label}</span>
                {active ? <AnimatedDots reduceMotion={Boolean(reduceMotion)} /> : null}
              </li>
            );
          })}
        </ol>
      </div>

      <div className="space-y-3" aria-hidden>
        {Array.from({ length: rows }).map((_, index) => (
          <div
            key={index}
            className="flex items-center gap-4 rounded-lg border border-border/60 p-4"
            style={{ opacity: 1 - index * 0.12 }}
          >
            <Skeleton className="h-4 w-2/5" />
            <Skeleton className="ml-auto h-4 w-10" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-14" />
            <Skeleton className="h-8 w-20 rounded-md" />
          </div>
        ))}
      </div>
    </div>
  );
}

function AnimatedDots({ reduceMotion }: { reduceMotion: boolean }) {
  if (reduceMotion) return null;
  return (
    <span className="flex items-center gap-1" aria-hidden>
      {[0, 1, 2].map((index) => (
        <motion.span
          key={index}
          className="size-1 rounded-full bg-foreground/60"
          animate={{ opacity: [0.2, 1, 0.2] }}
          transition={{ duration: 1.1, repeat: Infinity, delay: index * 0.18 }}
        />
      ))}
    </span>
  );
}
