"use client";

import { motion, useReducedMotion } from "motion/react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { formatScore } from "@/lib/format";
import { cn } from "@/lib/utils";

interface ScoreMeterProps {
  score: number;
  similarity: number;
  /** Stagger index, so the meter fills in step with its row. */
  index?: number;
  className?: string;
}

/**
 * Relevance score as a hairline meter. Deliberately monochrome - the ranking
 * order carries the meaning, not a colour scale.
 */
export function ScoreMeter({ score, similarity, index = 0, className }: ScoreMeterProps) {
  const reduceMotion = useReducedMotion();
  const percentage = Math.round(score * 100);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn("flex items-center gap-2.5", className)}
          tabIndex={0}
          role="img"
          aria-label={`Relevance score ${percentage} percent`}
        >
          <span className="relative h-1 w-14 overflow-hidden rounded-full bg-border">
            <motion.span
              className="absolute inset-y-0 left-0 rounded-full bg-foreground"
              initial={reduceMotion ? { width: `${percentage}%` } : { width: 0 }}
              animate={{ width: `${percentage}%` }}
              transition={{
                duration: 0.55,
                delay: reduceMotion ? 0 : 0.12 + index * 0.04,
                ease: [0.22, 1, 0.36, 1],
              }}
            />
          </span>
          <span className="text-xs tabular-nums text-foreground">
            {formatScore(score)}
          </span>
        </span>
      </TooltipTrigger>
      <TooltipContent>
        <p className="font-medium">Relevance {formatScore(score)}</p>
        <p className="text-muted-foreground">
          Text match {formatScore(similarity)} · blended with rating and review reliability.
        </p>
      </TooltipContent>
    </Tooltip>
  );
}
