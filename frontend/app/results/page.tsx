import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { ResultsView } from "@/components/results-view";
import { SearchForm } from "@/components/search-form";
import {
  MAX_QUERY_LENGTH,
  MAX_REQUIREMENTS_LENGTH,
  MIN_QUERY_LENGTH,
  clampLimit,
} from "@/lib/validation";

export const metadata: Metadata = { title: "Results" };

function firstValue(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value)?.trim() ?? "";
}

export default async function ResultsPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;

  const query = firstValue(params.q).slice(0, MAX_QUERY_LENGTH);
  const requirements = firstValue(params.r).slice(0, MAX_REQUIREMENTS_LENGTH);
  const limit = clampLimit(firstValue(params.n));

  // A bookmarked or hand-edited URL without a usable query goes back home
  // rather than rendering a broken results page.
  if (query.length < MIN_QUERY_LENGTH) {
    redirect("/");
  }

  return (
    <div className="mx-auto w-full max-w-5xl flex-1 px-5 py-10 sm:px-8 sm:py-14">
      <ResultsView query={query} requirements={requirements} limit={limit} />

      <section className="mt-16 border-t border-border/60 pt-10">
        <h2 className="mb-5 text-sm font-medium text-muted-foreground">Refine this search</h2>
        <div className="rounded-xl border border-border/80 bg-card/50 p-5 backdrop-blur-sm">
          <SearchForm compact defaults={{ query, requirements, limit }} />
        </div>
      </section>
    </div>
  );
}
