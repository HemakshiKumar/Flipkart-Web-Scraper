"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { ArrowLeft, Database, Info, Timer } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { SOURCE_LABELS, formatDuration, splitRequirements } from "@/lib/format";
import type { RecommendResponse } from "@/lib/types";

interface ResultsHeaderProps {
  query: string;
  requirements: string;
  response?: RecommendResponse;
}

export function ResultsHeader({ query, requirements, response }: ResultsHeaderProps) {
  const reduceMotion = useReducedMotion();
  const chips = splitRequirements(requirements);
  const source = response ? SOURCE_LABELS[response.source] : undefined;
  const notes = response?.parsed.notes ?? [];

  return (
    <motion.header
      initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="space-y-5"
    >
      <Button variant="ghost" size="sm" asChild className="-ml-2 text-muted-foreground">
        <Link href="/">
          <ArrowLeft aria-hidden />
          New search
        </Link>
      </Button>

      <div className="space-y-3">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Recommended products
          </h1>
          {response ? (
            <span className="text-sm text-muted-foreground">
              {response.count} {response.count === 1 ? "result" : "results"}
            </span>
          ) : null}
        </div>

        <p className="text-lg text-foreground/90">{query}</p>

        {chips.length > 0 ? (
          <ul className="flex flex-wrap gap-1.5">
            {chips.map((chip) => (
              <li key={chip}>
                <Badge variant="outline" className="font-normal">
                  {chip}
                </Badge>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      {response ? (
        <>
          <Separator />
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground">
            {source ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="flex items-center gap-1.5" tabIndex={0}>
                    <Database className="size-3.5" aria-hidden />
                    {source.label}
                    <span className="text-muted-foreground/70">
                      · {response.datasetSize} products analysed
                    </span>
                  </span>
                </TooltipTrigger>
                <TooltipContent>{source.description}</TooltipContent>
              </Tooltip>
            ) : null}

            <span className="flex items-center gap-1.5">
              <Timer className="size-3.5" aria-hidden />
              {formatDuration(response.elapsedMs)}
            </span>

            {notes.length > 0 ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="flex items-center gap-1.5" tabIndex={0}>
                    <Info className="size-3.5" aria-hidden />
                    {notes.length} filter{notes.length === 1 ? "" : "s"} applied
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  <ul className="space-y-0.5">
                    {notes.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                </TooltipContent>
              </Tooltip>
            ) : null}
          </div>
        </>
      ) : null}
    </motion.header>
  );
}
