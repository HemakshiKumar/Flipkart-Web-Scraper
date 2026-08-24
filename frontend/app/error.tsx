"use client";

import { useEffect } from "react";

import { ErrorState } from "@/components/status-state";

/** Route-level error boundary. Details are logged, never rendered. */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[ui] route error", { digest: error.digest, message: error.message });
  }, [error]);

  return (
    <div className="mx-auto w-full max-w-2xl flex-1 px-5 py-24 sm:px-8">
      <ErrorState code="internal_error" onRetry={reset} />
    </div>
  );
}
