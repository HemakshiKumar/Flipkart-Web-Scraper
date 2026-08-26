"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { AlertTriangle, RotateCcw, SearchX, WifiOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { ApiErrorCode } from "@/lib/types";

interface StatusStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}

function StatusState({ icon, title, description, action }: StatusStateProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.section
      initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="flex flex-col items-center gap-4 rounded-xl border border-border/80 bg-card px-6 py-16 text-center"
      role="status"
    >
      <span className="flex size-11 items-center justify-center rounded-full border border-border bg-surface-muted text-muted-foreground">
        {icon}
      </span>
      <div className="space-y-1.5">
        <h2 className="text-lg font-bold tracking-tight">{title}</h2>
        <p className="mx-auto max-w-sm text-balance text-sm text-muted-foreground">{description}</p>
      </div>
      {action}
    </motion.section>
  );
}

export function EmptyState({ onRetry }: { onRetry?: () => void }) {
  return (
    <StatusState
      icon={<SearchX className="size-5" aria-hidden />}
      title="No products found"
      description="Try broadening your search or relaxing your requirements — a lower rating floor or a higher budget usually helps."
      action={
        <div className="flex flex-wrap items-center justify-center gap-2">
          {onRetry ? (
            <Button variant="outline" onClick={onRetry}>
              <RotateCcw aria-hidden />
              Try again
            </Button>
          ) : null}
          <Button asChild>
            <Link href="/">New search</Link>
          </Button>
        </div>
      }
    />
  );
}

const ERROR_COPY: Record<ApiErrorCode, { title: string; description: string }> = {
  scraping_failed: {
    title: "We couldn't retrieve products",
    description:
      "Flipkart didn't return usable results for this search. Please try again in a moment.",
  },
  network_error: {
    title: "The recommendation service is unreachable",
    description:
      "The engine isn't responding. Make sure the recommendation service is running, then try again.",
  },
  invalid_request: {
    title: "That search wasn't valid",
    description: "Check the product, the requirements and the number of recommendations.",
  },
  no_results: {
    title: "No products found",
    description: "Nothing matched those requirements. Try relaxing them.",
  },
  internal_error: {
    title: "Something went wrong",
    description: "The recommendation pipeline failed. Please try again in a moment.",
  },
};

export function ErrorState({
  code = "internal_error",
  message,
  onRetry,
}: {
  code?: ApiErrorCode;
  message?: string;
  onRetry?: () => void;
}) {
  const copy = ERROR_COPY[code] ?? ERROR_COPY.internal_error;
  const icon =
    code === "network_error" ? (
      <WifiOff className="size-5" aria-hidden />
    ) : (
      <AlertTriangle className="size-5" aria-hidden />
    );

  return (
    <StatusState
      icon={icon}
      title={copy.title}
      description={message ?? copy.description}
      action={
        <div className="flex flex-wrap items-center justify-center gap-2">
          {onRetry ? (
            <Button onClick={onRetry}>
              <RotateCcw aria-hidden />
              Try again
            </Button>
          ) : null}
          <Button variant="outline" asChild>
            <Link href="/">New search</Link>
          </Button>
        </div>
      }
    />
  );
}
