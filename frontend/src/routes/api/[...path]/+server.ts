import { BACKEND_HOST, BACKEND_PORT, BACKEND_PROTOCOL, BACKEND_ORIGIN } from "$env/static/private";
import type { RequestHandler } from "./$types";

const protocol = BACKEND_PROTOCOL || "http";
const host = BACKEND_HOST || "127.0.0.1";
const port = BACKEND_PORT ? `:${BACKEND_PORT}` : "";
const backendOrigin = BACKEND_ORIGIN || `${protocol}://${host}${port || ":8000"}`;

const proxy: RequestHandler = async ({ request, params, url }) => {
    const endpointPath = params.path ? `/api/${params.path}` : "";
    const targetUrl = `${backendOrigin}${endpointPath}${url.search}`;

    const headers = new Headers(request.headers);
    headers.delete("host");
    headers.delete("origin");

    // Read body once and pass it to fetch
    let body: any = undefined;
    if (request.method !== "GET" && request.method !== "HEAD") {
        body = await request.text();
    }

    const res = await fetch(targetUrl, {
        method: request.method,
        headers,
        body,
    });

    const responseHeaders = new Headers(res.headers);
    return new Response(res.body, {
        status: res.status,
        statusText: res.statusText,
        headers: responseHeaders,
    });
};

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;