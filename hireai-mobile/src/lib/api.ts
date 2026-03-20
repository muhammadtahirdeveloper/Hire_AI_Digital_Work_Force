/**
 * API client for HireAI backend.
 * Handles JWT auth, token storage, and request/response processing.
 */

import * as SecureStore from "expo-secure-store";

const API_URL = "https://hireai-backend.onrender.com";

const TOKEN_KEY = "hireai_jwt_token";
const USER_KEY = "hireai_user";

// --- Token management ---

export async function getToken(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(TOKEN_KEY);
  } catch {
    return null;
  }
}

export async function setToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function removeToken(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(USER_KEY);
}

export async function getStoredUser(): Promise<Record<string, unknown> | null> {
  try {
    const json = await SecureStore.getItemAsync(USER_KEY);
    return json ? JSON.parse(json) : null;
  } catch {
    return null;
  }
}

export async function setStoredUser(user: Record<string, unknown>): Promise<void> {
  await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user));
}

// --- API request helper ---

interface ApiResponse<T = unknown> {
  success: boolean;
  data: T | null;
  error: string | null;
}

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = await getToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    });

    const json = await res.json();

    if (!res.ok) {
      return {
        success: false,
        data: null,
        error: json?.detail || json?.error || `HTTP ${res.status}`,
      };
    }

    return {
      success: json?.success ?? true,
      data: json?.data ?? json,
      error: json?.error ?? null,
    };
  } catch (err) {
    return {
      success: false,
      data: null,
      error: err instanceof Error ? err.message : "Network error",
    };
  }
}

// --- Convenience methods ---

export const api = {
  get: <T = unknown>(path: string) => apiRequest<T>(path),

  post: <T = unknown>(path: string, body?: unknown) =>
    apiRequest<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),

  patch: <T = unknown>(path: string, body?: unknown) =>
    apiRequest<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T = unknown>(path: string) =>
    apiRequest<T>(path, { method: "DELETE" }),
};
