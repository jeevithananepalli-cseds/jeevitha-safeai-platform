/**
 * Wire types mirroring the backend API contract (docs/api-contract.md).
 *
 * Keeping these in one place gives the whole frontend a single, typed view of
 * the API envelope so responses are handled uniformly and safely.
 */

export interface ErrorDetail {
  code: string;
  message: string;
  details: Record<string, string>;
}

/** Pagination metadata present on paginated list responses. */
export interface PageMeta {
  total: number;
  page: number;
  limit: number;
}

/** The standard envelope every endpoint returns. */
export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ErrorDetail | null;
  /** Present only on paginated list responses. */
  meta?: PageMeta | null;
}

/** Payload of a successful `GET /api/v1/health/ready`. */
export interface ReadinessStatus {
  status: "ready";
  version: string;
  database: "up";
}
