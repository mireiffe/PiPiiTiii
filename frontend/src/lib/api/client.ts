/**
 * API Client
 *
 * Base configuration and fetch wrapper for API calls.
 */

const protocol = import.meta.env.VITE_API_PROTOCOL || (typeof window !== 'undefined' ? window.location.protocol : 'http:');
const host = import.meta.env.VITE_API_HOST || (typeof window !== 'undefined' ? window.location.hostname : 'localhost');
const port = import.meta.env.VITE_API_PORT || (typeof window !== 'undefined' ? window.location.port : '') || '8000';
const portSuffix = port ? `:${port}` : '';

export const BASE_URL = `${protocol}//${host}${portSuffix}`;
export const IMAGE_BASE_URL = BASE_URL;

/**
 * Typed fetch wrapper for API calls
 */
export async function apiFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
    const url = `${BASE_URL}${endpoint}`;
    return fetch(url, options);
}

/**
 * Typed JSON fetch that parses response automatically
 */
export async function apiFetchJson<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const response = await apiFetch(endpoint, options);
    if (!response.ok) {
        throw new ApiError(response.status, response.statusText, endpoint);
    }
    return response.json();
}

/**
 * API Error class for better error handling
 */
export class ApiError extends Error {
    constructor(
        public readonly status: number,
        public readonly statusText: string,
        public readonly endpoint: string,
    ) {
        super(`API Error ${status}: ${statusText} (${endpoint})`);
        this.name = 'ApiError';
    }
}

/**
 * Type-safe POST helper
 */
export async function apiPost<TRequest, TResponse>(
    endpoint: string,
    data: TRequest,
): Promise<TResponse> {
    const response = await apiFetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!response.ok) {
        throw new ApiError(response.status, response.statusText, endpoint);
    }
    return response.json();
}
