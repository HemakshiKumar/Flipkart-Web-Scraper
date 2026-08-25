/**
 * Shared types for the recommendation API.
 *
 * These mirror `backend/app/models.py`. The zod schemas in `lib/validation.ts`
 * are the runtime source of truth; these types are derived from them so the two
 * can never drift.
 */

import type {
  parsedRequirementsSchema,
  productSchema,
  recommendRequestSchema,
  recommendResponseSchema,
} from "@/lib/validation";
import type { z } from "zod";

export type RecommendRequest = z.infer<typeof recommendRequestSchema>;
export type RecommendResponse = z.infer<typeof recommendResponseSchema>;
export type Product = z.infer<typeof productSchema>;
export type ParsedRequirements = z.infer<typeof parsedRequirementsSchema>;

/** Where the ranked rows came from. Surfaced in the UI for transparency. */
export type DatasetSource = RecommendResponse["source"];

/** Machine-readable failure codes the UI switches on. */
export type ApiErrorCode =
  | "invalid_request"
  | "scraping_failed"
  | "no_results"
  | "internal_error"
  | "network_error";

export interface ApiError {
  error: string;
  code: ApiErrorCode;
}

/** Thrown by the client helpers; carries a code the UI can branch on. */
export class RecommendationRequestError extends Error {
  readonly code: ApiErrorCode;

  constructor(message: string, code: ApiErrorCode) {
    super(message);
    this.name = "RecommendationRequestError";
    this.code = code;
  }
}
