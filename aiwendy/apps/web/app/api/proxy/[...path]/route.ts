export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type RouteContext = {
  params: {
    path?: string[];
  };
};

function normalizeBaseUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return '';

  const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;
  const withoutTrailingSlash = withProtocol.replace(/\/+$/, '');

  return withoutTrailingSlash.replace(/\/api\/?$/, '');
}

function unique(values: string[]): string[] {
  const result: string[] = [];
  const seen = new Set<string>();
  for (const value of values) {
    const normalized = value.trim();
    if (!normalized) continue;
    if (seen.has(normalized)) continue;
    seen.add(normalized);
    result.push(normalized);
  }
  return result;
}

function getApiBaseUrlCandidates(): string[] {
  const configuredRaw =
    process.env.KEELTRADER_API_URL ||
    process.env.API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    '';

  const candidates: string[] = [];
  const configured = normalizeBaseUrl(configuredRaw);

  if (configured) {
    candidates.push(configured);

    try {
      const url = new URL(configured);
      const host = url.hostname.toLowerCase();

      if (host === 'api') {
        candidates.push('http://localhost:8000');
      }

      if (host === 'localhost' || host === '127.0.0.1') {
        candidates.push('http://api:8000');
      }
    } catch {
      // ignore invalid URL and rely on the configured value only
    }

    return unique(candidates);
  }

  // Dev-friendly defaults: try host networking first, then Docker DNS.
  candidates.push('http://localhost:8000');
  candidates.push('http://api:8000');
  return unique(candidates);
}

function buildUpstreamUrl(baseUrl: string, requestUrl: URL, path: string[]): URL {
  const upstream = new URL(baseUrl);
  const joinedPath = path.filter(Boolean).join('/');

  upstream.pathname = `/api/${joinedPath}`;
  upstream.search = requestUrl.search;

  return upstream;
}

function shouldHaveBody(method: string): boolean {
  const upper = method.toUpperCase();
  return upper !== 'GET' && upper !== 'HEAD';
}

function rewriteLocationHeader(location: string): string {
  try {
    const url = new URL(location, 'http://placeholder.local');
    if (!url.pathname.startsWith('/api/')) return location;

    // Rewrite `/api/*` -> `/api/proxy/*` so the browser stays on same-origin.
    const rewritten = new URL(url.toString());
    rewritten.pathname = `/api/proxy${url.pathname.slice('/api'.length)}`;
    return `${rewritten.pathname}${rewritten.search}${rewritten.hash}`;
  } catch {
    return location;
  }
}

async function proxy(request: Request, context: RouteContext): Promise<Response> {
  const requestUrl = new URL(request.url);
  const path = context.params.path ?? [];
  const candidates = getApiBaseUrlCandidates();

  const requestHeaders = new Headers(request.headers);
  requestHeaders.delete('host');
  requestHeaders.delete('connection');
  requestHeaders.delete('content-length');
  requestHeaders.delete('accept-encoding');

  const hasBody = shouldHaveBody(request.method);
  const body = hasBody ? await request.arrayBuffer() : null;

  const errors: Array<{ baseUrl: string; message: string }> = [];

  for (const baseUrl of candidates) {
    const upstreamUrl = buildUpstreamUrl(baseUrl, requestUrl, path);

    try {
      const init: RequestInit = {
        method: request.method,
        headers: requestHeaders,
        body,
        redirect: 'manual',
      };

      const upstreamResponse = await fetch(upstreamUrl, init);

      const responseHeaders = new Headers(upstreamResponse.headers);
      responseHeaders.delete('content-length');
      responseHeaders.delete('transfer-encoding');

      const location = responseHeaders.get('location');
      if (location) {
        responseHeaders.set('location', rewriteLocationHeader(location));
      }

      return new Response(upstreamResponse.body, {
        status: upstreamResponse.status,
        headers: responseHeaders,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      errors.push({ baseUrl, message });
      continue;
    }
  }

  return new Response(
    JSON.stringify(
      {
        error: 'API proxy failed',
        tried: candidates,
        hint:
          'Check that the API is running and reachable. ' +
          'If you run Web outside Docker, set NEXT_PUBLIC_API_URL=http://localhost:8000. ' +
          'If you run Web inside Docker Compose, set NEXT_PUBLIC_API_URL=http://api:8000.',
        details: errors,
      },
      null,
      2
    ),
    {
      status: 502,
      headers: {
        'content-type': 'application/json; charset=utf-8',
      },
    }
  );
}

export async function GET(request: Request, context: RouteContext) {
  return proxy(request, context);
}

export async function POST(request: Request, context: RouteContext) {
  return proxy(request, context);
}

export async function PUT(request: Request, context: RouteContext) {
  return proxy(request, context);
}

export async function PATCH(request: Request, context: RouteContext) {
  return proxy(request, context);
}

export async function DELETE(request: Request, context: RouteContext) {
  return proxy(request, context);
}

export async function HEAD(request: Request, context: RouteContext) {
  return proxy(request, context);
}

export async function OPTIONS(request: Request, context: RouteContext) {
  return proxy(request, context);
}
