/**
 * Minimal typed API client.
 *
 * A single thin wrapper around `fetch` that:
 *  - prefixes the configured API base URL,
 *  - sends/parses JSON,
 *  - unwraps the standard `{ success, data, error }` envelope,
 *  - surfaces failures as a typed `ApiError`.
 *
 * Endpoint-specific helpers (auth, contacts, …) build on this in later phases,
 * so call sites never duplicate fetch/envelope plumbing.
 */

import type { ApiResponse } from "@/lib/api/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

/** Error thrown when a request fails at the transport or application level. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  /** Optional bearer token for authenticated calls (used from Phase 2). */
  token?: string;
  /** Forwarded to fetch; `no-store` keeps health checks live. */
  cache?: RequestCache;
}

/**
 * Perform a request and return the unwrapped payload.
 *
 * @throws {ApiError} if the network call fails or the envelope reports an error.
 */
export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, token, cache } = options;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache,
    });
  } catch {
    throw new ApiError("Network request failed", "network_error", 0);
  }

  let envelope: ApiResponse<T>;
  try {
    envelope = (await response.json()) as ApiResponse<T>;
  } catch {
    // A non-JSON body (proxy error page, empty 5xx, gateway timeout) must not
    // crash as an unhandled SyntaxError — surface it as a typed ApiError.
    throw new ApiError(
      "Malformed response from server",
      "invalid_response",
      response.status,
    );
  }

  if (!response.ok || !envelope.success || envelope.data === null) {
    const error = envelope.error;
    throw new ApiError(
      error?.message ?? "Request failed",
      error?.code ?? "unknown_error",
      response.status,
    );
  }

  return envelope.data;
}
