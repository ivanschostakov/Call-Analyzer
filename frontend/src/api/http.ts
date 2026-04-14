import { authStore } from '../auth/store';
import type { AuthTokens } from '../auth/types';

type RequestConfig = {
  url: string;
  method?: string;
  headers?: HeadersInit;
  params?: Record<string, unknown>;
  data?: unknown;
  body?: BodyInit | null;
  signal?: AbortSignal;
};

function resolveApiBaseUrl() {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  if (configuredBaseUrl) {
    if (/^https?:\/\//.test(configuredBaseUrl)) {
      return configuredBaseUrl.replace(/\/+$/, '');
    }
    if (typeof window !== 'undefined') {
      return new URL(configuredBaseUrl, window.location.origin).toString().replace(/\/+$/, '');
    }
    return configuredBaseUrl.replace(/\/+$/, '');
  }

  if (typeof window !== 'undefined') {
    return new URL('/api', window.location.origin).toString().replace(/\/+$/, '');
  }

  return 'http://127.0.0.1:8000';
}

const API_BASE_URL = resolveApiBaseUrl();

let refreshPromise: Promise<AuthTokens | null> | null = null;

export function buildApiUrl(path: string, params?: Record<string, unknown>) {
  const isAbsolute = /^https?:\/\//.test(path);
  const url = new URL(isAbsolute ? path : `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null) {
        return;
      }
      if (Array.isArray(value)) {
        value.forEach((item) => url.searchParams.append(key, String(item)));
        return;
      }
      url.searchParams.set(key, String(value));
    });
  }
  return url.toString();
}

async function parseJson<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function refreshAuthTokens(): Promise<AuthTokens | null> {
  const session = authStore.getSnapshot();
  if (!session) {
    return null;
  }

  const response = await fetch(buildApiUrl('/auth/refresh'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      refresh_token: session.refreshToken,
      session_id: session.sessionId,
    }),
  });

  if (!response.ok) {
    authStore.clear();
    return null;
  }

  const tokens = await parseJson<AuthTokens>(response);
  authStore.setSession({
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
    sessionId: tokens.session_id,
    tokenType: tokens.token_type ?? 'bearer',
    user: session.user,
  });
  return tokens;
}

async function ensureFreshTokens() {
  if (!refreshPromise) {
    refreshPromise = refreshAuthTokens().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

function normalizeArgs(urlOrConfig: string | RequestConfig, init?: RequestInit): RequestConfig {
  if (typeof urlOrConfig === 'string') {
    return {
      url: urlOrConfig,
      method: init?.method,
      headers: init?.headers,
      body: init?.body ?? undefined,
      signal: init?.signal ?? undefined,
    };
  }
  return urlOrConfig;
}

export async function apiFetchResponse(urlOrConfig: string | RequestConfig, init?: RequestInit, retry = true): Promise<Response> {
  const config = normalizeArgs(urlOrConfig, init);
  const session = authStore.getSnapshot();
  const headers = new Headers(config.headers);

  if (config.data !== undefined && !(config.data instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (config.body instanceof FormData && headers.has('Content-Type')) {
    headers.delete('Content-Type');
  }
  if (session?.accessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${session.accessToken}`);
  }

  const response = await fetch(buildApiUrl(config.url, config.params), {
    method: config.method ?? 'GET',
    headers,
    body: config.body ?? (
      config.data instanceof FormData
        ? config.data
        : config.data !== undefined
          ? JSON.stringify(config.data)
          : undefined
    ),
    signal: config.signal,
  });

  if (response.status === 401 && retry && session?.refreshToken) {
    const refreshed = await ensureFreshTokens();
    if (refreshed) {
      return apiFetchResponse(urlOrConfig, init, false);
    }
  }

  if (!response.ok) {
    let detail = 'Request failed.';
    try {
      const body = await response.json();
      detail = typeof body?.detail === 'string' ? body.detail : detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response;
}

export async function apiFetch<T>(urlOrConfig: string | RequestConfig, init?: RequestInit, retry = true): Promise<T> {
  const response = await apiFetchResponse(urlOrConfig, init, retry);
  return parseJson<T>(response);
}
