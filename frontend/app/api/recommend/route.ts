/**
 * POST /api/recommend
 *
 * Thin, validating proxy in front of the Python recommendation service. It
 * never leaks the upstream URL, its errors or its stack traces to the browser.
 */

import { NextResponse } from "next/server";

import { requestRecommendations } from "@/lib/recommendation-service";
import { recommendRequestSchema } from "@/lib/validation";

export const dynamic = "force-dynamic";

export async function POST(request: Request): Promise<NextResponse> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Send a JSON body.", code: "invalid_request" },
      { status: 400 },
    );
  }

  const parsed = recommendRequestSchema.safeParse(body);
  if (!parsed.success) {
    const message = parsed.error.issues[0]?.message ?? "That search wasn't valid.";
    return NextResponse.json({ error: message, code: "invalid_request" }, { status: 422 });
  }

  const started = Date.now();
  const result = await requestRecommendations(parsed.data);

  if (!result.ok) {
    return NextResponse.json({ error: result.message, code: result.code }, { status: result.status });
  }

  console.info("[recommend] ok", {
    query: parsed.data.query,
    limit: parsed.data.limit,
    count: result.data.count,
    source: result.data.source,
    ms: Date.now() - started,
  });

  return NextResponse.json(result.data, {
    status: 200,
    headers: { "Cache-Control": "no-store" },
  });
}
