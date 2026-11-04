import { getLanguage } from "../i18n";
import type { components } from "../types/api.generated";

export type HealthResponse = components["schemas"]["HealthResponse"];
type ApiError = components["schemas"]["ErrorResponse"];

export async function getHealth(signal: AbortSignal): Promise<HealthResponse> {
  const response = await fetch("/api/health", {
    signal,
    headers: { Accept: "application/json", "Accept-Language": getLanguage() },
  });
  if (!response.ok) {
    let body: Partial<ApiError> = {};
    try {
      body = (await response.json()) as ApiError;
    } catch {
      // Proxy failures need not contain JSON.
    }
    throw new Error(
      `${body.message || "API unavailable."} (${body.code || "API_UNAVAILABLE"}; ${body.request_id || response.status})`,
    );
  }
  return response.json() as Promise<HealthResponse>;
}
