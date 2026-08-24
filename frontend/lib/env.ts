/**
 * Server-only environment configuration.
 *
 * Importing this from a client component is a build error by design - the
 * recommendation service URL and its timeout never reach the browser.
 */

import "server-only";

const DEFAULT_API_URL = "http://127.0.0.1:8000";
// A cold search scrapes ~20 product pages, which can take the best part of a minute.
const DEFAULT_TIMEOUT_MS = 90_000;

function readTimeout(): number {
  const raw = Number(process.env.RECOMMENDER_TIMEOUT_MS);
  return Number.isFinite(raw) && raw > 0 ? raw : DEFAULT_TIMEOUT_MS;
}

export const serverEnv = {
  /** Base URL of the Python recommendation service. */
  recommenderApiUrl: (process.env.RECOMMENDER_API_URL ?? DEFAULT_API_URL).replace(/\/$/, ""),
  /** How long the route handler waits for the pipeline before giving up. */
  recommenderTimeoutMs: readTimeout(),
} as const;
