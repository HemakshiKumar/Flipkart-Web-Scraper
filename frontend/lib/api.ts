/** Browser-side client for the Next.js route handler. */

import { RecommendationRequestError, type RecommendResponse } from "@/lib/types";
import { apiErrorSchema, recommendResponseSchema } from "@/lib/validation";

export interface RecommendInput {
  query: string;
  requirements: string;
  limit: number;
  refresh?: boolean;
}

export async function fetchRecommendations(
  input: RecommendInput,
  signal?: AbortSignal,
): Promise<RecommendResponse> {
  let response: Response;
  try {
    response = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new RecommendationRequestError(
      "We couldn't reach the recommendation service. Check your connection and try again.",
      "network_error",
    );
  }

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const parsed = apiErrorSchema.safeParse(body);
    throw new RecommendationRequestError(
      parsed.success ? parsed.data.error : "Something went wrong while generating recommendations.",
      parsed.success ? parsed.data.code : "internal_error",
    );
  }

  const parsed = recommendResponseSchema.safeParse(body);
  if (!parsed.success) {
    throw new RecommendationRequestError(
      "The recommendation service returned an unexpected response.",
      "internal_error",
    );
  }

  return parsed.data;
}
