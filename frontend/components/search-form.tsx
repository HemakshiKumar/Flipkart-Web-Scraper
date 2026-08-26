"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight, Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  DEFAULT_LIMIT,
  LIMIT_OPTIONS,
  MAX_QUERY_LENGTH,
  MAX_REQUIREMENTS_LENGTH,
  MIN_QUERY_LENGTH,
  clampLimit,
  recommendRequestSchema,
} from "@/lib/validation";

const EXAMPLES = [
  { query: "Bluetooth headphones", requirements: ">4.5 rating, high battery life, under ₹5000" },
  { query: "Wireless earbuds", requirements: "good sound quality, noise cancellation" },
  { query: "Neckband", requirements: "battery life is more important than price" },
] as const;

export interface SearchFormDefaults {
  query?: string;
  requirements?: string;
  limit?: number;
}

interface SearchFormProps {
  defaults?: SearchFormDefaults;
  /** Compact layout is used on the results page. */
  compact?: boolean;
}

export function SearchForm({ defaults, compact = false }: SearchFormProps) {
  const router = useRouter();
  const reduceMotion = useReducedMotion();

  const [query, setQuery] = useState(defaults?.query ?? "");
  const [requirements, setRequirements] = useState(defaults?.requirements ?? "");
  const [limit, setLimit] = useState(String(clampLimit(defaults?.limit ?? DEFAULT_LIMIT)));
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = recommendRequestSchema.safeParse({ query, requirements, limit });

    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Check your search and try again.");
      return;
    }

    setError(null);
    setSubmitting(true);

    const params = new URLSearchParams({
      q: parsed.data.query,
      n: String(parsed.data.limit),
    });
    if (parsed.data.requirements) params.set("r", parsed.data.requirements);
    router.push(`/results?${params.toString()}`);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={cn("w-full space-y-5", compact && "space-y-4")}
      noValidate
    >
      <Field
        label="What are you looking for?"
        htmlFor="query"
        hint={`${query.length}/${MAX_QUERY_LENGTH}`}
      >
        <div className="relative">
          <Search
            aria-hidden
            className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            id="query"
            name="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Bluetooth headphones"
            maxLength={MAX_QUERY_LENGTH}
            minLength={MIN_QUERY_LENGTH}
            autoComplete="off"
            autoFocus={!compact}
            required
            aria-invalid={Boolean(error) && query.trim().length < MIN_QUERY_LENGTH}
            aria-describedby={error ? "search-error" : undefined}
            className="h-12 pl-10 text-base"
          />
        </div>
      </Field>

      <Field
        label="What matters to you?"
        htmlFor="requirements"
        hint={`${requirements.length}/${MAX_REQUIREMENTS_LENGTH}`}
      >
        <Textarea
          id="requirements"
          name="requirements"
          value={requirements}
          onChange={(event) => setRequirements(event.target.value)}
          placeholder="&gt;4.5 rating, high battery life, under ₹5000"
          maxLength={MAX_REQUIREMENTS_LENGTH}
          rows={compact ? 2 : 3}
          className="text-base"
          aria-describedby="requirements-help"
        />
        <p id="requirements-help" className="text-xs text-muted-foreground">
          Plain English works: ratings, budgets, features and priorities are all parsed into filters.
        </p>
      </Field>

      <div className="flex flex-col gap-4 pt-1 sm:flex-row sm:items-end sm:justify-between">
        <div className="w-full space-y-2 sm:w-40">
          <Label htmlFor="limit">Recommendations</Label>
          <Select value={limit} onValueChange={setLimit}>
            <SelectTrigger id="limit" aria-label="Number of recommendations">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LIMIT_OPTIONS.map((option) => (
                <SelectItem key={option} value={String(option)}>
                  {option} products
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <motion.div
          whileHover={reduceMotion ? undefined : { scale: 1.01 }}
          whileTap={reduceMotion ? undefined : { scale: 0.99 }}
          className="w-full sm:w-auto"
        >
          <Button type="submit" size="lg" disabled={submitting} className="w-full sm:w-auto">
            {submitting ? (
              <>
                <Loader2 className="animate-spin" aria-hidden />
                Analyzing…
              </>
            ) : (
              <>
                Find Products
                <ArrowRight aria-hidden />
              </>
            )}
          </Button>
        </motion.div>
      </div>

      {error ? (
        <p id="search-error" role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      {compact ? null : (
        <div className="flex flex-wrap items-center gap-2 pt-2">
          <span className="text-xs text-muted-foreground">Try:</span>
          {EXAMPLES.map((example) => (
            <button
              key={example.query}
              type="button"
              onClick={() => {
                setQuery(example.query);
                setRequirements(example.requirements);
              }}
              className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {example.query}
            </button>
          ))}
        </div>
      )}
    </form>
  );
}

function Field({
  label,
  htmlFor,
  hint,
  children,
}: {
  label: string;
  htmlFor: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-3">
        <Label htmlFor={htmlFor}>{label}</Label>
        {hint ? <span className="text-[0.75rem] text-muted-foreground">{hint}</span> : null}
      </div>
      {children}
    </div>
  );
}
