import {
  type RouteContext,
  normalizeBaseUrl,
  proxyRequest,
} from "@/lib/server/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ACCESS_TOKEN_COOKIE = "keeltrader_access_token";

function getResearchBaseUrl(): string {
  return normalizeBaseUrl(
    process.env.RESEARCH_API_URL ||
      process.env.NEXT_PUBLIC_RESEARCH_API_URL ||
      "https://research.joyeeassets.com",
    "https"
  );
}

function proxy(request: Request, context: RouteContext): Promise<Response> {
  const baseUrl = getResearchBaseUrl();

  return proxyRequest(request, context, {
    baseUrls: () => [baseUrl],
    auth: {
      accessTokenCookie: ACCESS_TOKEN_COOKIE,
    },
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
