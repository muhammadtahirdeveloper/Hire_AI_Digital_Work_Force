import axios from "axios";
import { getSession } from "next-auth/react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Axios instance configured for HireAI backend API
 */
export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Interceptor: attach JWT Bearer token from NextAuth session to every request
 */
api.interceptors.request.use(async (config) => {
  try {
    const session = await getSession();
    if (session) {
      const token =
        (session as unknown as Record<string, unknown>).accessToken ||
        "";
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
  } catch {
    // Session fetch failed — continue without auth header
  }
  return config;
});

/**
 * API error handler
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function handleApiError(error: any): string {
  if (error.response) {
    return error.response.data.detail || error.response.data.message || "An error occurred";
  } else if (error.request) {
    return "No response from server. Please check your connection.";
  } else {
    return error.message || "An unexpected error occurred";
  }
}
