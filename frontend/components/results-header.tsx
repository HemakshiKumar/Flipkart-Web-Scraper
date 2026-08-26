"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { ArrowLeft } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { splitRequirements } from "@/lib/format";
import type { RecommendResponse } from "@/lib/types";

interface ResultsHeaderProps {
  query: string;
  requirements: string;
  response?: RecommendResponse;
}

export function ResultsHeader({ query, requirements, response }: ResultsHeaderProps) {
  const reduceMotion = useReducedMotion();
  const chips = splitRequirements(requirements);

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
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
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
    </motion.header>
  );
}
