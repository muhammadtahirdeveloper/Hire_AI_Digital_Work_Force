import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Save JWT token to localStorage
 */
export function setAuthToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("hireai_token", token);
  }
}

/**
 * Get JWT token from localStorage
 */
export function getAuthToken(): string {
  if (typeof window !== "undefined") {
    return localStorage.getItem("hireai_token") || "";
  }
  return "";
}

/**
 * Remove JWT token from localStorage
 */
export function removeAuthToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("hireai_token");
  }
}

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
 * Interceptor: attach JWT Bearer token from localStorage to every request
 */
api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
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
