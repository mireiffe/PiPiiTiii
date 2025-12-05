const protocol = import.meta.env.VITE_API_PROTOCOL || (typeof window !== "undefined" ? window.location.protocol : "http:");
const host = import.meta.env.VITE_API_HOST || (typeof window !== "undefined" ? window.location.hostname : "localhost");
const port = import.meta.env.VITE_API_PORT || (typeof window !== "undefined" ? window.location.port : "") || "8000";
const portSuffix = port ? `:${port}` : "";
export const BASE_URL = `${protocol}//${host}${portSuffix}`;
export const IMAGE_BASE_URL = BASE_URL;

export async function apiFetch(endpoint: string, options: RequestInit = {}) {
    const url = `${BASE_URL}${endpoint}`;
    const res = await fetch(url, options);
    return res;
}
