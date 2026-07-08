import {
  type RouteContext,
  proxyRequest,
  rewriteApiLocationToProxy,
} from "@/lib/server/proxy";
import { getApiBaseUrlCandidates } from "@/lib/server/upstreams";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ACCESS_TOKEN_COOKIE = "keeltrader_access_token";
const REFRESH_TOKEN_COOKIE = "keeltrader_refresh_token";

function proxy(request: Request, context: RouteContext): Promise<Response> {
  return proxyRequest(request, context, {
    baseUrls: getApiBaseUrlCandidates,
    publicPaths: [
      "v1/auth/login",
      "v1/auth/register",
      "v1/auth/forgot-password",
      "v1/auth/reset-password",
      "v1/auth/google",
    ],
    auth: {
      loginPath: "v1/auth/login",
      refreshPath: "v1/auth/refresh",
      logoutPath: "v1/auth/logout",
      accessTokenCookie: ACCESS_TOKEN_COOKIE,
      refreshTokenCookie: REFRESH_TOKEN_COOKIE,
    },
    rewriteLocation: rewriteApiLocationToProxy,
    errorPayload: ({ candidates, errors }) => ({
      error: "API proxy failed",
      tried: candidates,
      hint:
        "Check that the API is running and reachable. " +
        "If you run Web outside Docker, set NEXT_PUBLIC_API_URL=http://localhost:8000. " +
        "If you run Web inside Docker Compose, set NEXT_PUBLIC_API_URL=http://api:8000.",
      details: errors,
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
