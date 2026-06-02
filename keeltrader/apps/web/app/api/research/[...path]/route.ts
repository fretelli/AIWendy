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

  const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  return withProtocol.replace(/\/+$/, '').replace(/\/api\/?$/, '');
}

function getResearchBaseUrl(): string {
  return normalizeBaseUrl(process.env.RESEARCH_API_URL || process.env.NEXT_PUBLIC_RESEARCH_API_URL || 'https://research.joyeeassets.com');
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

async function proxy(request: Request, context: RouteContext): Promise<Response> {
  const requestUrl = new URL(request.url);
  const path = context.params.path ?? [];
  const baseUrl = getResearchBaseUrl();
  const upstreamUrl = buildUpstreamUrl(baseUrl, requestUrl, path);

  const requestHeaders = new Headers(request.headers);
  requestHeaders.delete('host');
  requestHeaders.delete('connection');
  requestHeaders.delete('content-length');
  requestHeaders.delete('accept-encoding');

  try {
    const upstreamResponse = await fetch(upstreamUrl, {
      method: request.method,
      headers: requestHeaders,
      body: shouldHaveBody(request.method) ? await request.arrayBuffer() : null,
      redirect: 'manual',
    });

    const responseHeaders = new Headers(upstreamResponse.headers);
    responseHeaders.delete('content-length');
    responseHeaders.delete('transfer-encoding');

    return new Response(upstreamResponse.body, {
      status: upstreamResponse.status,
      headers: responseHeaders,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return new Response(
      JSON.stringify({
        detail: 'Research API proxy failed',
        upstream: baseUrl,
        message,
      }),
      {
        status: 502,
        headers: { 'content-type': 'application/json; charset=utf-8' },
      }
    );
  }
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
