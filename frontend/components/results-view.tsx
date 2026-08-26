"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

import { LoadingState } from "@/components/loading-state";
import { ProductCard } from "@/components/product-card";
import { RecommendationTable } from "@/components/recommendation-table";
import { ResultsHeader } from "@/components/results-header";
import { EmptyState, ErrorState } from "@/components/status-state";
import { fetchRecommendations } from "@/lib/api";
import { RecommendationRequestError, type ApiErrorCode, type RecommendResponse } from "@/lib/types";

interface ResultsViewProps {
  query: string;
  requirements: string;
  limit: number;
}

type Status =
  | { phase: "loading" }
  | { phase: "ready"; data: RecommendResponse }
  | { phase: "error"; code: ApiErrorCode; message: string };

/**
 * Owns the retry counter. The actual request lives in `ResultsRequest`, which
 * is remounted (via `key`) whenever the search or the retry counter changes -
 * so its state always starts from a clean "loading" instead of being reset
 * from inside an effect.
 */
export function ResultsView({ query, requirements, limit }: ResultsViewProps) {
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt((value) => value + 1), []);

  return (
    <ResultsRequest
      key={`${query}|${requirements}|${limit}|${attempt}`}
      query={query}
      requirements={requirements}
      limit={limit}
      onRetry={retry}
    />
  );
}

function ResultsRequest({
  query,
  requirements,
  limit,
  onRetry,
}: ResultsViewProps & { onRetry: () => void }) {
  const [status, setStatus] = useState<Status>({ phase: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    fetchRecommendations({ query, requirements, limit }, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setStatus({ phase: "ready", data });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof RecommendationRequestError) {
          setStatus({ phase: "error", code: error.code, message: error.message });
          return;
        }
        setStatus({
          phase: "error",
          code: "internal_error",
          message: "Something went wrong while generating recommendations.",
        });
      });

    return () => controller.abort();
  }, [query, requirements, limit]);

  return (
    <div className="space-y-8">
      <ResultsHeader
        query={query}
        requirements={requirements}
        response={status.phase === "ready" ? status.data : undefined}
      />

      <AnimatePresence mode="wait">
        {status.phase === "loading" ? (
          <motion.div key="loading" exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
            <LoadingState rows={Math.min(limit, 6)} />
          </motion.div>
        ) : status.phase === "error" ? (
          <ErrorState key="error" code={status.code} message={status.message} onRetry={onRetry} />
        ) : status.data.results.length === 0 ? (
          <EmptyState key="empty" onRetry={onRetry} />
        ) : (
          <motion.div
            key="results"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.25 }}
            className="space-y-5"
          >
            <div className="hidden md:block">
              <RecommendationTable products={status.data.results} />
            </div>

            <ul className="space-y-3 md:hidden">
              {status.data.results.map((product, index) => (
                <ProductCard key={`${product.name}-${index}`} product={product} index={index} />
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
