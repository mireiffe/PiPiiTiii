const port = import.meta.env.VITE_API_PORT || "8000";
export const BASE_URL = `http://localhost:${port}`;
export const IMAGE_BASE_URL = BASE_URL;

export async function apiFetch(endpoint: string, options: RequestInit = {}) {
    const url = `${BASE_URL}${endpoint}`;
    const res = await fetch(url, options);
    return res;
}
