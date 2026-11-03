import { expect, test } from "@playwright/test";
import { readEvents } from "../src/features/chat/stream";

test("SSE parser handles split UTF-8, split frames and heartbeat", async () => {
  const bytes = new TextEncoder().encode(
    ': keep-alive\r\n\r\nevent: token\r\ndata: {"event":"token","message_id":"m","conversation_id":"c","text":"你好"}\r\n\r\nevent: message_end\ndata: {"event":"message_end","message_id":"m","conversation_id":"c"}\n\n',
  );
  const response = new Response(
    new ReadableStream({
      start(controller) {
        for (const byte of bytes) controller.enqueue(new Uint8Array([byte]));
        controller.close();
      },
    }),
  );
  const received: string[] = [];
  await readEvents(response, (event) => {
    if (event.text) received.push(event.text);
  });
  expect(received).toEqual(["你好"]);
});

test("SSE parser rejects a lost terminal event", async () => {
  await expect(
    readEvents(
      new Response(
        'data: {"event":"token","message_id":"m","conversation_id":"c","text":"partial"}\n\n',
      ),
      () => undefined,
    ),
  ).rejects.toThrow("before the response completed");
});
