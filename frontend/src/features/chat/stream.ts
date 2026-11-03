import type { components } from "../../types/api.generated";

export type ChatEvent = components["schemas"]["StreamEvent"];

export async function readEvents(
  response: Response,
  receive: (event: ChatEvent) => void,
) {
  if (!response.body)
    throw new Error("Streaming is unavailable in this browser.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finished = false;
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      buffer = buffer.replace(/\r\n/g, "\n");
      let boundary: number;
      while ((boundary = buffer.indexOf("\n\n")) >= 0) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const data = block
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart())
          .join("\n");
        if (!data) continue;
        const event = JSON.parse(data) as ChatEvent;
        if (!event.event || !event.message_id || !event.conversation_id)
          throw new Error("Invalid chat stream frame.");
        receive(event);
        if (event.event === "message_end" || event.event === "error")
          finished = true;
      }
      if (buffer.length > 262144)
        throw new Error("Chat stream frame exceeded the limit.");
      if (done) break;
    }
    if (!finished)
      throw new Error(
        "Connection ended before the response completed. Reload history and retry explicitly.",
      );
  } finally {
    reader.releaseLock();
  }
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok) throw await responseError(response);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function responseError(response: Response): Promise<Error> {
  try {
    const body =
      (await response.json()) as components["schemas"]["ErrorResponse"];
    return new Error(`${body.message} (${body.code}; ${body.request_id})`);
  } catch {
    return new Error(
      `API returned HTTP ${response.status}. Check backend availability.`,
    );
  }
}
