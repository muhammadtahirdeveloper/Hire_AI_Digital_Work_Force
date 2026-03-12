import axios from "axios";

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
 * Add authentication token to requests
 */
export function setAuthToken(token: string) {
  api.defaults.headers.common["X-API-Key"] = token;
}

/**
 * Remove authentication token
 */
export function removeAuthToken() {
  delete api.defaults.headers.common["X-API-Key"];
}

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
