import { NextRequest, NextResponse } from "next/server";

const PUBLIC_ROUTES: RegExp[] = [
  /^health$/,
  /^events$/,
  /^events\/[^/]+$/,
  /^selected$/,
  /^objects$/,
  /^objects\/[^/]+$/,
  /^topics$/,
  /^topics\/[^/]+$/,
  /^trends$/,
  /^digests\/(daily|weekly|monthly)$/,
  /^metrics$/,
];

function isAllowed(path: string): boolean {
  return PUBLIC_ROUTES.some((pattern) => pattern.test(path));
}

function internalApiBase(): string | null {
  const value = process.env.API_PROXY_TARGET || process.env.INTERNAL_API_BASE;
  return value ? value.replace(/\/$/, "") : null;
}

async function proxyGet(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path: segments } = await context.params;
  const path = (segments || []).join("/");
  if (!isAllowed(path)) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  const base = internalApiBase();
  if (!base) {
    return NextResponse.json({ error: "service_unavailable" }, { status: 503 });
  }

  const upstream = new URL(`${base}/${path}`);
  upstream.search = request.nextUrl.search;

  try {
    const response = await fetch(upstream, {
      method: "GET",
      headers: { accept: request.headers.get("accept") || "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });

    const body = await response.arrayBuffer();
    const headers = new Headers();
    const contentType = response.headers.get("content-type");
    if (contentType) headers.set("content-type", contentType);
    headers.set("cache-control", "no-store");

    return new NextResponse(body, {
      status: response.status,
      headers,
    });
  } catch {
    return NextResponse.json({ error: "service_unavailable" }, { status: 503 });
  }
}

export const GET = proxyGet;
