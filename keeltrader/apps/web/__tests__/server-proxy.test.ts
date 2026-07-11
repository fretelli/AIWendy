/**
 * @jest-environment node
 */

import {
  proxyRequest,
  rewriteApiLocationToProxy,
  type RouteContext,
} from "../lib/server/proxy";

const fetchMock = jest.fn();

function context(path: string[]): RouteContext {
  return { params: Promise.resolve({ path }) };
}

function request(
  path: string,
  init: RequestInit & { cookie?: string } = {}
): Request {
  const headers = new Headers(init.headers);
  if (init.cookie) {
    headers.set("cookie", init.cookie);
  }

  return new Request(`https://keeltrader.test${path}`, {
    ...init,
    headers,
  });
}

describe("server proxy helper", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    global.fetch = fetchMock;
  });

  it("returns 401 for protected paths without a token", async () => {
    const response = await proxyRequest(
      request("/api/proxy/v1/agent/health"),
      context(["v1", "agent", "health"]),
      {
        baseUrls: () => ["http://api:8000"],
        auth: { accessTokenCookie: "keeltrader_access_token" },
      }
    );

    await expect(response.json()).resolves.toEqual({
      detail: "Authentication required",
    });
    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sets auth cookies after login", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          access_token: "access-token",
          refresh_token: "refresh-token",
          expires_in: 123,
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );

    const response = await proxyRequest(
      request("/api/proxy/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: "a@b.test", password: "secret" }),
      }),
      context(["v1", "auth", "login"]),
      {
        baseUrls: () => ["http://api:8000"],
        publicPaths: ["v1/auth/login"],
        auth: {
          loginPath: "v1/auth/login",
          accessTokenCookie: "keeltrader_access_token",
          refreshTokenCookie: "keeltrader_refresh_token",
        },
      }
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("set-cookie")).toContain(
      "keeltrader_access_token=access-token"
    );
    expect(response.headers.get("set-cookie")).toContain(
      "keeltrader_refresh_token=refresh-token"
    );
    expect(response.headers.get("set-cookie")).toContain("Max-Age=123");
  });

  it("injects bearer auth from the access token cookie", async () => {
    fetchMock.mockResolvedValueOnce(new Response("ok", { status: 200 }));

    await proxyRequest(
      request("/api/proxy/v1/agent/health", {
        cookie: "keeltrader_access_token=cookie-token",
      }),
      context(["v1", "agent", "health"]),
      {
        baseUrls: () => ["http://api:8000"],
        auth: { accessTokenCookie: "keeltrader_access_token" },
      }
    );

    const [, init] = fetchMock.mock.calls[0] as [URL, RequestInit];
    expect((init.headers as Headers).get("authorization")).toBe(
      "Bearer cookie-token"
    );
  });

  it("falls back to the next upstream candidate", async () => {
    fetchMock
      .mockRejectedValueOnce(new Error("first down"))
      .mockResolvedValueOnce(new Response("ok", { status: 200 }));

    const response = await proxyRequest(
      request("/api/proxy/v1/agent/health", {
        cookie: "keeltrader_access_token=cookie-token",
      }),
      context(["v1", "agent", "health"]),
      {
        baseUrls: () => ["http://localhost:8000", "http://api:8000"],
        auth: { accessTokenCookie: "keeltrader_access_token" },
      }
    );

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(String(fetchMock.mock.calls[1][0])).toBe(
      "http://api:8000/api/v1/agent/health"
    );
  });

  it("keeps research proxy protected but forwards with a token", async () => {
    fetchMock.mockResolvedValueOnce(new Response("research", { status: 200 }));

    const response = await proxyRequest(
      request("/api/research/reports/search", {
        method: "POST",
        headers: { authorization: "Bearer research-token" },
        body: JSON.stringify({ query: "retail" }),
      }),
      context(["reports", "search"]),
      {
        baseUrls: () => ["https://research.example.com"],
      }
    );

    expect(response.status).toBe(200);
    expect(String(fetchMock.mock.calls[0][0])).toBe(
      "https://research.example.com/api/reports/search"
    );
  });

  it("rewrites API location headers to same-origin proxy paths", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(null, {
        status: 307,
        headers: { location: "http://api:8000/api/v1/auth/login?next=/x#top" },
      })
    );

    const response = await proxyRequest(
      request("/api/proxy/v1/private", {
        cookie: "keeltrader_access_token=cookie-token",
      }),
      context(["v1", "private"]),
      {
        baseUrls: () => ["http://api:8000"],
        auth: { accessTokenCookie: "keeltrader_access_token" },
        rewriteLocation: rewriteApiLocationToProxy,
      }
    );

    expect(response.headers.get("location")).toBe(
      "/api/proxy/v1/auth/login?next=/x#top"
    );
  });
});
