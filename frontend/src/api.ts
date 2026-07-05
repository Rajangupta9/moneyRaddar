// Thin API client for the RupeeRadar backend.
// Uses same-origin /api paths (proxied to FastAPI in dev — see vite.config.ts).

import type { AnalyzeResponse, HealthResponse } from "./types";

const BASE = "/api";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthResponse> {
  return json<HealthResponse>(await fetch(`${BASE}/health`));
}

// Phase 1+: uploads a statement file and runs the pipeline.
// Wired in Phase 1; present here so the shell compiles against the contract.
export async function analyze(file: File): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("file", file);
  return json<AnalyzeResponse>(
    await fetch(`${BASE}/analyze`, { method: "POST", body: form }),
  );
}
