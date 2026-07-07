export type RouteContext = {
  params: Promise<{
    path?: string[];
  }>;
};

type CookieOptions = {
  maxAge?: number;
  expires?: Date;
};

type AuthTokenConfig = {
  loginPath?: string;
  refreshPath?: string;
  logoutPath?: string;
  accessTokenCookie: string;
  refreshTokenCookie?: string;
  defaultAccessMaxAge?: number;
  defaultRefreshMaxAge?: number;
};

export type ProxyErrorContext = {
  candidates: string[];
  errors: Array<{ baseUrl: string; message: string }>;
};

export type ProxyConfig = {
  baseUrls: () => string[];
  requireAuth?: boolean;
  publicPaths?: string[];
  auth?: AuthTokenConfig;
  pathPrefix?: string;
  rewriteLocation?: (location: string) => string;
  errorPayload?: (context: ProxyErrorContext) => unknown;
};

const HOP_BY_HOP_HEADERS = [
  "host",
  "connection",
  "content-length",
  "accept-encoding",
  "transfer-encoding",
];

export function normalizeBaseUrl(raw: string, defaultProtocol = "http"): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";

  const withProtocol = /^https?:\/\//i.test(trimmed)
    ? trimmed
    : `${defaultProtocol}://${trimmed}`;

  return withProtocol.replace(/\/+$/, "").replace(/\/api\/?$/, "");
}

export function unique(values: string[]): string[] {
  const result: string[] = [];
  const seen = new Set<string>();

  for (const value of values) {
    const normalized = value.trim();
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    result.push(normalized);
  }

  return result;
}

export function parseCookieHeader(cookieHeader: string | null): Map<string, string> {
  const cookies = new Map<string, string>();
  if (!cookieHeader) return cookies;

  for (const part of cookieHeader.split(";")) {
    const index = part.indexOf("=");
    if (index < 0) continue;
    const name = part.slice(0, index).trim();
    const value = part.slice(index + 1).trim();
    if (!name) continue;
    cookies.set(name, decodeURIComponent(value));
  }

  return cookies;
}

export function serializeCookie(
  name: string,
  value: string,
  options: CookieOptions = {}
): string {
  const parts = [
    `${name}=${encodeURIComponent(value)}`,
    "Path=/",
    "HttpOnly",
    "SameSite=Lax",
  ];

  if (process.env.NODE_ENV === "production") {
    parts.push("Secure");
  }

  if (typeof options.maxAge === "number") {
    parts.push(`Max-Age=${options.maxAge}`);
  }

  if (options.expires) {
    parts.push(`Expires=${options.expires.toUTCString()}`);
  }

  return parts.join("; ");
}

export function clearCookie(name: string): string {
  return serializeCookie(name, "", {
    maxAge: 0,
    expires: new Date(0),
  });
}

export function buildUpstreamUrl(
  baseUrl: string,
  requestUrl: URL,
  path: string[],
  pathPrefix = "/api"
): URL {
  const upstream = new URL(baseUrl);
  const joinedPath = path.filter(Boolean).join("/");

  upstream.pathname = `${pathPrefix}/${joinedPath}`.replace(/\/+/g, "/");
  upstream.search = requestUrl.search;

  return upstream;
}

export function shouldHaveBody(method: string): boolean {
  const upper = method.toUpperCase();
  return upper !== "GET" && upper !== "HEAD";
}

export function rewriteApiLocationToProxy(location: string): string {
  try {
    const url = new URL(location, "http://placeholder.local");
    if (!url.pathname.startsWith("/api/")) return location;

    const rewritten = new URL(url.toString());
    rewritten.pathname = `/api/proxy${url.pathname.slice("/api".length)}`;
    return `${rewritten.pathname}${rewritten.search}${rewritten.hash}`;
  } catch {
    return location;
  }
}

function createJsonResponse(payload: unknown, status: number): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function prepareRequestHeaders(request: Request, auth?: AuthTokenConfig): Headers {
  const requestHeaders = new Headers(request.headers);

  for (const header of HOP_BY_HOP_HEADERS) {
    requestHeaders.delete(header);
  }

  if (auth && !requestHeaders.has("authorization")) {
    const cookies = parseCookieHeader(request.headers.get("cookie"));
    const accessToken = cookies.get(auth.accessTokenCookie);
    if (accessToken) {
      requestHeaders.set("authorization", `Bearer ${accessToken}`);
    }
  }

  return requestHeaders;
}

