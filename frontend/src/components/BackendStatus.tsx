"use client";

import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api/client";
import { getReadiness } from "@/lib/api/health";
import type { ReadinessStatus } from "@/lib/api/types";

type State =
  | { kind: "loading" }
  | { kind: "ok"; readiness: ReadinessStatus }
  | { kind: "error"; message: string };

/**
 * Small client component that probes the backend readiness endpoint and renders
 * the connection status. It is the end-to-end proof that the typed API client
 * talks to the FastAPI service.
 */
export function BackendStatus() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    getReadiness()
      .then((readiness) => active && setState({ kind: "ok", readiness }))
      .catch((error: unknown) => {
        if (!active) return;
        const message =
          error instanceof ApiError ? error.message : "Could not reach backend";
        setState({ kind: "error", message });
      });
    return () => {
      active = false;
    };
  }, []);

  if (state.kind === "loading") {
    return <p className="text-sm text-slate-500">Checking backend…</p>;
  }

  if (state.kind === "error") {
    return (
      <p className="text-sm font-medium text-emergency">
        Backend unreachable — {state.message}
      </p>
    );
  }

  const { status, version, database } = state.readiness;
  return (
    <div className="text-sm">
      <span className="font-semibold text-safe">Backend {status}</span>
      <span className="text-slate-500">
        {" "}
        · v{version} · database {database}
      </span>
    </div>
  );
}
