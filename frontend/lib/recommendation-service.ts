/**
 * Server-side client for the Python recommendation service.
 *
 * Only the Next.js route handler talks to this module: the browser never sees
 * the service URL, and upstream errors are mapped onto the small set of codes
 * the UI understands before anything is returned.
 */

import "server-only";

import { serverEnv } from "@/lib/env";
import {
  apiErrorSchema,
  recommendResponseSchema,
  type recommendRequestSchema,
} from "@/lib/validation";
import type { ApiErrorCode, RecommendResponse } from "@/lib/types";
import type { z } from "zod";

export interface ServiceFailure {
  ok: false;
  status: number;
  code: ApiErrorCode;
  message: string;
}

export interface ServiceSuccess {
  ok: true;
  data: RecommendResponse;
}

export type ServiceResult = ServiceSuccess | ServiceFailure;

const USER_MESSAGES: Record<ApiErrorCode, string> = {
  invalid_request: "That search wasn't valid. Check the fields and try again.",
  scraping_failed: "We couldn't retrieve products right now. Please try again in a moment.",
  no_results: "No products matched those requirements.",
  internal_error: "Something went wrong while generating recommendations.",
  network_error: "The recommendation service is unreachable. Please try again shortly.",
};

function failure(code: ApiErrorCode, status: number): ServiceFailure {
  return { ok: false, status, code, message: USER_MESSAGES[code] };
}

export async function requestRecommendations(
  payload: z.infer<typeof recommendRequestSchema>,
): Promise<ServiceResult> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), serverEnv.recommenderTimeoutMs);

  try {
    const response = await fetch(`${serverEnv.recommenderApiUrl}/api/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
      cache: "no-store",
    });

    const body: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      const parsedError = apiErrorSchema.safeParse(body);
      const code: ApiErrorCode = parsedError.success ? parsedError.data.code : "internal_error";
      console.error("[recommend] upstream error", {
        status: response.status,
        code,
      });
      return failure(code, response.status === 422 ? 422 : response.status);
    }

    const parsed = recommendResponseSchema.safeParse(body);
    if (!parsed.success) {
      console.error("[recommend] unexpected response shape", parsed.error.issues);
      return failure("internal_error", 502);
    }

    return { ok: true, data: parsed.data };
  } catch (error) {
    const aborted = error instanceof Error && error.name === "AbortError";
    console.error("[recommend] request failed", {
      aborted,
      message: error instanceof Error ? error.message : String(error),
    });
    return failure("network_error", aborted ? 504 : 502);
  } finally {
    clearTimeout(timeout);
  }
}

export async function checkServiceHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${serverEnv.recommenderApiUrl}/api/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    });
    return response.ok;
  } catch {
    return false;
  }
}
