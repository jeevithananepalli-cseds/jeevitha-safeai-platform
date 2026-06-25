/** Health endpoint helpers — the first consumers of the API client. */

import { apiRequest } from "@/lib/api/client";
import type { ReadinessStatus } from "@/lib/api/types";

/**
 * Fetch backend readiness (database-aware). Never cached so the status reflects
 * reality. A not-ready backend responds 503 and surfaces as an `ApiError`.
 */
export async function getReadiness(): Promise<ReadinessStatus> {
  return apiRequest<ReadinessStatus>("/health/ready", { cache: "no-store" });
}