function prepareResponseHeaders(
  upstreamHeaders: Headers,
  rewriteLocation?: (location: string) => string
): Headers {
  const responseHeaders = new Headers(upstreamHeaders);
  responseHeaders.delete("content-length");
  responseHeaders.delete("transfer-encoding");

  const location = responseHeaders.get("location");
  if (location && rewriteLocation) {
    responseHeaders.set("location", rewriteLocation(location));
  }

  return responseHeaders;
}

function appendAuthCookies(
  responseHeaders: Headers,
  auth: AuthTokenConfig,
  payload: { access_token?: string; refresh_token?: string; expires_in?: number }
): void {
  if (payload.access_token) {
    responseHeaders.append(
      "set-cookie",
      serializeCookie(auth.accessTokenCookie, payload.access_token, {
        maxAge: payload.expires_in ?? auth.defaultAccessMaxAge ?? 60 * 60,
      })
    );
  }

  if (auth.refreshTokenCookie && payload.refresh_token) {
    responseHeaders.append(
      "set-cookie",
      serializeCookie(auth.refreshTokenCookie, payload.refresh_token, {
        maxAge: auth.defaultRefreshMaxAge ?? 30 * 24 * 60 * 60,
      })
    );
  }
}

export async function proxyRequest(
  request: Request,
  context: RouteContext,
  config: ProxyConfig
): Promise<Response> {
  const requestUrl = new URL(request.url);
  const params = await context.params;
  const path = params.path ?? [];
  const joinedPath = path.filter(Boolean).join("/");
  const candidates = unique(config.baseUrls());
  const auth = config.auth;
  const isLogin = request.method.toUpperCase() === "POST" && joinedPath === auth?.loginPath;
  const isRefresh = request.method.toUpperCase() === "POST" && joinedPath === auth?.refreshPath;
  const isLogout = request.method.toUpperCase() === "POST" && joinedPath === auth?.logoutPath;

  const requestHeaders = prepareRequestHeaders(request, auth);
  const isPublicPath = config.publicPaths?.includes(joinedPath) ?? false;
  if (config.requireAuth !== false && !isPublicPath && !requestHeaders.has("authorization")) {
    return createJsonResponse({ detail: "Authentication required" }, 401);
  }

  const body = shouldHaveBody(request.method) ? await request.arrayBuffer() : null;
  const errors: Array<{ baseUrl: string; message: string }> = [];

  for (const baseUrl of candidates) {
    const upstreamUrl = buildUpstreamUrl(
      baseUrl,
      requestUrl,
      path,
      config.pathPrefix ?? "/api"
    );

    try {
      const upstreamResponse = await fetch(upstreamUrl, {
        method: request.method,
        headers: requestHeaders,
        body,
        redirect: "manual",
      });

      const responseHeaders = prepareResponseHeaders(
        upstreamResponse.headers,
        config.rewriteLocation
      );

      if ((isLogin || isRefresh) && auth) {
        const text = await upstreamResponse.text();
        if (upstreamResponse.ok) {
          const payload = JSON.parse(text) as {
            access_token?: string;
            refresh_token?: string;
            expires_in?: number;
          };
          appendAuthCookies(responseHeaders, auth, payload);
        }

        return new Response(text, {
          status: upstreamResponse.status,
          headers: responseHeaders,
        });
      }

      if (isLogout && auth) {
        responseHeaders.append("set-cookie", clearCookie(auth.accessTokenCookie));
        if (auth.refreshTokenCookie) {
          responseHeaders.append("set-cookie", clearCookie(auth.refreshTokenCookie));
        }
      }

      return new Response(upstreamResponse.body, {
        status: upstreamResponse.status,
        headers: responseHeaders,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      errors.push({ baseUrl, message });
    }
  }

  const payload = config.errorPayload?.({ candidates, errors }) ?? {
    error: "API proxy failed",
    tried: candidates,
    details: errors,
  };

  return createJsonResponse(payload, 502);
}
