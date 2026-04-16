import { getAccessToken } from './auth';

const API_BASE = '/api/v1';

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function getTenantId(): string | null {
  try {
    return localStorage.getItem('gnucash_tenant_id');
  } catch {
    return null;
  }
}

async function refreshToken(): Promise<string | null> {
  try {
    const response = await fetch(`${API_BASE}/auth/refresh/`, {
      method: 'POST',
      credentials: 'include',
    });
    if (!response.ok) return null;
    const data = await response.json();
    return data.access ?? null;
  } catch {
    return null;
  }
}

// Queue for concurrent 401 retries
let refreshPromise: Promise<string | null> | null = null;

async function ensureAccessToken(): Promise<string | null> {
  if (getAccessToken()) return getAccessToken();

  if (!refreshPromise) {
    refreshPromise = refreshToken().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await ensureAccessToken();
  const tenantId = getTenantId();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(tenantId ? { 'X-Tenant-ID': tenantId } : {}),
    ...(init?.headers as Record<string, string> ?? {}),
  };

  let response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });

  // Handle 401 — one retry after token refresh
  if (response.status === 401) {
    const newToken = await refreshToken();
    if (newToken && !response.headers.get('x-retried')) {
      headers.Authorization = `Bearer ${newToken}`;
      response = await fetch(`${API_BASE}${path}`, {
        ...init,
        headers,
        credentials: 'include',
      });
    }
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body, response.statusText);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};
