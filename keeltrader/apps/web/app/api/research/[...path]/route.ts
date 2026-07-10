import {
  type RouteContext,
  proxyRequest,
} from "@/lib/server/proxy";
import { getResearchBaseUrl } from "@/lib/server/upstreams";
import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function proxy(request: Request, context: RouteContext): Promise<Response> {
  const baseUrl = getResearchBaseUrl();
  if (!baseUrl) {
    return Promise.resolve(
      NextResponse.json(
        { detail: "Research Cloud is not configured for this deployment" },
        { status: 503 }
      )
    );
  }

  return proxyRequest(request, context, {
    baseUrls: () => [baseUrl],
    errorPayload: ({ errors }) => ({
      detail: "Research API proxy failed",
      upstream: baseUrl,
      message: errors[0]?.message ?? "Unknown error",
    }),
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const HEAD = proxy;
export const OPTIONS = proxy;
