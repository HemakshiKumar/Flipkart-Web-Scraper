/**
 * Runtime validation for everything crossing a trust boundary.
 *
 * - `recommendRequestSchema` validates what the browser sends to the Next.js
 *   route handler (the Python service validates it a second time).
 * - `recommendResponseSchema` validates what the Python service sends back, so
 *   a shape change surfaces as a clean error instead of a client crash.
 */

import { z } from "zod";

export const MIN_QUERY_LENGTH = 2;
export const MAX_QUERY_LENGTH = 120;
export const MAX_REQUIREMENTS_LENGTH = 500;
export const MIN_LIMIT = 1;
export const MAX_LIMIT = 50;
export const LIMIT_OPTIONS = [5, 10, 15, 20, 25, 50] as const;
export const DEFAULT_LIMIT = 10;

export const recommendRequestSchema = z.object({
  query: z
    .string()
    .trim()
    .min(MIN_QUERY_LENGTH, "Tell us what you are looking for.")
    .max(MAX_QUERY_LENGTH, `Keep the search under ${MAX_QUERY_LENGTH} characters.`),
  requirements: z
    .string()
    .trim()
    .max(MAX_REQUIREMENTS_LENGTH, `Keep requirements under ${MAX_REQUIREMENTS_LENGTH} characters.`)
    .default(""),
  limit: z.coerce.number().int().min(MIN_LIMIT).max(MAX_LIMIT).default(DEFAULT_LIMIT),
  refresh: z.boolean().default(false),
});

export const parsedRequirementsSchema = z.object({
  minRating: z.number().nullable().default(null),
  maxRating: z.number().nullable().default(null),
  minPrice: z.number().nullable().default(null),
  maxPrice: z.number().nullable().default(null),
  preferCheap: z.boolean().default(false),
  preferPopular: z.boolean().default(false),
  boostedFeatures: z.array(z.string()).default([]),
  notes: z.array(z.string()).default([]),
});

export const productSchema = z.object({
  name: z.string(),
  price: z.number(),
  rating: z.number(),
  score: z.number(),
  similarity: z.number(),
  url: z.string().nullable().default(null),
  searchUrl: z.string().default(""),
  ratingsCount: z.number().default(0),
  reviewsCount: z.number().default(0),
  returnPolicy: z.string().nullable().default(null),
  attributes: z.record(z.string(), z.string()).default({}),
  highlights: z.array(z.string()).default([]),
});

export const recommendResponseSchema = z.object({
  query: z.string(),
  requirements: z.string().default(""),
  limit: z.number(),
  count: z.number(),
  source: z.enum(["live", "cache", "seed"]),
  datasetSize: z.number(),
  elapsedMs: z.number(),
  parsed: parsedRequirementsSchema,
  warnings: z.array(z.string()).default([]),
  results: z.array(productSchema).default([]),
});

export const apiErrorSchema = z.object({
  error: z.string(),
  code: z.enum(["invalid_request", "scraping_failed", "no_results", "internal_error"]),
});

/** Clamp a user-supplied limit (e.g. from the URL) into the allowed range. */
export function clampLimit(value: unknown): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return DEFAULT_LIMIT;
  return Math.min(MAX_LIMIT, Math.max(MIN_LIMIT, Math.trunc(parsed)));
}
