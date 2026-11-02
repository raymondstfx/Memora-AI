import type { components } from "../types/api.generated";

export type HealthResponse = components["schemas"]["HealthResponse"];
type ApiError = components["schemas"]["ErrorResponse"];

export async function getHealth(signal: AbortSignal): Promise<HealthResponse> {
  const response = await fetch("/api/health", {
    signal,
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    const body = (await response.json()) as ApiError;
    throw new Error(
      `${body.message || "API unavailable."} Reference: ${body.request_id || response.status}`,
    );
  }
  return response.json() as Promise<HealthResponse>;
}
